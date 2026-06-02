"""
Core diffing logic for comparing API specifications.

Detects breaking, potentially breaking, and non-breaking changes
between two API specifications.
"""

import json
from typing import Dict, Any, List, Optional, Set
from app.models.change import Change, DiffResult
from app.core.classifier import Classifier
from app.core.normalizer import Normalizer
from app.core.schema_utils import schema_type_set


class Differ:
    """Compares two API specifications and detects changes."""

    CONSTRAINT_KEYWORDS = (
        "$schema",
        "$id",
        "$defs",
        "const",
        "default",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "pattern",
        "format",
        "minItems",
        "maxItems",
        "uniqueItems",
        "minProperties",
        "maxProperties",
        "propertyNames",
        "dependentRequired",
        "dependentSchemas",
        "if",
        "then",
        "else",
        "contains",
        "minContains",
        "maxContains",
        "unevaluatedProperties",
        "unevaluatedItems",
        "contentEncoding",
        "contentMediaType",
        "contentSchema",
    )
    INCREASE_STRICTER_KEYWORDS = {
        "minimum",
        "exclusiveMinimum",
        "minLength",
        "minItems",
        "minProperties",
        "minContains",
    }
    DECREASE_STRICTER_KEYWORDS = {
        "maximum",
        "exclusiveMaximum",
        "maxLength",
        "maxItems",
        "maxProperties",
        "maxContains",
    }

    def __init__(self):
        self.changes: List[Change] = []
        self.old_version: Optional[str] = None
        self.new_version: Optional[str] = None

    def diff(self, old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> DiffResult:
        """
        Compare two specifications and return diff result.

        Args:
            old_spec: The original specification
            new_spec: The new specification

        Returns:
            DiffResult containing changes and metadata
        """
        self.changes = []

        # Extract version information before normalization
        self.old_version = self._extract_version(old_spec)
        self.new_version = self._extract_version(new_spec)

        component_ref_index = self._build_component_ref_index(
            old_spec.get("paths", {}),
            new_spec.get("paths", {}),
            old_spec.get("webhooks", {}),
            new_spec.get("webhooks", {}),
        )

        # Normalize both specs
        old_normalized = Normalizer.normalize(old_spec)
        new_normalized = Normalizer.normalize(new_spec)

        self._diff_json_schema_dialect(old_normalized, new_normalized)

        old_components = old_normalized.get("components", {})
        new_components = new_normalized.get("components", {})

        # Extract paths
        old_paths = old_normalized.get("paths", {})
        new_paths = new_normalized.get("paths", {})

        # Detect reusable component-level changes
        self._diff_components(old_components, new_components, component_ref_index)

        # Detect endpoint-level changes
        self._diff_endpoints(old_paths, new_paths)

        # Detect method and operation-level changes
        self._diff_operations(old_paths, new_paths)

        # Create summary
        summary = self._create_summary()

        # Return DiffResult
        return DiffResult(
            summary=summary,
            changes=self.changes,
            old_version=self.old_version,
            new_version=self.new_version,
        )

    def _diff_json_schema_dialect(
        self, old_spec: Dict[str, Any], new_spec: Dict[str, Any]
    ) -> None:
        """Detect OpenAPI 3.1 root JSON Schema dialect changes."""
        old_dialect = old_spec.get("jsonSchemaDialect")
        new_dialect = new_spec.get("jsonSchemaDialect")

        if old_dialect == new_dialect:
            return

        self.changes.append(
            Change(
                type="potentially_breaking",
                category="metadata",
                path="#",
                field_name="jsonSchemaDialect",
                message="JSON Schema dialect changed",
                details={
                    "schema_path": "#/jsonSchemaDialect",
                    "keyword": "jsonSchemaDialect",
                    "old_value": old_dialect,
                    "new_value": new_dialect,
                },
            )
        )

    @staticmethod
    def _extract_version(spec: Dict[str, Any]) -> Optional[str]:
        """
        Extract version from specification.

        Args:
            spec: The API specification

        Returns:
            Version string or None
        """
        # Try info.version first (OpenAPI standard location)
        info = spec.get("info", {})
        version = info.get("version")

        if version:
            # Combine title with version if available
            title = info.get("title", "")
            if title:
                return f"{title} v{version}"
            return f"v{version}"

        return None

    def _create_summary(self) -> Dict[str, int]:
        """
        Create summary statistics of changes.

        Returns:
            Dictionary with counts of each change type
        """
        summary = {
            "breaking": 0,
            "potentially_breaking": 0,
            "non_breaking": 0,
            "total": len(self.changes),
        }

        for change in self.changes:
            if change.type == "breaking":
                summary["breaking"] += 1
            elif change.type == "potentially_breaking":
                summary["potentially_breaking"] += 1
            elif change.type == "non_breaking":
                summary["non_breaking"] += 1

        return summary

    def _diff_components(
        self,
        old_components: Dict[str, Any],
        new_components: Dict[str, Any],
        component_ref_index: Dict[str, List[str]],
    ) -> None:
        """Detect changes in reusable OpenAPI components."""
        component_types = (
            "schemas",
            "parameters",
            "responses",
            "requestBodies",
            "headers",
            "securitySchemes",
            "examples",
            "callbacks",
            "pathItems",
        )

        for component_type in component_types:
            old_items = old_components.get(component_type, {})
            new_items = new_components.get(component_type, {})
            if not isinstance(old_items, dict) or not isinstance(new_items, dict):
                continue

            if component_type == "schemas":
                self._diff_component_schemas(
                    old_items, new_items, component_ref_index
                )
            else:
                self._diff_component_map(
                    component_type, old_items, new_items, component_ref_index
                )

    def _diff_component_schemas(
        self,
        old_schemas: Dict[str, Any],
        new_schemas: Dict[str, Any],
        component_ref_index: Dict[str, List[str]],
    ) -> None:
        """Detect reusable schema component additions, removals, and changes."""
        component_type = "schemas"

        for schema_name in old_schemas:
            if schema_name not in new_schemas:
                self.changes.append(
                    Classifier.classify_component_change(
                        component_type,
                        schema_name,
                        "removed",
                        old_value=old_schemas[schema_name],
                        details=self._component_details(
                            component_type, schema_name, component_ref_index
                        ),
                    )
                )

        for schema_name in new_schemas:
            if schema_name not in old_schemas:
                self.changes.append(
                    Classifier.classify_component_change(
                        component_type,
                        schema_name,
                        "added",
                        new_value=new_schemas[schema_name],
                        details=self._component_details(
                            component_type, schema_name, component_ref_index
                        ),
                    )
                )

        for schema_name in old_schemas:
            if schema_name not in new_schemas:
                continue

            old_schema = old_schemas[schema_name]
            new_schema = new_schemas[schema_name]
            if not isinstance(old_schema, dict) or not isinstance(new_schema, dict):
                if old_schema != new_schema:
                    self.changes.append(
                        Classifier.classify_component_change(
                            component_type,
                            schema_name,
                            "changed",
                            old_value=old_schema,
                            new_value=new_schema,
                            details=self._component_details(
                                component_type, schema_name, component_ref_index
                            ),
                        )
                    )
                continue

            self._diff_schema(
                f"#/components/schemas/{self._json_pointer_escape(schema_name)}",
                "",
                old_schema,
                new_schema,
                "component_schema",
                self._component_pointer(component_type, schema_name),
                schema_name,
            )

    def _diff_component_map(
        self,
        component_type: str,
        old_items: Dict[str, Any],
        new_items: Dict[str, Any],
        component_ref_index: Dict[str, List[str]],
    ) -> None:
        """Detect additions, removals, and object changes in reusable components."""
        for component_name in old_items:
            if component_name not in new_items:
                self.changes.append(
                    Classifier.classify_component_change(
                        component_type,
                        component_name,
                        "removed",
                        old_value=old_items[component_name],
                        details=self._component_details(
                            component_type, component_name, component_ref_index
                        ),
                    )
                )

        for component_name in new_items:
            if component_name not in old_items:
                self.changes.append(
                    Classifier.classify_component_change(
                        component_type,
                        component_name,
                        "added",
                        new_value=new_items[component_name],
                        details=self._component_details(
                            component_type, component_name, component_ref_index
                        ),
                    )
                )

        for component_name in old_items:
            if (
                component_name in new_items
                and old_items[component_name] != new_items[component_name]
            ):
                self.changes.append(
                    Classifier.classify_component_change(
                        component_type,
                        component_name,
                        "changed",
                        old_value=old_items[component_name],
                        new_value=new_items[component_name],
                        details=self._component_details(
                            component_type, component_name, component_ref_index
                        ),
                    )
                )

    def _component_details(
        self,
        component_type: str,
        component_name: str,
        component_ref_index: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """Return common details for reusable component changes."""
        ref = f"#/components/{component_type}/{self._json_pointer_escape(component_name)}"
        details: Dict[str, Any] = {"ref": ref}
        impacted_operations = component_ref_index.get(ref)
        if impacted_operations:
            details["impacted_operations"] = impacted_operations
        return details

    def _build_component_ref_index(
        self,
        old_paths: Dict[str, Any],
        new_paths: Dict[str, Any],
        old_webhooks: Dict[str, Any],
        new_webhooks: Dict[str, Any],
    ) -> Dict[str, List[str]]:
        """Index local component refs by the operations that use them."""
        ref_index: Dict[str, Set[str]] = {}
        for paths, prefix in (
            (old_paths, ""),
            (new_paths, ""),
            (old_webhooks, "WEBHOOK "),
            (new_webhooks, "WEBHOOK "),
        ):
            for path, path_item in paths.items():
                if not isinstance(path_item, dict):
                    continue
                path_level_refs = self._extract_component_refs(
                    path_item.get("parameters", [])
                )
                for method, operation in path_item.items():
                    if method.lower() not in {
                        "get",
                        "post",
                        "put",
                        "delete",
                        "patch",
                        "options",
                        "head",
                    }:
                        continue
                    operation_label = f"{prefix}{method.upper()} {path}"
                    operation_refs = path_level_refs | self._extract_component_refs(
                        operation
                    )
                    for ref in operation_refs:
                        ref_index.setdefault(ref, set()).add(operation_label)

        return {ref: sorted(operations) for ref, operations in ref_index.items()}

    def _extract_component_refs(self, value: Any) -> Set[str]:
        """Return local component refs found anywhere under a value."""
        refs: Set[str] = set()
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/"):
                refs.add(ref)
            for child in value.values():
                refs.update(self._extract_component_refs(child))
        elif isinstance(value, list):
            for item in value:
                refs.update(self._extract_component_refs(item))
        return refs

    def _diff_endpoints(
        self, old_paths: Dict[str, Any], new_paths: Dict[str, Any]
    ) -> None:
        """Detect added and removed endpoints."""
        # Removed endpoints
        for path in old_paths:
            if path not in new_paths:
                self.changes.append(
                    Classifier.classify_endpoint_removal(
                        path, details={"schema_path": self._path_item_pointer(path)}
                    )
                )

        # Added endpoints
        for path in new_paths:
            if path not in old_paths:
                self.changes.append(
                    Classifier.classify_endpoint_addition(
                        path, details={"schema_path": self._path_item_pointer(path)}
                    )
                )

    def _diff_operations(
        self, old_paths: Dict[str, Any], new_paths: Dict[str, Any]
    ) -> None:
        """Detect changes in HTTP methods and operations."""
        # Check common paths
        for path in old_paths:
            if path not in new_paths:
                continue

            old_path_item = old_paths[path]
            new_path_item = new_paths[path]

            # Get all methods (already filtered by normalizer)
            old_methods = old_path_item
            new_methods = new_path_item

            # Removed methods
            for method in old_methods:
                if method not in new_methods:
                    self.changes.append(
                        Classifier.classify_method_removal(
                            path,
                            method,
                            details={
                                "schema_path": self._operation_pointer(path, method)
                            },
                        )
                    )

            # Added methods
            for method in new_methods:
                if method not in old_methods:
                    self.changes.append(
                        Classifier.classify_method_addition(
                            path,
                            method,
                            details={
                                "schema_path": self._operation_pointer(path, method)
                            },
                        )
                    )

            # Changed methods
            for method in old_methods:
                if method in new_methods:
                    self._diff_operation(
                        path, method, old_methods[method], new_methods[method]
                    )

    def _diff_operation(
        self, path: str, method: str, old_op: Dict[str, Any], new_op: Dict[str, Any]
    ) -> None:
        """Detect changes within a single operation."""
        # Diff parameters
        self._diff_parameters(path, method, old_op, new_op)

        # Diff request body
        self._diff_request_body(path, method, old_op, new_op)

        # Diff responses
        self._diff_responses(path, method, old_op, new_op)

    def _diff_parameters(
        self,
        path: str,
        method: str,
        old_op: Dict[str, Any],
        new_op: Dict[str, Any],
    ) -> None:
        """Detect parameter changes."""
        # Operations are already normalized, use extract methods
        old_params = Normalizer.extract_parameters(old_op)
        new_params = Normalizer.extract_parameters(new_op)

        # Check each parameter type (query, path, header, cookie)
        for param_in in ("query", "path", "header", "cookie"):
            old_in_params = old_params.get(param_in, {})
            new_in_params = new_params.get(param_in, {})

            # Removed parameters
            for param_name in old_in_params:
                if param_name not in new_in_params:
                    self.changes.append(
                        Classifier.classify_parameter_change(
                            path,
                            method,
                            param_name,
                            "removed",
                            param_in=param_in,
                            details={
                                "schema_path": self._parameter_pointer(
                                    path, method, param_in, param_name
                                ),
                                "old_value": old_in_params[param_name],
                            },
                        )
                    )

            # Added parameters
            for param_name in new_in_params:
                if param_name not in old_in_params:
                    is_required = new_in_params[param_name].get("required", False)
                    self.changes.append(
                        Classifier.classify_parameter_change(
                            path,
                            method,
                            param_name,
                            "added",
                            is_required,
                            param_in=param_in,
                            details={
                                "schema_path": self._parameter_pointer(
                                    path, method, param_in, param_name
                                ),
                                "new_value": new_in_params[param_name],
                            },
                        )
                    )

            # Changed parameters (type changes)
            for param_name in old_in_params:
                if param_name in new_in_params:
                    old_param = old_in_params[param_name]
                    new_param = new_in_params[param_name]

                    # Compare schemas (already normalized to use schema wrapper)
                    old_schema = old_param.get("schema", {})
                    new_schema = new_param.get("schema", {})

                    old_type = schema_type_set(old_schema)
                    new_type = schema_type_set(new_schema)

                    if old_type != new_type and old_type and new_type:
                        old_type_value = self._format_schema_type(old_type)
                        new_type_value = self._format_schema_type(new_type)
                        self.changes.append(
                            Classifier.classify_parameter_change(
                                path,
                                method,
                                param_name,
                                "type_changed",
                                param_in=param_in,
                                old_type=old_type_value,
                                new_type=new_type_value,
                                details={
                                    "schema_path": f"{self._parameter_pointer(path, method, param_in, param_name)}/schema/type",
                                    "keyword": "type",
                                    "old_value": old_type_value,
                                    "new_value": new_type_value,
                                },
                            )
                        )

                    self._diff_schema_constraints(
                        path,
                        method,
                        old_schema,
                        new_schema,
                        f"parameter_{param_in}",
                        f"{self._parameter_pointer(path, method, param_in, param_name)}/schema",
                        param_name,
                    )

                    self._diff_parameter_serialization(
                        path, method, param_in, param_name, old_param, new_param
                    )

                    # Check required status change
                    old_required = old_param.get("required", False)
                    new_required = new_param.get("required", False)

                    if not old_required and new_required:
                        self.changes.append(
                            Classifier.classify_parameter_change(
                                path,
                                method,
                                param_name,
                                "made_required",
                                param_in=param_in,
                                details={
                                    "schema_path": f"{self._parameter_pointer(path, method, param_in, param_name)}/required",
                                    "keyword": "required",
                                    "old_value": old_required,
                                    "new_value": new_required,
                                },
                            )
                        )
                    elif old_required and not new_required:
                        self.changes.append(
                            Classifier.classify_parameter_change(
                                path,
                                method,
                                param_name,
                                "made_optional",
                                param_in=param_in,
                                details={
                                    "schema_path": f"{self._parameter_pointer(path, method, param_in, param_name)}/required",
                                    "keyword": "required",
                                    "old_value": old_required,
                                    "new_value": new_required,
                                },
                            )
                        )

    def _diff_request_body(
        self, path: str, method: str, old_op: Dict[str, Any], new_op: Dict[str, Any]
    ) -> None:
        """Detect request body schema changes."""
        old_body = Normalizer.extract_request_body(old_op)
        new_body = Normalizer.extract_request_body(new_op)

        # Get content types
        old_content_type = self._get_primary_content_type(old_body)
        new_content_type = self._get_primary_content_type(new_body)
        content_type = new_content_type or old_content_type

        # Check if request body was added or removed
        if old_body and not new_body:
            self.changes.append(
                Classifier.classify_request_body_change(
                    path,
                    method,
                    "removed",
                    content_type=old_content_type,
                    details={
                        "schema_path": self._request_body_pointer(
                            path, method, old_content_type
                        ),
                        "old_value": old_body,
                    },
                )
            )
            return

        if not old_body and new_body:
            is_required = new_body.get("required", False)
            self.changes.append(
                Classifier.classify_request_body_change(
                    path,
                    method,
                    "added",
                    is_required,
                    content_type=new_content_type,
                    details={
                        "schema_path": self._request_body_pointer(
                            path, method, new_content_type
                        ),
                        "new_value": new_body,
                    },
                )
            )
            return

        if not old_body or not new_body:
            return

        # Check required status change
        old_required = old_body.get("required", False)
        new_required = new_body.get("required", False)

        if not old_required and new_required:
            self.changes.append(
                Classifier.classify_request_body_change(
                    path,
                    method,
                    "made_required",
                    content_type=content_type,
                    details={
                        "schema_path": f"{self._request_body_pointer(path, method, content_type)}/required",
                        "keyword": "required",
                        "old_value": old_required,
                        "new_value": new_required,
                    },
                )
            )
        elif old_required and not new_required:
            self.changes.append(
                Classifier.classify_request_body_change(
                    path,
                    method,
                    "made_optional",
                    content_type=content_type,
                    details={
                        "schema_path": f"{self._request_body_pointer(path, method, content_type)}/required",
                        "keyword": "required",
                        "old_value": old_required,
                        "new_value": new_required,
                    },
                )
            )

        self._diff_request_content(path, method, old_body, new_body)

    def _diff_schema(
        self,
        path: str,
        method: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        location: str = "request_body",
        schema_path: str = "",
        field_name: str = "schema",
    ) -> None:
        """Recursively detect schema changes."""
        old_type = schema_type_set(old_schema)
        new_type = schema_type_set(new_schema)

        if old_type != new_type and old_type and new_type:
            old_type_value = self._format_schema_type(old_type)
            new_type_value = self._format_schema_type(new_type)
            self.changes.append(
                Classifier.classify_schema_change(
                    path,
                    method,
                    field_name,
                    "type_changed",
                    location,
                    old_type=old_type_value,
                    new_type=new_type_value,
                    details={
                        "schema_path": (
                            f"{schema_path}/type" if schema_path else "#/type"
                        ),
                        "keyword": "type",
                        "old_value": old_type_value,
                        "new_value": new_type_value,
                    },
                )
            )

        self._diff_schema_constraints(
            path, method, old_schema, new_schema, location, schema_path, field_name
        )

        old_props = old_schema.get("properties", {})
        new_props = new_schema.get("properties", {})
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))

        # Removed properties
        for prop_name in old_props:
            if prop_name not in new_props:
                self.changes.append(
                    Classifier.classify_schema_change(
                        path,
                        method,
                        self._field_path(field_name, prop_name),
                        "removed",
                        location,
                        details={
                            "schema_path": self._schema_property_pointer(
                                schema_path, prop_name
                            ),
                            "old_value": old_props[prop_name],
                        },
                    )
                )

        # Added properties
        for prop_name in new_props:
            if prop_name not in old_props:
                is_required = prop_name in new_required
                self.changes.append(
                    Classifier.classify_schema_change(
                        path,
                        method,
                        self._field_path(field_name, prop_name),
                        "added",
                        location,
                        is_required,
                        details={
                            "schema_path": self._schema_property_pointer(
                                schema_path, prop_name
                            ),
                            "new_value": new_props[prop_name],
                        },
                    )
                )

        # Changed property types
        for prop_name in old_props:
            if prop_name in new_props:
                # Check if property was made required or optional
                was_required = prop_name in old_required
                is_required = prop_name in new_required
                nested_field_name = self._field_path(field_name, prop_name)

                if not was_required and is_required:
                    self.changes.append(
                        Classifier.classify_schema_change(
                            path,
                            method,
                            nested_field_name,
                            "made_required",
                            location,
                            details={
                                "schema_path": f"{schema_path}/required",
                                "keyword": "required",
                                "old_value": sorted(old_required),
                                "new_value": sorted(new_required),
                            },
                        )
                    )
                elif was_required and not is_required:
                    self.changes.append(
                        Classifier.classify_schema_change(
                            path,
                            method,
                            nested_field_name,
                            "made_optional",
                            location,
                            details={
                                "schema_path": f"{schema_path}/required",
                                "keyword": "required",
                                "old_value": sorted(old_required),
                                "new_value": sorted(new_required),
                            },
                        )
                    )

                self._diff_schema(
                    path,
                    method,
                    old_props[prop_name],
                    new_props[prop_name],
                    location,
                    self._schema_property_pointer(schema_path, prop_name),
                    nested_field_name,
                )

        self._diff_array_items(
            path, method, old_schema, new_schema, location, schema_path, field_name
        )
        self._diff_prefix_items(
            path, method, old_schema, new_schema, location, schema_path, field_name
        )
        self._diff_additional_properties(
            path, method, old_schema, new_schema, location, schema_path, field_name
        )
        self._diff_composition(
            path, method, old_schema, new_schema, location, schema_path, field_name
        )

    def _diff_schema_constraints(
        self,
        path: str,
        method: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        location: str,
        schema_path: str,
        field_name: str,
    ) -> None:
        """Detect JSON Schema enum, default, and validation constraint changes."""
        self._diff_enum_constraint(
            path, method, old_schema, new_schema, location, schema_path, field_name
        )
        self._diff_examples_keyword(
            path, method, old_schema, new_schema, location, schema_path, field_name
        )

        for keyword in self.CONSTRAINT_KEYWORDS:
            if keyword == "default":
                self._diff_default_constraint(
                    path,
                    method,
                    old_schema,
                    new_schema,
                    location,
                    schema_path,
                    field_name,
                )
                continue

            old_has_keyword = keyword in old_schema
            new_has_keyword = keyword in new_schema
            old_value = old_schema.get(keyword)
            new_value = new_schema.get(keyword)

            if not old_has_keyword and not new_has_keyword:
                continue
            if old_has_keyword and new_has_keyword and old_value == new_value:
                continue

            change_type = self._classify_constraint_direction(
                keyword, old_has_keyword, old_value, new_has_keyword, new_value
            )
            self._append_schema_constraint_change(
                path,
                method,
                field_name,
                change_type,
                location,
                keyword,
                old_value if old_has_keyword else None,
                new_value if new_has_keyword else None,
                self._keyword_pointer(schema_path, keyword),
            )

    def _diff_examples_keyword(
        self,
        path: str,
        method: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        location: str,
        schema_path: str,
        field_name: str,
    ) -> None:
        """Compare OpenAPI 3.0 example and OpenAPI 3.1 examples consistently."""
        old_has_examples = "examples" in old_schema or "example" in old_schema
        new_has_examples = "examples" in new_schema or "example" in new_schema

        if not old_has_examples and not new_has_examples:
            return

        old_value = self._schema_examples_value(old_schema)
        new_value = self._schema_examples_value(new_schema)
        if old_value == new_value:
            return

        self._append_schema_constraint_change(
            path,
            method,
            field_name,
            "changed",
            location,
            "examples",
            old_value if old_has_examples else None,
            new_value if new_has_examples else None,
            self._keyword_pointer(schema_path, "examples"),
        )

    @staticmethod
    def _schema_examples_value(schema: Dict[str, Any]) -> Any:
        if "examples" in schema:
            return schema["examples"]
        if "example" in schema:
            return [schema["example"]]
        return None

    def _diff_enum_constraint(
        self,
        path: str,
        method: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        location: str,
        schema_path: str,
        field_name: str,
    ) -> None:
        """Detect enum value additions and removals."""
        old_enum = old_schema.get("enum")
        new_enum = new_schema.get("enum")
        if not isinstance(old_enum, list) and not isinstance(new_enum, list):
            return

        if not isinstance(old_enum, list):
            self._append_schema_constraint_change(
                path,
                method,
                field_name,
                "made_stricter",
                location,
                "enum",
                None,
                new_enum,
                self._keyword_pointer(schema_path, "enum"),
            )
            return

        if not isinstance(new_enum, list):
            self._append_schema_constraint_change(
                path,
                method,
                field_name,
                "made_looser",
                location,
                "enum",
                old_enum,
                None,
                self._keyword_pointer(schema_path, "enum"),
            )
            return

        old_values = self._comparable_values(old_enum)
        new_values = self._comparable_values(new_enum)

        for key, value in old_values.items():
            if key not in new_values:
                self._append_schema_constraint_change(
                    path,
                    method,
                    field_name,
                    "enum_value_removed",
                    location,
                    "enum",
                    value,
                    None,
                    self._keyword_pointer(schema_path, "enum"),
                )

        for key, value in new_values.items():
            if key not in old_values:
                self._append_schema_constraint_change(
                    path,
                    method,
                    field_name,
                    "enum_value_added",
                    location,
                    "enum",
                    None,
                    value,
                    self._keyword_pointer(schema_path, "enum"),
                )

    def _diff_default_constraint(
        self,
        path: str,
        method: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        location: str,
        schema_path: str,
        field_name: str,
    ) -> None:
        """Detect default value additions, removals, and changes."""
        old_has_default = "default" in old_schema
        new_has_default = "default" in new_schema

        if not old_has_default and not new_has_default:
            return

        old_value = old_schema.get("default")
        new_value = new_schema.get("default")
        if old_has_default and new_has_default and old_value == new_value:
            return

        if old_has_default and not new_has_default:
            change_type = "default_removed"
        elif new_has_default and not old_has_default:
            change_type = "default_added"
        else:
            change_type = "default_changed"

        self._append_schema_constraint_change(
            path,
            method,
            field_name,
            change_type,
            location,
            "default",
            old_value if old_has_default else None,
            new_value if new_has_default else None,
            self._keyword_pointer(schema_path, "default"),
        )

    def _append_schema_constraint_change(
        self,
        path: str,
        method: str,
        field_name: str,
        change_type: str,
        location: str,
        keyword: str,
        old_value: Any,
        new_value: Any,
        schema_path: str,
    ) -> None:
        """Append a schema constraint change with consistent details."""
        self.changes.append(
            Classifier.classify_schema_constraint_change(
                path,
                method,
                field_name,
                change_type,
                location,
                keyword,
                old_value,
                new_value,
                details={"schema_path": schema_path},
            )
        )

    def _classify_constraint_direction(
        self,
        keyword: str,
        old_has_keyword: bool,
        old_value: Any,
        new_has_keyword: bool,
        new_value: Any,
    ) -> str:
        """Classify whether a validation constraint became stricter or looser."""
        if not old_has_keyword and new_has_keyword:
            return "made_stricter"
        if old_has_keyword and not new_has_keyword:
            return "made_looser"

        if keyword in self.INCREASE_STRICTER_KEYWORDS:
            return self._compare_number_direction(
                old_value, new_value, increase_stricter=True
            )
        if keyword in self.DECREASE_STRICTER_KEYWORDS:
            return self._compare_number_direction(
                old_value, new_value, increase_stricter=False
            )

        if keyword == "uniqueItems":
            if old_value is False and new_value is True:
                return "made_stricter"
            if old_value is True and new_value is False:
                return "made_looser"

        return "changed"

    @staticmethod
    def _compare_number_direction(
        old_value: Any, new_value: Any, increase_stricter: bool
    ) -> str:
        """Classify numeric constraint direction when both values are comparable."""
        if not isinstance(old_value, (int, float)) or not isinstance(
            new_value, (int, float)
        ):
            return "changed"
        if old_value == new_value:
            return "changed"

        increased = new_value > old_value
        if increased == increase_stricter:
            return "made_stricter"
        return "made_looser"

    def _diff_array_items(
        self,
        path: str,
        method: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        location: str,
        schema_path: str,
        field_name: str,
    ) -> None:
        """Detect changes in homogeneous array item schemas."""
        old_has_items = "items" in old_schema
        new_has_items = "items" in new_schema
        item_field = f"{field_name}[]"
        item_path = f"{schema_path}/items" if schema_path else "#/items"

        if old_has_items and not new_has_items:
            self.changes.append(
                Classifier.classify_schema_change(
                    path,
                    method,
                    item_field,
                    "removed",
                    location,
                    details={
                        "schema_path": item_path,
                        "keyword": "items",
                        "old_value": old_schema["items"],
                    },
                )
            )
            return

        if new_has_items and not old_has_items:
            self.changes.append(
                Classifier.classify_schema_change(
                    path,
                    method,
                    item_field,
                    "added",
                    location,
                    details={
                        "schema_path": item_path,
                        "keyword": "items",
                        "new_value": new_schema["items"],
                    },
                )
            )
            return

        old_items = old_schema.get("items")
        new_items = new_schema.get("items")
        if isinstance(old_items, dict) and isinstance(new_items, dict):
            self._diff_schema(
                path, method, old_items, new_items, location, item_path, item_field
            )
        elif old_has_items and new_has_items and old_items != new_items:
            self.changes.append(
                Classifier.classify_schema_change(
                    path,
                    method,
                    item_field,
                    "type_changed",
                    location,
                    details={
                        "schema_path": item_path,
                        "keyword": "items",
                        "old_value": old_items,
                        "new_value": new_items,
                    },
                )
            )

    def _diff_prefix_items(
        self,
        path: str,
        method: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        location: str,
        schema_path: str,
        field_name: str,
    ) -> None:
        """Detect changes in tuple-style array item schemas."""
        old_items = old_schema.get("prefixItems", [])
        new_items = new_schema.get("prefixItems", [])
        if not isinstance(old_items, list) or not isinstance(new_items, list):
            return

        prefix_path = f"{schema_path}/prefixItems" if schema_path else "#/prefixItems"
        common_length = min(len(old_items), len(new_items))

        for index in range(common_length):
            item_field = f"{field_name}[{index}]"
            item_path = f"{prefix_path}/{index}"
            old_item = old_items[index]
            new_item = new_items[index]
            if isinstance(old_item, dict) and isinstance(new_item, dict):
                self._diff_schema(
                    path, method, old_item, new_item, location, item_path, item_field
                )
            elif old_item != new_item:
                self.changes.append(
                    Classifier.classify_schema_change(
                        path,
                        method,
                        item_field,
                        "type_changed",
                        location,
                        details={
                            "schema_path": item_path,
                            "keyword": "prefixItems",
                            "old_value": old_item,
                            "new_value": new_item,
                        },
                    )
                )

        for index in range(common_length, len(old_items)):
            self.changes.append(
                Classifier.classify_schema_change(
                    path,
                    method,
                    f"{field_name}[{index}]",
                    "removed",
                    location,
                    details={
                        "schema_path": f"{prefix_path}/{index}",
                        "keyword": "prefixItems",
                        "old_value": old_items[index],
                    },
                )
            )

        for index in range(common_length, len(new_items)):
            self.changes.append(
                Classifier.classify_schema_change(
                    path,
                    method,
                    f"{field_name}[{index}]",
                    "added",
                    location,
                    details={
                        "schema_path": f"{prefix_path}/{index}",
                        "keyword": "prefixItems",
                        "new_value": new_items[index],
                    },
                )
            )

    def _diff_additional_properties(
        self,
        path: str,
        method: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        location: str,
        schema_path: str,
        field_name: str,
    ) -> None:
        """Detect changes in map/dictionary value schemas."""
        old_has_additional = "additionalProperties" in old_schema
        new_has_additional = "additionalProperties" in new_schema
        map_field = f"{field_name}.*"
        map_path = (
            f"{schema_path}/additionalProperties"
            if schema_path
            else "#/additionalProperties"
        )

        if old_has_additional and not new_has_additional:
            self.changes.append(
                Classifier.classify_schema_change(
                    path,
                    method,
                    map_field,
                    "removed",
                    location,
                    details={
                        "schema_path": map_path,
                        "keyword": "additionalProperties",
                        "old_value": old_schema["additionalProperties"],
                    },
                )
            )
            return

        if new_has_additional and not old_has_additional:
            self.changes.append(
                Classifier.classify_schema_change(
                    path,
                    method,
                    map_field,
                    "added",
                    location,
                    details={
                        "schema_path": map_path,
                        "keyword": "additionalProperties",
                        "new_value": new_schema["additionalProperties"],
                    },
                )
            )
            return

        old_additional = old_schema.get("additionalProperties")
        new_additional = new_schema.get("additionalProperties")
        if isinstance(old_additional, dict) and isinstance(new_additional, dict):
            self._diff_schema(
                path,
                method,
                old_additional,
                new_additional,
                location,
                map_path,
                map_field,
            )
        elif (
            old_has_additional
            and new_has_additional
            and old_additional != new_additional
        ):
            self.changes.append(
                Classifier.classify_schema_change(
                    path,
                    method,
                    map_field,
                    "type_changed",
                    location,
                    details={
                        "schema_path": map_path,
                        "keyword": "additionalProperties",
                        "old_value": old_additional,
                        "new_value": new_additional,
                    },
                )
            )

    def _diff_composition(
        self,
        path: str,
        method: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        location: str,
        schema_path: str,
        field_name: str,
    ) -> None:
        """Detect changes in composed schema branches."""
        for keyword in ("allOf", "oneOf", "anyOf"):
            old_branches = old_schema.get(keyword, [])
            new_branches = new_schema.get(keyword, [])
            if not isinstance(old_branches, list) or not isinstance(new_branches, list):
                continue

            keyword_path = f"{schema_path}/{keyword}" if schema_path else f"#/{keyword}"
            common_length = min(len(old_branches), len(new_branches))

            for index in range(common_length):
                branch_field = f"{field_name}.{keyword}[{index}]"
                branch_path = f"{keyword_path}/{index}"
                old_branch = old_branches[index]
                new_branch = new_branches[index]
                if isinstance(old_branch, dict) and isinstance(new_branch, dict):
                    self._diff_schema(
                        path,
                        method,
                        old_branch,
                        new_branch,
                        location,
                        branch_path,
                        branch_field,
                    )
                elif old_branch != new_branch:
                    self.changes.append(
                        Classifier.classify_schema_change(
                            path,
                            method,
                            branch_field,
                            "type_changed",
                            location,
                            details={
                                "schema_path": branch_path,
                                "keyword": keyword,
                                "old_value": old_branch,
                                "new_value": new_branch,
                            },
                        )
                    )

            for index in range(common_length, len(old_branches)):
                self.changes.append(
                    Classifier.classify_schema_change(
                        path,
                        method,
                        f"{field_name}.{keyword}[{index}]",
                        "removed",
                        location,
                        details={
                            "schema_path": f"{keyword_path}/{index}",
                            "keyword": keyword,
                            "old_value": old_branches[index],
                        },
                    )
                )

            for index in range(common_length, len(new_branches)):
                self.changes.append(
                    Classifier.classify_schema_change(
                        path,
                        method,
                        f"{field_name}.{keyword}[{index}]",
                        "added",
                        location,
                        details={
                            "schema_path": f"{keyword_path}/{index}",
                            "keyword": keyword,
                            "new_value": new_branches[index],
                        },
                    )
                )

        old_not = old_schema.get("not")
        new_not = new_schema.get("not")
        not_path = f"{schema_path}/not" if schema_path else "#/not"
        if isinstance(old_not, dict) and isinstance(new_not, dict):
            self._diff_schema(
                path,
                method,
                old_not,
                new_not,
                location,
                not_path,
                f"{field_name}.not",
            )
        elif old_not != new_not:
            if old_not is None and new_not is None:
                return
            change_type = (
                "added"
                if old_not is None
                else "removed" if new_not is None else "type_changed"
            )
            self.changes.append(
                Classifier.classify_schema_change(
                    path,
                    method,
                    f"{field_name}.not",
                    change_type,
                    location,
                    details={
                        "schema_path": not_path,
                        "keyword": "not",
                        "old_value": old_not,
                        "new_value": new_not,
                    },
                )
            )

    @staticmethod
    def _get_primary_content_type(body: Dict[str, Any]) -> str:
        """Extract primary content type from body."""
        if not body:
            return ""
        content = body.get("content", {})
        if "application/json" in content:
            return "application/json"
        if content:
            return next(iter(content.keys()))
        return ""

    @staticmethod
    def _format_schema_type(types: set[str]) -> Any:
        """Format a schema type set for stable result details."""
        ordered = sorted(type_name for type_name in types if type_name != "null")
        if "null" in types:
            ordered.append("null")
        if len(ordered) == 1:
            return ordered[0]
        return ordered

    def _diff_responses(
        self, path: str, method: str, old_op: Dict[str, Any], new_op: Dict[str, Any]
    ) -> None:
        """Detect response changes."""
        old_responses = Normalizer.extract_responses(old_op)
        new_responses = Normalizer.extract_responses(new_op)

        # Removed responses
        for status_code in old_responses:
            if status_code not in new_responses:
                self.changes.append(
                    Classifier.classify_response_change(
                        path,
                        method,
                        status_code,
                        "removed",
                        details={
                            "schema_path": self._response_pointer(
                                path, method, status_code
                            ),
                            "old_value": old_responses[status_code],
                        },
                    )
                )

        # Added responses
        for status_code in new_responses:
            if status_code not in old_responses:
                self.changes.append(
                    Classifier.classify_response_change(
                        path,
                        method,
                        status_code,
                        "added",
                        details={
                            "schema_path": self._response_pointer(
                                path, method, status_code
                            ),
                            "new_value": new_responses[status_code],
                        },
                    )
                )

        # Changed responses (schema changes)
        for status_code in old_responses:
            if status_code in new_responses:
                old_response = old_responses[status_code]
                new_response = new_responses[status_code]

                self._diff_response_content(
                    path, method, status_code, old_response, new_response
                )
                self._diff_response_headers(
                    path, method, status_code, old_response, new_response
                )

    def _diff_parameter_serialization(
        self,
        path: str,
        method: str,
        param_in: str,
        param_name: str,
        old_param: Dict[str, Any],
        new_param: Dict[str, Any],
    ) -> None:
        """Detect OpenAPI parameter serialization attribute changes."""
        for keyword in (
            "style",
            "explode",
            "allowReserved",
            "allowEmptyValue",
            "collectionFormat",
            "content",
        ):
            old_has_keyword = keyword in old_param
            new_has_keyword = keyword in new_param
            old_value = old_param.get(keyword)
            new_value = new_param.get(keyword)

            if not old_has_keyword and not new_has_keyword:
                continue
            if old_has_keyword and new_has_keyword and old_value == new_value:
                continue

            self.changes.append(
                Classifier.classify_parameter_serialization_change(
                    path,
                    method,
                    param_name,
                    param_in,
                    keyword,
                    old_value if old_has_keyword else None,
                    new_value if new_has_keyword else None,
                    details={
                        "schema_path": self._keyword_pointer(
                            self._parameter_pointer(path, method, param_in, param_name),
                            keyword,
                        )
                    },
                )
            )

    def _diff_request_content(
        self,
        path: str,
        method: str,
        old_body: Dict[str, Any],
        new_body: Dict[str, Any],
    ) -> None:
        """Detect request body media type and per-media schema changes."""
        old_content = old_body.get("content", {})
        new_content = new_body.get("content", {})
        self._diff_content_media_types(
            path,
            method,
            old_content,
            new_content,
            location="request_body",
            pointer_builder=lambda content_type: self._request_body_pointer(
                path, method, content_type
            ),
        )

        for content_type in old_content:
            if content_type not in new_content:
                continue

            old_schema = old_content[content_type].get("schema", {})
            new_schema = new_content[content_type].get("schema", {})
            if old_schema and new_schema:
                self._diff_schema(
                    path,
                    method,
                    old_schema,
                    new_schema,
                    "request_body",
                    self._request_schema_pointer(path, method, content_type),
                )

    def _diff_response_content(
        self,
        path: str,
        method: str,
        status_code: str,
        old_response: Dict[str, Any],
        new_response: Dict[str, Any],
    ) -> None:
        """Detect response media type and per-media schema changes."""
        old_content = old_response.get("content", {})
        new_content = new_response.get("content", {})
        self._diff_content_media_types(
            path,
            method,
            old_content,
            new_content,
            location="response",
            status_code=status_code,
            pointer_builder=lambda content_type: self._response_content_pointer(
                path, method, status_code, content_type
            ),
        )

        for content_type in old_content:
            if content_type not in new_content:
                continue

            old_schema = old_content[content_type].get("schema", {})
            new_schema = new_content[content_type].get("schema", {})
            if old_schema and new_schema:
                self._diff_schema(
                    path,
                    method,
                    old_schema,
                    new_schema,
                    f"response_{status_code}",
                    self._response_schema_pointer(
                        path, method, status_code, content_type
                    ),
                )

    def _diff_content_media_types(
        self,
        path: str,
        method: str,
        old_content: Dict[str, Any],
        new_content: Dict[str, Any],
        location: str,
        pointer_builder,
        status_code: str = "",
    ) -> None:
        """Detect media type additions and removals for a content map."""
        for content_type in old_content:
            if content_type not in new_content:
                self.changes.append(
                    Classifier.classify_media_type_change(
                        path,
                        method,
                        location,
                        content_type,
                        "removed",
                        status_code=status_code,
                        old_value=old_content[content_type],
                        details={"schema_path": pointer_builder(content_type)},
                    )
                )

        for content_type in new_content:
            if content_type not in old_content:
                self.changes.append(
                    Classifier.classify_media_type_change(
                        path,
                        method,
                        location,
                        content_type,
                        "added",
                        status_code=status_code,
                        new_value=new_content[content_type],
                        details={"schema_path": pointer_builder(content_type)},
                    )
                )

    def _diff_response_headers(
        self,
        path: str,
        method: str,
        status_code: str,
        old_response: Dict[str, Any],
        new_response: Dict[str, Any],
    ) -> None:
        """Detect response header additions, removals, and schema changes."""
        old_headers = old_response.get("headers", {})
        new_headers = new_response.get("headers", {})

        for header_name in old_headers:
            if header_name not in new_headers:
                self.changes.append(
                    Classifier.classify_response_header_change(
                        path,
                        method,
                        status_code,
                        header_name,
                        "removed",
                        old_value=old_headers[header_name],
                        details={
                            "schema_path": self._response_header_pointer(
                                path, method, status_code, header_name
                            )
                        },
                    )
                )

        for header_name in new_headers:
            if header_name not in old_headers:
                self.changes.append(
                    Classifier.classify_response_header_change(
                        path,
                        method,
                        status_code,
                        header_name,
                        "added",
                        new_value=new_headers[header_name],
                        details={
                            "schema_path": self._response_header_pointer(
                                path, method, status_code, header_name
                            )
                        },
                    )
                )

        for header_name in old_headers:
            if header_name not in new_headers:
                continue
            old_header = old_headers[header_name]
            new_header = new_headers[header_name]
            header_path = self._response_header_pointer(
                path, method, status_code, header_name
            )

            if not isinstance(old_header, dict) or not isinstance(new_header, dict):
                if old_header != new_header:
                    self.changes.append(
                        Classifier.classify_response_header_change(
                            path,
                            method,
                            status_code,
                            header_name,
                            "changed",
                            old_value=old_header,
                            new_value=new_header,
                            details={"schema_path": header_path},
                        )
                    )
                continue

            old_schema = old_header.get("schema", {})
            new_schema = new_header.get("schema", {})
            if old_schema and new_schema:
                self._diff_schema(
                    path,
                    method,
                    old_schema,
                    new_schema,
                    f"response_{status_code}_header",
                    f"{header_path}/schema",
                    header_name,
                )
            elif old_header != new_header:
                self.changes.append(
                    Classifier.classify_response_header_change(
                        path,
                        method,
                        status_code,
                        header_name,
                        "changed",
                        old_value=old_header,
                        new_value=new_header,
                        details={"schema_path": header_path},
                    )
                )

    @staticmethod
    def _extract_schema_from_request_body(
        request_body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract schema from request body object."""
        if not request_body:
            return {}

        content = request_body.get("content", {})
        # Try to get application/json first, then any content type
        for content_type in ["application/json", *content.keys()]:
            if content_type in content:
                schema = content[content_type].get("schema", {})
                if schema:
                    return schema
        return {}

    @staticmethod
    def _extract_schema_from_response(
        response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract schema from response object."""
        if not response:
            return {}

        content = response.get("content", {})
        # Try to get application/json first, then any content type
        for content_type in ["application/json", *content.keys()]:
            if content_type in content:
                schema = content[content_type].get("schema", {})
                if schema:
                    return schema
        return {}

    @staticmethod
    def _json_pointer_escape(value: str) -> str:
        """Escape a path segment for JSON Pointer."""
        return value.replace("~", "~0").replace("/", "~1")

    @classmethod
    def _path_item_pointer(cls, path: str) -> str:
        """Return a stable pointer for an OpenAPI path item."""
        return f"#/paths/{cls._json_pointer_escape(path)}"

    @classmethod
    def _operation_pointer(cls, path: str, method: str) -> str:
        """Return a stable pointer for an OpenAPI operation."""
        return f"{cls._path_item_pointer(path)}/{method.lower()}"

    @classmethod
    def _parameter_pointer(
        cls, path: str, method: str, param_in: str, param_name: str
    ) -> str:
        """Return a stable identity pointer for a normalized parameter."""
        escaped_location = cls._json_pointer_escape(param_in)
        escaped_name = cls._json_pointer_escape(param_name)
        return f"{cls._operation_pointer(path, method)}/parameters/{escaped_location}/{escaped_name}"

    @classmethod
    def _request_body_pointer(
        cls, path: str, method: str, content_type: str = ""
    ) -> str:
        """Return a stable pointer for a request body or one of its media types."""
        pointer = f"{cls._operation_pointer(path, method)}/requestBody"
        if content_type:
            pointer = f"{pointer}/content/{cls._json_pointer_escape(content_type)}"
        return pointer

    @classmethod
    def _request_schema_pointer(
        cls, path: str, method: str, content_type: str = ""
    ) -> str:
        """Return a stable pointer for a request body schema."""
        return f"{cls._request_body_pointer(path, method, content_type)}/schema"

    @classmethod
    def _response_pointer(cls, path: str, method: str, status_code: str) -> str:
        """Return a stable pointer for a response."""
        return f"{cls._operation_pointer(path, method)}/responses/{cls._json_pointer_escape(status_code)}"

    @classmethod
    def _response_content_pointer(
        cls, path: str, method: str, status_code: str, content_type: str = ""
    ) -> str:
        """Return a stable pointer for a response media type."""
        pointer = cls._response_pointer(path, method, status_code)
        if content_type:
            pointer = f"{pointer}/content/{cls._json_pointer_escape(content_type)}"
        return pointer

    @classmethod
    def _response_schema_pointer(
        cls, path: str, method: str, status_code: str, content_type: str = ""
    ) -> str:
        """Return a stable pointer for a response schema."""
        return f"{cls._response_content_pointer(path, method, status_code, content_type)}/schema"

    @classmethod
    def _response_header_pointer(
        cls, path: str, method: str, status_code: str, header_name: str
    ) -> str:
        """Return a stable pointer for a response header."""
        return (
            f"{cls._response_pointer(path, method, status_code)}/headers/"
            f"{cls._json_pointer_escape(header_name)}"
        )

    @classmethod
    def _component_pointer(cls, component_type: str, component_name: str) -> str:
        """Return a stable pointer for a reusable component."""
        return (
            f"#/components/{cls._json_pointer_escape(component_type)}/"
            f"{cls._json_pointer_escape(component_name)}"
        )

    @classmethod
    def _schema_property_pointer(cls, schema_path: str, prop_name: str) -> str:
        """Return a pointer for a property under a schema."""
        if not schema_path:
            return f"#/properties/{cls._json_pointer_escape(prop_name)}"
        return f"{schema_path}/properties/{cls._json_pointer_escape(prop_name)}"

    @classmethod
    def _keyword_pointer(cls, schema_path: str, keyword: str) -> str:
        """Return a pointer for a keyword under a schema."""
        escaped_keyword = cls._json_pointer_escape(keyword)
        if not schema_path:
            return f"#/{escaped_keyword}"
        return f"{schema_path}/{escaped_keyword}"

    @staticmethod
    def _comparable_values(values: List[Any]) -> Dict[str, Any]:
        """Return enum values keyed by stable JSON representations."""
        comparable = {}
        for value in values:
            try:
                key = json.dumps(value, sort_keys=True, separators=(",", ":"))
            except TypeError:
                key = repr(value)
            comparable[key] = value
        return comparable

    @staticmethod
    def _field_path(parent: str, child: str) -> str:
        """Return a compact dotted field path for result display."""
        if not parent or parent == "schema":
            return child
        return f"{parent}.{child}"
