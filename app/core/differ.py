"""
Core diffing logic for comparing API specifications.

Detects breaking, potentially breaking, and non-breaking changes
between two API specifications.
"""

from typing import Dict, Any, List, Optional
from app.models.change import Change, DiffResult
from app.core.classifier import Classifier
from app.core.normalizer import Normalizer
from app.core.schema_utils import schema_type_set


class Differ:
    """Compares two API specifications and detects changes."""

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

        # Normalize both specs
        old_normalized = Normalizer.normalize(old_spec)
        new_normalized = Normalizer.normalize(new_spec)

        # Extract paths
        old_paths = old_normalized.get("paths", {})
        new_paths = new_normalized.get("paths", {})

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

        # Extract schemas from content
        old_schema = self._extract_schema_from_request_body(old_body)
        new_schema = self._extract_schema_from_request_body(new_body)

        if not old_schema or not new_schema:
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

        # Diff schema properties
        self._diff_schema(
            path,
            method,
            old_schema,
            new_schema,
            "request_body",
            self._request_schema_pointer(path, method, content_type),
        )

    def _diff_schema(
        self,
        path: str,
        method: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        location: str = "request_body",
        schema_path: str = "",
    ) -> None:
        """Detect schema property changes."""
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
                        prop_name,
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
                        prop_name,
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
                old_prop_type = schema_type_set(old_props[prop_name])
                new_prop_type = schema_type_set(new_props[prop_name])

                if old_prop_type != new_prop_type and old_prop_type and new_prop_type:
                    old_type_value = self._format_schema_type(old_prop_type)
                    new_type_value = self._format_schema_type(new_prop_type)
                    self.changes.append(
                        Classifier.classify_schema_change(
                            path,
                            method,
                            prop_name,
                            "type_changed",
                            location,
                            old_type=old_type_value,
                            new_type=new_type_value,
                            details={
                                "schema_path": f"{self._schema_property_pointer(schema_path, prop_name)}/type",
                                "keyword": "type",
                                "old_value": old_type_value,
                                "new_value": new_type_value,
                            },
                        )
                    )

                # Check if property was made required or optional
                was_required = prop_name in old_required
                is_required = prop_name in new_required

                if not was_required and is_required:
                    self.changes.append(
                        Classifier.classify_schema_change(
                            path,
                            method,
                            prop_name,
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
                            prop_name,
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

                # Extract schemas from responses
                old_schema = self._extract_schema_from_response(old_response)
                new_schema = self._extract_schema_from_response(new_response)
                content_type = self._get_primary_content_type(
                    new_response
                ) or self._get_primary_content_type(old_response)

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
    def _response_schema_pointer(
        cls, path: str, method: str, status_code: str, content_type: str = ""
    ) -> str:
        """Return a stable pointer for a response schema."""
        pointer = cls._response_pointer(path, method, status_code)
        if content_type:
            pointer = f"{pointer}/content/{cls._json_pointer_escape(content_type)}"
        return f"{pointer}/schema"

    @classmethod
    def _schema_property_pointer(cls, schema_path: str, prop_name: str) -> str:
        """Return a pointer for a property under a schema."""
        if not schema_path:
            return f"#/properties/{cls._json_pointer_escape(prop_name)}"
        return f"{schema_path}/properties/{cls._json_pointer_escape(prop_name)}"
