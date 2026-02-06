"""
Specification normalizer.

Normalizes OpenAPI v3 and Swagger v2 specifications to a common structure
for consistent diffing.
"""

import json
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
            raise ValueError("Unknown specification format")

    @staticmethod
    def _normalize_openapi_3(spec: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize OpenAPI 3.x specification to common format."""
        normalized = {
            "version": spec.get("openapi", "3.0.0"),
            "info": spec.get("info", {}),
            "servers": spec.get("servers", []),
            "paths": Normalizer._normalize_paths(spec.get("paths", {}), is_openapi3=True),
            "components": spec.get("components", {}),
        }
        return normalized

    @staticmethod
    def _normalize_swagger_2(spec: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Swagger 2.0 specification to common format."""
        # Convert host + basePath to servers format
        servers = Normalizer._convert_to_servers(
            spec.get("host", ""),
            spec.get("basePath", ""),
            spec.get("schemes", ["https"])
        )
        
        # Convert definitions and securityDefinitions to components
        components = {
            "schemas": spec.get("definitions", {}),
            "securitySchemes": spec.get("securityDefinitions", {})
        }

        normalized = {
            "version": spec.get("swagger", "2.0"),
            "info": spec.get("info", {}),
            "servers": servers,
            "paths": Normalizer._normalize_paths(spec.get("paths", {}), is_openapi3=False),
            "components": components,
        }
        # print(f"Normalized Swagger 2.0 spec: {json.dumps(normalized, indent=None)}")
        return normalized

    @staticmethod
    def _convert_to_servers(host: str, base_path: str, schemes: List[str]) -> List[Dict[str, str]]:
        """
        Convert Swagger 2.0 host/basePath/schemes to OpenAPI 3.x servers format.

        Args:
            host: The host from Swagger 2.0
            base_path: The basePath from Swagger 2.0
            schemes: The schemes from Swagger 2.0

        Returns:
            List of server objects
        """
        if not host:
            return []
        
        servers = []
        for scheme in schemes:
            url = f"{scheme}://{host}{base_path}"
            servers.append({"url": url})
        
        return servers

    @staticmethod
    def _normalize_paths(paths: Dict[str, Any], is_openapi3: bool) -> Dict[str, Any]:
        """
        Normalize paths to common format.

        Args:
            paths: The paths object from the spec
            is_openapi3: Whether this is OpenAPI 3.x format

        Returns:
            Normalized paths
        """
        normalized = {}
        
        for path, path_item in paths.items():
            normalized[path] = {}
            
            # Extract path-level parameters
            path_params = path_item.get("parameters", [])
            
            # Normalize path-level parameters
            if path_params and not is_openapi3:
                path_params = [Normalizer._normalize_parameter(p, is_openapi3=False) for p in path_params]
            
            # Process each HTTP method
            for method in ["get", "post", "put", "delete", "patch", "options", "head"]:
                if method in path_item:
                    operation = path_item[method]
                    normalized_operation = Normalizer._normalize_operation(
                        operation, 
                        path_params, 
                        is_openapi3
                    )
                    normalized[path][method] = normalized_operation
        
        return normalized

    @staticmethod
    def _normalize_operation(
        operation: Dict[str, Any], 
        path_params: List[Dict[str, Any]], 
        is_openapi3: bool
    ) -> Dict[str, Any]:
        """
        Normalize an operation to common format.

        Args:
            operation: The operation object
            path_params: Path-level parameters to merge
            is_openapi3: Whether this is OpenAPI 3.x format

        Returns:
            Normalized operation
        """
        normalized = {
            "summary": operation.get("summary", ""),
            "description": operation.get("description", ""),
            "operationId": operation.get("operationId", ""),
            "tags": operation.get("tags", []),
            "deprecated": operation.get("deprecated", False),
            "security": operation.get("security", []),
        }

        # Normalize parameters
        op_params = operation.get("parameters", [])
        all_params = []
        
        # Add path-level parameters first
        all_params.extend(path_params)
        
        # Process operation-level parameters
        body_param = None
        consumes = operation.get("consumes", ["application/json"])
        
        for param in op_params:
            if not is_openapi3 and param.get("in") == "body":
                # Extract body parameter for Swagger 2.0
                body_param = param
            else:
                # Normalize non-body parameters
                normalized_param = Normalizer._normalize_parameter(param, is_openapi3)
                all_params.append(normalized_param)
        
        normalized["parameters"] = all_params

        # Handle request body
        if is_openapi3:
            if "requestBody" in operation:
                normalized["requestBody"] = operation["requestBody"]
        else:
            # Convert Swagger 2.0 body parameter to requestBody
            if body_param:
                normalized["requestBody"] = Normalizer._convert_body_param_to_request_body(
                    body_param, 
                    consumes
                )

        # Normalize responses
        normalized["responses"] = Normalizer._normalize_responses(
            operation.get("responses", {}),
            operation.get("produces", ["application/json"]),
            is_openapi3
        )

        return normalized

    @staticmethod
    def _normalize_parameter(param: Dict[str, Any], is_openapi3: bool) -> Dict[str, Any]:
        """
        Normalize a parameter to common format (always use schema wrapper).

        Args:
            param: The parameter object
            is_openapi3: Whether this is OpenAPI 3.x format

        Returns:
            Normalized parameter
        """
        normalized = {
            "name": param.get("name", ""),
            "in": param.get("in", ""),
            "description": param.get("description", ""),
            "required": param.get("required", False),
        }

        if is_openapi3:
            # Already has schema wrapper
            normalized["schema"] = param.get("schema", {})
        else:
            # Convert Swagger 2.0 format to schema wrapper
            schema = {}
            for key in ["type", "format", "items", "enum", "default", "minimum", "maximum", 
                       "minLength", "maxLength", "pattern", "minItems", "maxItems"]:
                if key in param:
                    schema[key] = param[key]
            
            # Handle collection format
            if "collectionFormat" in param:
                schema["collectionFormat"] = param["collectionFormat"]
            
            normalized["schema"] = schema

        return normalized

    @staticmethod
    def _convert_body_param_to_request_body(
        body_param: Dict[str, Any], 
        consumes: List[str]
    ) -> Dict[str, Any]:
        """
        Convert Swagger 2.0 body parameter to OpenAPI 3.x requestBody.

        Args:
            body_param: The body parameter from Swagger 2.0
            consumes: The consumes array

        Returns:
            RequestBody object
        """
        content = {}
        schema = body_param.get("schema", {})
        
        for media_type in consumes:
            content[media_type] = {"schema": schema}
        
        return {
            "description": body_param.get("description", ""),
            "required": body_param.get("required", False),
            "content": content
        }

    @staticmethod
    def _normalize_responses(
        responses: Dict[str, Any], 
        produces: List[str],
        is_openapi3: bool
    ) -> Dict[str, Any]:
        """
        Normalize responses to common format (always use content wrapper).

        Args:
            responses: The responses object
            produces: The produces array (Swagger 2.0)
            is_openapi3: Whether this is OpenAPI 3.x format

        Returns:
            Normalized responses
        """
        normalized = {}
        
        for status_code, response in responses.items():
            normalized_response = {
                "description": response.get("description", "")
            }

            if is_openapi3:
                # Already has content wrapper
                if "content" in response:
                    normalized_response["content"] = response["content"]
                if "headers" in response:
                    normalized_response["headers"] = response["headers"]
            else:
                # Convert Swagger 2.0 schema to content wrapper
                if "schema" in response:
                    content = {}
                    for media_type in produces:
                        content[media_type] = {
                            "schema": response["schema"]
                        }
                    normalized_response["content"] = content
                
                if "headers" in response:
                    normalized_response["headers"] = response["headers"]
            
            normalized[status_code] = normalized_response
        
        return normalized

    @staticmethod
    def extract_parameters(operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract parameters from a normalized operation.

        Args:
            operation: The normalized operation object

        Returns:
            Parameters organized by type
        """
        params = {
            "query": {},
            "path": {},
            "header": {},
            "cookie": {}
        }

        for param in operation.get("parameters", []):
            param_in = param.get("in", "")
            param_name = param.get("name", "")
            
            if param_in in params:
                params[param_in][param_name] = {
                    "required": param.get("required", False),
                    "schema": param.get("schema", {}),
                    "description": param.get("description", "")
                }

        return params

    @staticmethod
    def extract_responses(operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract responses from a normalized operation.

        Args:
            operation: The normalized operation object

        Returns:
            Normalized responses
        """
        return operation.get("responses", {})

    @staticmethod
    def extract_request_body(operation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract request body from a normalized operation.

        Args:
            operation: The normalized operation object

        Returns:
            Request body or None
        """
        return operation.get("requestBody")