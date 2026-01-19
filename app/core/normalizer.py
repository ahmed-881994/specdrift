"""
Specification normalizer.

Normalizes OpenAPI v3 and Swagger v2 specifications to a common structure
for consistent diffing.
"""

from typing import Any, Dict, List, Optional


class Normalizer:
    """Normalizes API specifications to a common format."""

    @staticmethod
    def normalize(spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize specification to common structure.
        
        Args:
            spec: The parsed specification
            
        Returns:
            Normalized specification
        """
        is_swagger_2 = "swagger" in spec
        is_openapi_3 = "openapi" in spec

        if is_swagger_2:
            return Normalizer._normalize_swagger_2(spec)
        elif is_openapi_3:
            return Normalizer._normalize_openapi_3(spec)
        else:
            return spec

    @staticmethod
    def _normalize_openapi_3(spec: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize OpenAPI 3.x specification."""
        normalized = {
            "version": spec.get("openapi", "3.0.0"),
            "info": spec.get("info", {}),
            "paths": Normalizer._normalize_paths_openapi3(spec.get("paths", {})),
            "components": spec.get("components", {}),
        }
        return normalized

    @staticmethod
    def _normalize_swagger_2(spec: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Swagger 2.0 specification."""
        normalized = {
            "version": spec.get("swagger", "2.0"),
            "info": spec.get("info", {}),
            "paths": Normalizer._normalize_paths_swagger2(spec.get("paths", {})),
            "definitions": spec.get("definitions", {}),
        }
        return normalized

    @staticmethod
    def _normalize_paths_openapi3(paths: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize OpenAPI 3.x paths."""
        normalized = {}
        for path, path_item in paths.items():
            normalized[path] = {}
            for method, operation in path_item.items():
                if method.lower() in ("get", "post", "put", "delete", "patch", "options", "head"):
                    normalized[path][method.lower()] = operation
        return normalized

    @staticmethod
    def _normalize_paths_swagger2(paths: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Swagger 2.0 paths."""
        normalized = {}
        for path, path_item in paths.items():
            normalized[path] = {}
            for method, operation in path_item.items():
                if method.lower() in ("get", "post", "put", "delete", "patch", "options", "head"):
                    normalized[path][method.lower()] = operation
        return normalized

    @staticmethod
    def extract_parameters(operation: Dict[str, Any], is_openapi3: bool = True) -> Dict[str, Any]:
        """
        Extract parameters from an operation.
        
        Args:
            operation: The operation object
            is_openapi3: Whether this is OpenAPI 3.x format
            
        Returns:
            Normalized parameters
        """
        params = {"query": {}, "path": {}, "header": {}, "body": {}}

        if is_openapi3:
            for param in operation.get("parameters", []):
                param_in = param.get("in")
                param_name = param.get("name")
                if param_in and param_name:
                    params[param_in][param_name] = {
                        "required": param.get("required", False),
                        "schema": param.get("schema", {}),
                    }

            request_body = operation.get("requestBody", {})
            if request_body:
                content = request_body.get("content", {})
                for content_type, content_spec in content.items():
                    schema = content_spec.get("schema", {})
                    params["body"][content_type] = {
                        "required": request_body.get("required", False),
                        "schema": schema,
                    }
        else:
            # Swagger 2.0
            for param in operation.get("parameters", []):
                param_in = param.get("in")
                param_name = param.get("name")
                if param_in and param_name:
                    params[param_in][param_name] = {
                        "required": param.get("required", False),
                        "type": param.get("type"),
                    }

        return params

    @staticmethod
    def extract_responses(operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract responses from an operation.
        
        Args:
            operation: The operation object
            
        Returns:
            Normalized responses
        """
        responses = {}
        for status_code, response in operation.get("responses", {}).items():
            responses[status_code] = response
        return responses
