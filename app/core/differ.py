"""
Core diffing logic for comparing API specifications.

Detects breaking, potentially breaking, and non-breaking changes
between two API specifications.
"""

from typing import Dict, Any, List, Tuple
from app.models.change import Change
from app.core.classifier import Classifier
from app.core.normalizer import Normalizer


class Differ:
    """Compares two API specifications and detects changes."""

    def __init__(self):
        self.changes: List[Change] = []

    def diff(self, old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> List[Change]:
        """
        Compare two specifications and return list of changes.
        
        Args:
            old_spec: The original specification
            new_spec: The new specification
            
        Returns:
            List of detected changes
        """
        self.changes = []
        
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

        return self.changes

    def _diff_endpoints(
        self, old_paths: Dict[str, Any], new_paths: Dict[str, Any]
    ) -> None:
        """Detect added and removed endpoints."""
        # Removed endpoints
        for path in old_paths:
            if path not in new_paths:
                self.changes.append(Classifier.classify_endpoint_removal(path))

        # Added endpoints
        for path in new_paths:
            if path not in old_paths:
                self.changes.append(Classifier.classify_endpoint_addition(path))

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

            # Get all methods
            old_methods = {
                k: v
                for k, v in old_path_item.items()
                if isinstance(v, dict) and k.lower() in (
                    "get", "post", "put", "delete", "patch", "options", "head"
                )
            }
            new_methods = {
                k: v
                for k, v in new_path_item.items()
                if isinstance(v, dict) and k.lower() in (
                    "get", "post", "put", "delete", "patch", "options", "head"
                )
            }

            # Removed methods
            for method in old_methods:
                if method not in new_methods:
                    self.changes.append(
                        Classifier.classify_method_removal(path, method)
                    )

            # Added methods
            for method in new_methods:
                if method not in old_methods:
                    self.changes.append(
                        Classifier.classify_method_addition(path, method)
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
        is_openapi3 = "parameters" in old_op or "requestBody" in old_op

        # Diff parameters
        self._diff_parameters(path, method, old_op, new_op, is_openapi3)

        # Diff request body
        if is_openapi3:
            self._diff_request_body(path, method, old_op, new_op)

        # Diff responses
        self._diff_responses(path, method, old_op, new_op)

    def _diff_parameters(
        self,
        path: str,
        method: str,
        old_op: Dict[str, Any],
        new_op: Dict[str, Any],
        is_openapi3: bool,
    ) -> None:
        """Detect parameter changes."""
        old_params = Normalizer.extract_parameters(old_op, is_openapi3)
        new_params = Normalizer.extract_parameters(new_op, is_openapi3)

        # Check each parameter type (query, path, header)
        for param_in in ("query", "path", "header"):
            old_in_params = old_params.get(param_in, {})
            new_in_params = new_params.get(param_in, {})

            # Removed parameters
            for param_name in old_in_params:
                if param_name not in new_in_params:
                    self.changes.append(
                        Classifier.classify_parameter_change(
                            path, method, param_name, "removed"
                        )
                    )

            # Added parameters
            for param_name in new_in_params:
                if param_name not in old_in_params:
                    is_required = new_in_params[param_name].get("required", False)
                    self.changes.append(
                        Classifier.classify_parameter_change(
                            path, method, param_name, "added", is_required
                        )
                    )

            # Changed parameters (type changes)
            for param_name in old_in_params:
                if param_name in new_in_params:
                    old_param = old_in_params[param_name]
                    new_param = new_in_params[param_name]

                    # Type comparison (simplified)
                    old_type = str(old_param.get("schema") or old_param.get("type", ""))
                    new_type = str(new_param.get("schema") or new_param.get("type", ""))

                    if old_type != new_type and old_type and new_type:
                        self.changes.append(
                            Classifier.classify_parameter_change(
                                path, method, param_name, "type_changed"
                            )
                        )

    def _diff_request_body(
        self, path: str, method: str, old_op: Dict[str, Any], new_op: Dict[str, Any]
    ) -> None:
        """Detect request body schema changes."""
        old_body = old_op.get("requestBody", {})
        new_body = new_op.get("requestBody", {})

        if not old_body and not new_body:
            return

        # Extract schemas
        old_schema = self._extract_schema_from_request_body(old_body)
        new_schema = self._extract_schema_from_request_body(new_body)

        if not old_schema or not new_schema:
            return

        # Diff schema properties
        self._diff_schema(path, method, old_schema, new_schema, "body")

    def _diff_schema(
        self,
        path: str,
        method: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        location: str = "body",
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
                        path, method, prop_name, "removed"
                    )
                )

        # Added properties
        for prop_name in new_props:
            if prop_name not in old_props:
                is_required = prop_name in new_required
                self.changes.append(
                    Classifier.classify_schema_change(
                        path, method, prop_name, "added", is_required
                    )
                )

        # Changed property types
        for prop_name in old_props:
            if prop_name in new_props:
                old_prop_type = str(old_props[prop_name].get("type", ""))
                new_prop_type = str(new_props[prop_name].get("type", ""))

                if old_prop_type != new_prop_type and old_prop_type and new_prop_type:
                    self.changes.append(
                        Classifier.classify_schema_change(
                            path, method, prop_name, "type_changed"
                        )
                    )

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
                        path, method, status_code, "removed"
                    )
                )

        # Added responses
        for status_code in new_responses:
            if status_code not in old_responses:
                self.changes.append(
                    Classifier.classify_response_change(
                        path, method, status_code, "added"
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
        for content_type, content_spec in content.items():
            schema = content_spec.get("schema", {})
            if schema:
                return schema
        return {}
