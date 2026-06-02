"""
Unit tests for the Normalizer class.
"""

import pytest
from app.core.normalizer import Normalizer


class TestNormalize:
    """Tests for the main normalize method."""

    def test_normalize_swagger_2(self):
        """Test normalizing a Swagger 2.0 spec."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "host": "api.example.com",
            "basePath": "/v1",
            "schemes": ["https"],
            "paths": {},
            "definitions": {}
        }
        
        result = Normalizer.normalize(spec)
        
        assert result["version"] == "2.0"
        assert result["info"]["title"] == "Test API"
        assert result["servers"] == [{"url": "https://api.example.com/v1"}]
        assert "components" in result
        assert "paths" in result

    def test_normalize_openapi_3(self):
        """Test normalizing an OpenAPI 3.x spec."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com/v1"}],
            "paths": {},
            "components": {}
        }
        
        result = Normalizer.normalize(spec)
        
        assert result["version"] == "3.0.0"
        assert result["info"]["title"] == "Test API"
        assert result["servers"] == [{"url": "https://api.example.com/v1"}]
        assert "components" in result
        assert "paths" in result

    def test_normalize_openapi_3_nullable_component_schema(self):
        """Test that OpenAPI 3.0 nullable is normalized in components."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "nickname": {"type": "string", "nullable": True}
                        },
                    }
                }
            },
        }

        result = Normalizer.normalize(spec)

        nickname = result["components"]["schemas"]["User"]["properties"]["nickname"]
        assert nickname == {"type": ["string", "null"]}

    def test_normalize_unknown_format(self):
        """Test that unknown format raises ValueError."""
        spec = {"unknown": "format"}
        
        with pytest.raises(ValueError, match="Unknown specification format"):
            Normalizer.normalize(spec)


class TestConvertToServers:
    """Tests for _convert_to_servers method."""

    def test_convert_single_scheme(self):
        """Test converting with a single scheme."""
        result = Normalizer._convert_to_servers(
            "api.example.com",
            "/v1",
            ["https"]
        )
        
        assert result == [{"url": "https://api.example.com/v1"}]

    def test_convert_multiple_schemes(self):
        """Test converting with multiple schemes."""
        result = Normalizer._convert_to_servers(
            "api.example.com",
            "/v1",
            ["https", "http"]
        )
        
        assert len(result) == 2
        assert {"url": "https://api.example.com/v1"} in result
        assert {"url": "http://api.example.com/v1"} in result

    def test_convert_no_base_path(self):
        """Test converting without base path."""
        result = Normalizer._convert_to_servers(
            "api.example.com",
            "",
            ["https"]
        )
        
        assert result == [{"url": "https://api.example.com"}]

    def test_convert_no_host(self):
        """Test that empty host returns empty list."""
        result = Normalizer._convert_to_servers("", "/v1", ["https"])
        
        assert result == []

    def test_convert_with_port(self):
        """Test converting with port in host."""
        result = Normalizer._convert_to_servers(
            "api.example.com:8080",
            "/v1",
            ["https"]
        )
        
        assert result == [{"url": "https://api.example.com:8080/v1"}]


class TestNormalizePaths:
    """Tests for _normalize_paths method."""

    def test_normalize_empty_paths(self):
        """Test normalizing empty paths."""
        result = Normalizer._normalize_paths({}, is_openapi3=True)
        
        assert result == {}

    def test_normalize_simple_path_openapi3(self):
        """Test normalizing a simple path for OpenAPI 3."""
        paths = {
            "/users": {
                "get": {
                    "summary": "Get users",
                    "responses": {"200": {"description": "Success"}}
                }
            }
        }
        
        result = Normalizer._normalize_paths(paths, is_openapi3=True)
        
        assert "/users" in result
        assert "get" in result["/users"]
        assert result["/users"]["get"]["summary"] == "Get users"

    def test_normalize_path_with_path_params_swagger2(self):
        """Test normalizing path with path-level parameters for Swagger 2.0."""
        paths = {
            "/users/{userId}": {
                "parameters": [
                    {
                        "name": "userId",
                        "in": "path",
                        "type": "string",
                        "required": True
                    }
                ],
                "get": {
                    "summary": "Get user",
                    "responses": {"200": {"description": "Success"}}
                }
            }
        }
        
        result = Normalizer._normalize_paths(paths, is_openapi3=False)
        
        assert "/users/{userId}" in result
        assert "get" in result["/users/{userId}"]
        params = result["/users/{userId}"]["get"]["parameters"]
        assert len(params) == 1
        assert params[0]["name"] == "userId"
        assert params[0]["schema"]["type"] == "string"

    def test_normalize_multiple_methods(self):
        """Test normalizing path with multiple HTTP methods."""
        paths = {
            "/users": {
                "get": {"summary": "Get users", "responses": {}},
                "post": {"summary": "Create user", "responses": {}},
                "put": {"summary": "Update user", "responses": {}}
            }
        }
        
        result = Normalizer._normalize_paths(paths, is_openapi3=True)
        
        assert len(result["/users"]) == 3
        assert "get" in result["/users"]
        assert "post" in result["/users"]
        assert "put" in result["/users"]

    def test_normalize_ignores_non_http_methods(self):
        """Test that non-HTTP method keys are ignored."""
        paths = {
            "/users": {
                "get": {"summary": "Get users", "responses": {}},
                "parameters": [],
                "servers": [],
                "summary": "User operations"
            }
        }
        
        result = Normalizer._normalize_paths(paths, is_openapi3=True)
        
        assert "get" in result["/users"]
        assert "parameters" not in result["/users"]
        assert "servers" not in result["/users"]
        assert "summary" not in result["/users"]


class TestNormalizeOperation:
    """Tests for _normalize_operation method."""

    def test_normalize_basic_operation(self):
        """Test normalizing a basic operation."""
        operation = {
            "summary": "Get user",
            "description": "Retrieve a user by ID",
            "operationId": "getUser",
            "tags": ["users"],
            "responses": {}
        }
        
        result = Normalizer._normalize_operation(operation, [], is_openapi3=True)
        
        assert result["summary"] == "Get user"
        assert result["description"] == "Retrieve a user by ID"
        assert result["operationId"] == "getUser"
        assert result["tags"] == ["users"]
        assert result["deprecated"] == False
        assert result["security"] == []

    def test_normalize_operation_with_path_params(self):
        """Test that path-level parameters are merged."""
        operation = {
            "summary": "Get user",
            "parameters": [
                {"name": "limit", "in": "query", "schema": {"type": "integer"}}
            ],
            "responses": {}
        }
        path_params = [
            {"name": "userId", "in": "path", "schema": {"type": "string"}}
        ]
        
        result = Normalizer._normalize_operation(operation, path_params, is_openapi3=True)
        
        assert len(result["parameters"]) == 2
        assert result["parameters"][0]["name"] == "userId"
        assert result["parameters"][1]["name"] == "limit"

    def test_normalize_operation_swagger2_body_param(self):
        """Test converting Swagger 2.0 body parameter to requestBody."""
        operation = {
            "summary": "Create user",
            "parameters": [
                {
                    "in": "body",
                    "name": "body",
                    "required": True,
                    "schema": {"type": "object"}
                }
            ],
            "consumes": ["application/json"],
            "responses": {}
        }
        
        result = Normalizer._normalize_operation(operation, [], is_openapi3=False)
        
        assert "requestBody" in result
        assert result["requestBody"]["required"] == True
        assert "application/json" in result["requestBody"]["content"]
        assert result["requestBody"]["content"]["application/json"]["schema"]["type"] == "object"
        # Body parameter should not be in parameters list
        assert len(result["parameters"]) == 0

    def test_normalize_operation_openapi3_requestbody(self):
        """Test that OpenAPI 3.x requestBody is preserved."""
        operation = {
            "summary": "Create user",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"type": "object"}
                    }
                }
            },
            "responses": {}
        }
        
        result = Normalizer._normalize_operation(operation, [], is_openapi3=True)
        
        assert "requestBody" in result
        assert result["requestBody"]["required"] == True

    def test_normalize_operation_openapi3_nullable_requestbody(self):
        """Test normalizing nullable schemas inside OpenAPI 3 request bodies."""
        operation = {
            "summary": "Create user",
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "nickname": {"type": "string", "nullable": True}
                            },
                        }
                    }
                }
            },
            "responses": {},
        }

        result = Normalizer._normalize_operation(operation, [], is_openapi3=True)
        schema = result["requestBody"]["content"]["application/json"]["schema"]

        assert schema["properties"]["nickname"] == {"type": ["string", "null"]}

    def test_normalize_operation_with_security(self):
        """Test normalizing operation with security."""
        operation = {
            "summary": "Get user",
            "security": [{"api_key": []}],
            "responses": {}
        }
        
        result = Normalizer._normalize_operation(operation, [], is_openapi3=True)
        
        assert result["security"] == [{"api_key": []}]

    def test_normalize_operation_deprecated(self):
        """Test normalizing deprecated operation."""
        operation = {
            "summary": "Old endpoint",
            "deprecated": True,
            "responses": {}
        }
        
        result = Normalizer._normalize_operation(operation, [], is_openapi3=True)
        
        assert result["deprecated"] == True


class TestNormalizeParameter:
    """Tests for _normalize_parameter method."""

    def test_normalize_openapi3_parameter(self):
        """Test normalizing OpenAPI 3.x parameter (already has schema)."""
        param = {
            "name": "limit",
            "in": "query",
            "description": "Max items to return",
            "required": False,
            "schema": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100
            }
        }
        
        result = Normalizer._normalize_parameter(param, is_openapi3=True)
        
        assert result["name"] == "limit"
        assert result["in"] == "query"
        assert result["description"] == "Max items to return"
        assert result["required"] == False
        assert result["schema"]["type"] == "integer"
        assert result["schema"]["minimum"] == 1

    def test_normalize_openapi3_nullable_parameter(self):
        """Test normalizing OpenAPI 3.0 nullable parameter schemas."""
        param = {
            "name": "status",
            "in": "query",
            "schema": {"type": "string", "nullable": True},
        }

        result = Normalizer._normalize_parameter(param, is_openapi3=True)

        assert result["schema"] == {"type": ["string", "null"]}

    def test_normalize_swagger2_parameter(self):
        """Test normalizing Swagger 2.0 parameter (needs schema wrapper)."""
        param = {
            "name": "limit",
            "in": "query",
            "description": "Max items",
            "required": False,
            "type": "integer",
            "minimum": 1,
            "maximum": 100
        }
        
        result = Normalizer._normalize_parameter(param, is_openapi3=False)
        
        assert result["name"] == "limit"
        assert result["in"] == "query"
        assert result["schema"]["type"] == "integer"
        assert result["schema"]["minimum"] == 1
        assert result["schema"]["maximum"] == 100

    def test_normalize_swagger2_array_parameter(self):
        """Test normalizing Swagger 2.0 array parameter."""
        param = {
            "name": "tags",
            "in": "query",
            "type": "array",
            "items": {"type": "string"},
            "collectionFormat": "csv"
        }
        
        result = Normalizer._normalize_parameter(param, is_openapi3=False)
        
        assert result["schema"]["type"] == "array"
        assert result["schema"]["items"]["type"] == "string"
        assert result["schema"]["collectionFormat"] == "csv"

    def test_normalize_parameter_with_enum(self):
        """Test normalizing parameter with enum."""
        param = {
            "name": "status",
            "in": "query",
            "type": "string",
            "enum": ["active", "inactive"]
        }
        
        result = Normalizer._normalize_parameter(param, is_openapi3=False)
        
        assert result["schema"]["enum"] == ["active", "inactive"]

    def test_normalize_parameter_path_required(self):
        """Test normalizing path parameter."""
        param = {
            "name": "userId",
            "in": "path",
            "required": True,
            "type": "string"
        }
        
        result = Normalizer._normalize_parameter(param, is_openapi3=False)
        
        assert result["in"] == "path"
        assert result["required"] == True


class TestConvertBodyParamToRequestBody:
    """Tests for _convert_body_param_to_request_body method."""

    def test_convert_simple_body_param(self):
        """Test converting simple body parameter."""
        body_param = {
            "description": "User object",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                }
            }
        }
        consumes = ["application/json"]
        
        result = Normalizer._convert_body_param_to_request_body(body_param, consumes)
        
        assert result["description"] == "User object"
        assert result["required"] == True
        assert "application/json" in result["content"]
        assert result["content"]["application/json"]["schema"]["type"] == "object"

    def test_convert_body_param_multiple_media_types(self):
        """Test converting body parameter with multiple media types."""
        body_param = {
            "schema": {"type": "object"}
        }
        consumes = ["application/json", "application/xml"]
        
        result = Normalizer._convert_body_param_to_request_body(body_param, consumes)
        
        assert len(result["content"]) == 2
        assert "application/json" in result["content"]
        assert "application/xml" in result["content"]

    def test_convert_body_param_optional(self):
        """Test converting optional body parameter."""
        body_param = {
            "required": False,
            "schema": {"type": "object"}
        }
        consumes = ["application/json"]
        
        result = Normalizer._convert_body_param_to_request_body(body_param, consumes)
        
        assert result["required"] == False


class TestNormalizeResponses:
    """Tests for _normalize_responses method."""

    def test_normalize_openapi3_responses(self):
        """Test normalizing OpenAPI 3.x responses (already has content)."""
        responses = {
            "200": {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {"type": "object"}
                    }
                }
            }
        }
        
        result = Normalizer._normalize_responses(responses, [], is_openapi3=True)
        
        assert "200" in result
        assert result["200"]["description"] == "Success"
        assert "application/json" in result["200"]["content"]

    def test_normalize_openapi3_nullable_response_schema(self):
        """Test normalizing nullable schemas inside OpenAPI 3 responses."""
        responses = {
            "200": {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "nickname": {"type": "string", "nullable": True}
                            },
                        }
                    }
                },
            }
        }

        result = Normalizer._normalize_responses(responses, [], is_openapi3=True)
        schema = result["200"]["content"]["application/json"]["schema"]

        assert schema["properties"]["nickname"] == {"type": ["string", "null"]}

    def test_normalize_swagger2_responses(self):
        """Test normalizing Swagger 2.0 responses (needs content wrapper)."""
        responses = {
            "200": {
                "description": "Success",
                "schema": {"type": "object"}
            }
        }
        produces = ["application/json"]
        
        result = Normalizer._normalize_responses(responses, produces, is_openapi3=False)
        
        assert "200" in result
        assert "content" in result["200"]
        assert "application/json" in result["200"]["content"]
        assert result["200"]["content"]["application/json"]["schema"]["type"] == "object"

    def test_normalize_responses_multiple_media_types(self):
        """Test normalizing responses with multiple media types."""
        responses = {
            "200": {
                "description": "Success",
                "schema": {"type": "object"}
            }
        }
        produces = ["application/json", "application/xml"]
        
        result = Normalizer._normalize_responses(responses, produces, is_openapi3=False)
        
        assert len(result["200"]["content"]) == 2
        assert "application/json" in result["200"]["content"]
        assert "application/xml" in result["200"]["content"]

    def test_normalize_responses_with_headers(self):
        """Test normalizing responses with headers."""
        responses = {
            "200": {
                "description": "Success",
                "schema": {"type": "object"},
                "headers": {
                    "X-Rate-Limit": {"type": "integer"}
                }
            }
        }
        
        result = Normalizer._normalize_responses(responses, ["application/json"], is_openapi3=False)
        
        assert "headers" in result["200"]
        assert "X-Rate-Limit" in result["200"]["headers"]

    def test_normalize_multiple_status_codes(self):
        """Test normalizing multiple response status codes."""
        responses = {
            "200": {"description": "Success", "schema": {"type": "object"}},
            "404": {"description": "Not found"},
            "500": {"description": "Server error"}
        }
        
        result = Normalizer._normalize_responses(responses, ["application/json"], is_openapi3=False)
        
        assert len(result) == 3
        assert "200" in result
        assert "404" in result
        assert "500" in result

    def test_normalize_response_no_schema(self):
        """Test normalizing response without schema."""
        responses = {
            "204": {"description": "No content"}
        }
        
        result = Normalizer._normalize_responses(responses, ["application/json"], is_openapi3=False)
        
        assert result["204"]["description"] == "No content"
        assert "content" not in result["204"]


class TestExtractParameters:
    """Tests for extract_parameters method."""

    def test_extract_no_parameters(self):
        """Test extracting from operation with no parameters."""
        operation = {"parameters": []}
        
        result = Normalizer.extract_parameters(operation)
        
        assert result == {
            "query": {},
            "path": {},
            "header": {},
            "cookie": {}
        }

    def test_extract_query_parameters(self):
        """Test extracting query parameters."""
        operation = {
            "parameters": [
                {
                    "name": "limit",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer"},
                    "description": "Max items"
                },
                {
                    "name": "offset",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer"}
                }
            ]
        }
        
        result = Normalizer.extract_parameters(operation)
        
        assert len(result["query"]) == 2
        assert "limit" in result["query"]
        assert "offset" in result["query"]
        assert result["query"]["limit"]["schema"]["type"] == "integer"

    def test_extract_path_parameters(self):
        """Test extracting path parameters."""
        operation = {
            "parameters": [
                {
                    "name": "userId",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"}
                }
            ]
        }
        
        result = Normalizer.extract_parameters(operation)
        
        assert len(result["path"]) == 1
        assert "userId" in result["path"]
        assert result["path"]["userId"]["required"] == True

    def test_extract_header_parameters(self):
        """Test extracting header parameters."""
        operation = {
            "parameters": [
                {
                    "name": "X-API-Key",
                    "in": "header",
                    "required": True,
                    "schema": {"type": "string"}
                }
            ]
        }
        
        result = Normalizer.extract_parameters(operation)
        
        assert len(result["header"]) == 1
        assert "X-API-Key" in result["header"]

    def test_extract_mixed_parameters(self):
        """Test extracting mixed parameter types."""
        operation = {
            "parameters": [
                {"name": "userId", "in": "path", "schema": {"type": "string"}},
                {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                {"name": "X-API-Key", "in": "header", "schema": {"type": "string"}}
            ]
        }
        
        result = Normalizer.extract_parameters(operation)
        
        assert len(result["path"]) == 1
        assert len(result["query"]) == 1
        assert len(result["header"]) == 1


class TestExtractResponses:
    """Tests for extract_responses method."""

    def test_extract_responses(self):
        """Test extracting responses."""
        operation = {
            "responses": {
                "200": {"description": "Success"},
                "404": {"description": "Not found"}
            }
        }
        
        result = Normalizer.extract_responses(operation)
        
        assert len(result) == 2
        assert "200" in result
        assert "404" in result

    def test_extract_no_responses(self):
        """Test extracting from operation with no responses."""
        operation = {}
        
        result = Normalizer.extract_responses(operation)
        
        assert result == {}


class TestExtractRequestBody:
    """Tests for extract_request_body method."""

    def test_extract_request_body(self):
        """Test extracting request body."""
        operation = {
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"type": "object"}
                    }
                }
            }
        }
        
        result = Normalizer.extract_request_body(operation)
        
        assert result is not None
        assert result["required"] == True
        assert "application/json" in result["content"]

    def test_extract_no_request_body(self):
        """Test extracting from operation with no request body."""
        operation = {}
        
        result = Normalizer.extract_request_body(operation)
        
        assert result is None


class TestIntegration:
    """Integration tests for complete normalization flows."""

    def test_full_swagger2_normalization(self):
        """Test complete Swagger 2.0 normalization."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "host": "api.example.com",
            "basePath": "/v1",
            "schemes": ["https"],
            "paths": {
                "/users/{userId}": {
                    "parameters": [
                        {"name": "userId", "in": "path", "type": "string", "required": True}
                    ],
                    "get": {
                        "summary": "Get user",
                        "produces": ["application/json"],
                        "responses": {
                            "200": {
                                "description": "Success",
                                "schema": {"type": "object"}
                            }
                        }
                    },
                    "put": {
                        "summary": "Update user",
                        "consumes": ["application/json"],
                        "parameters": [
                            {
                                "in": "body",
                                "name": "body",
                                "required": True,
                                "schema": {"type": "object"}
                            }
                        ],
                        "responses": {
                            "200": {"description": "Updated"}
                        }
                    }
                }
            },
            "definitions": {
                "User": {"type": "object"}
            },
            "securityDefinitions": {
                "api_key": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
            }
        }
        
        result = Normalizer.normalize(spec)
        
        # Check version and info
        assert result["version"] == "2.0"
        assert result["info"]["title"] == "Test API"
        
        # Check servers conversion
        assert result["servers"] == [{"url": "https://api.example.com/v1"}]
        
        # Check components conversion
        assert "User" in result["components"]["schemas"]
        assert "api_key" in result["components"]["securitySchemes"]
        
        # Check path normalization
        assert "/users/{userId}" in result["paths"]
        
        # Check GET operation
        get_op = result["paths"]["/users/{userId}"]["get"]
        assert get_op["summary"] == "Get user"
        assert len(get_op["parameters"]) == 1
        assert get_op["parameters"][0]["name"] == "userId"
        assert get_op["parameters"][0]["schema"]["type"] == "string"
        assert "200" in get_op["responses"]
        assert "application/json" in get_op["responses"]["200"]["content"]
        
        # Check PUT operation
        put_op = result["paths"]["/users/{userId}"]["put"]
        assert put_op["summary"] == "Update user"
        assert "requestBody" in put_op
        assert put_op["requestBody"]["required"] == True
        assert "application/json" in put_op["requestBody"]["content"]

    def test_full_openapi3_normalization(self):
        """Test complete OpenAPI 3.x normalization."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com/v1"}],
            "paths": {
                "/users/{userId}": {
                    "parameters": [
                        {
                            "name": "userId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "get": {
                        "summary": "Get user",
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {"type": "object"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "User": {"type": "object"}
                }
            }
        }
        
        result = Normalizer.normalize(spec)
        
        # Check version and info
        assert result["version"] == "3.0.0"
        assert result["info"]["title"] == "Test API"
        
        # Check servers preserved
        assert result["servers"] == [{"url": "https://api.example.com/v1"}]
        
        # Check components preserved
        assert "User" in result["components"]["schemas"]
        
        # Check path normalization
        get_op = result["paths"]["/users/{userId}"]["get"]
        assert get_op["summary"] == "Get user"
        assert len(get_op["parameters"]) == 1
        assert get_op["parameters"][0]["name"] == "userId"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_normalize_spec_without_paths(self):
        """Test normalizing spec without paths."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
        }
        
        result = Normalizer.normalize(spec)
        
        assert result["paths"] == {}
        assert result["servers"] == []

    def test_normalize_swagger2_without_definitions(self):
        """Test Swagger 2.0 without definitions."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {}
        }
        
        result = Normalizer.normalize(spec)
        
        assert result["components"]["schemas"] == {}
        assert result["components"]["securitySchemes"] == {}

    def test_extract_parameters_with_cookie(self):
        """Test extracting cookie parameters."""
        operation = {
            "parameters": [
                {
                    "name": "session_id",
                    "in": "cookie",
                    "required": True,
                    "schema": {"type": "string"}
                }
            ]
        }
        
        result = Normalizer.extract_parameters(operation)
        
        assert len(result["cookie"]) == 1
        assert "session_id" in result["cookie"]

    def test_normalize_operation_without_optional_fields(self):
        """Test normalizing operation with minimal fields."""
        operation = {
            "responses": {"200": {"description": "OK"}}
        }
        
        result = Normalizer._normalize_operation(operation, [], is_openapi3=True)
        
        assert result["summary"] == ""
        assert result["description"] == ""
        assert result["operationId"] == ""
        assert result["tags"] == []
        assert result["deprecated"] == False
        assert result["security"] == []
        assert result["parameters"] == []

    def test_normalize_parameter_with_all_constraints(self):
        """Test normalizing parameter with all constraints."""
        param = {
            "name": "age",
            "in": "query",
            "type": "integer",
            "minimum": 0,
            "maximum": 120,
            "default": 18,
            "format": "int32"
        }
        
        result = Normalizer._normalize_parameter(param, is_openapi3=False)
        
        assert result["schema"]["type"] == "integer"
        assert result["schema"]["minimum"] == 0
        assert result["schema"]["maximum"] == 120
        assert result["schema"]["default"] == 18
        assert result["schema"]["format"] == "int32"

    def test_normalize_parameter_with_pattern(self):
        """Test normalizing parameter with pattern."""
        param = {
            "name": "email",
            "in": "query",
            "type": "string",
            "pattern": "^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$",
            "minLength": 5,
            "maxLength": 100
        }
        
        result = Normalizer._normalize_parameter(param, is_openapi3=False)
        
        assert result["schema"]["pattern"] == "^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$"
        assert result["schema"]["minLength"] == 5
        assert result["schema"]["maxLength"] == 100

    def test_normalize_array_parameter_with_constraints(self):
        """Test normalizing array parameter with constraints."""
        param = {
            "name": "ids",
            "in": "query",
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 1,
            "maxItems": 10
        }
        
        result = Normalizer._normalize_parameter(param, is_openapi3=False)
        
        assert result["schema"]["type"] == "array"
        assert result["schema"]["minItems"] == 1
        assert result["schema"]["maxItems"] == 10

    def test_convert_servers_with_multiple_schemes(self):
        """Test server conversion preserves order."""
        result = Normalizer._convert_to_servers(
            "api.example.com",
            "/v2",
            ["https", "http", "ws"]
        )
        
        assert len(result) == 3
        assert result[0]["url"] == "https://api.example.com/v2"
        assert result[1]["url"] == "http://api.example.com/v2"
        assert result[2]["url"] == "ws://api.example.com/v2"

    def test_normalize_paths_openapi3_with_path_params(self):
        """Test OpenAPI 3.x path-level parameters are preserved."""
        paths = {
            "/items/{itemId}": {
                "parameters": [
                    {
                        "name": "itemId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"}
                    }
                ],
                "get": {
                    "summary": "Get item",
                    "responses": {"200": {"description": "Success"}}
                }
            }
        }
        
        result = Normalizer._normalize_paths(paths, is_openapi3=True)
        
        # Path parameters should be merged into operation
        assert len(result["/items/{itemId}"]["get"]["parameters"]) == 1
        assert result["/items/{itemId}"]["get"]["parameters"][0]["name"] == "itemId"

    def test_swagger2_body_param_with_multiple_consumes(self):
        """Test Swagger 2.0 body parameter with multiple content types."""
        operation = {
            "parameters": [
                {
                    "in": "body",
                    "name": "body",
                    "schema": {"type": "object"}
                }
            ],
            "consumes": ["application/json", "application/xml", "application/x-www-form-urlencoded"],
            "responses": {}
        }
        
        result = Normalizer._normalize_operation(operation, [], is_openapi3=False)
        
        assert len(result["requestBody"]["content"]) == 3
        assert "application/json" in result["requestBody"]["content"]
        assert "application/xml" in result["requestBody"]["content"]
        assert "application/x-www-form-urlencoded" in result["requestBody"]["content"]

    def test_response_without_content_type(self):
        """Test response without schema (like 204 No Content)."""
        responses = {
            "204": {"description": "No Content"},
            "304": {"description": "Not Modified"}
        }
        
        result = Normalizer._normalize_responses(responses, ["application/json"], is_openapi3=False)
        
        assert "204" in result
        assert "304" in result
        assert "content" not in result["204"]
        assert "content" not in result["304"]

    def test_normalize_operation_with_multiple_body_and_query_params(self):
        """Test operation with both body and query parameters."""
        operation = {
            "parameters": [
                {"name": "force", "in": "query", "type": "boolean"},
                {"in": "body", "name": "body", "schema": {"type": "object"}}
            ],
            "consumes": ["application/json"],
            "responses": {}
        }
        
        result = Normalizer._normalize_operation(operation, [], is_openapi3=False)
        
        # Query parameter should be in parameters
        assert len(result["parameters"]) == 1
        assert result["parameters"][0]["name"] == "force"
        # Body should be in requestBody
        assert "requestBody" in result

    def test_path_and_operation_params_no_duplicates(self):
        """Test that path and operation parameters don't create duplicates."""
        path_params = [
            {"name": "userId", "in": "path", "schema": {"type": "string"}}
        ]
        operation = {
            "parameters": [
                {"name": "include", "in": "query", "schema": {"type": "string"}}
            ],
            "responses": {}
        }
        
        result = Normalizer._normalize_operation(operation, path_params, is_openapi3=True)
        
        assert len(result["parameters"]) == 2
        # Path params come first
        assert result["parameters"][0]["name"] == "userId"
        assert result["parameters"][1]["name"] == "include"

    def test_operation_with_empty_consumes_produces(self):
        """Test operation without consumes/produces uses defaults."""
        operation = {
            "parameters": [
                {"in": "body", "name": "body", "schema": {"type": "object"}}
            ],
            "responses": {
                "200": {"description": "Success", "schema": {"type": "object"}}
            }
        }
        
        result = Normalizer._normalize_operation(operation, [], is_openapi3=False)
        
        # Should default to application/json
        assert "application/json" in result["requestBody"]["content"]
        assert "application/json" in result["responses"]["200"]["content"]

    def test_extract_parameters_with_empty_operation(self):
        """Test extracting parameters from operation without parameters key."""
        operation = {"responses": {}}
        
        result = Normalizer.extract_parameters(operation)
        
        assert result["query"] == {}
        assert result["path"] == {}
        assert result["header"] == {}
        assert result["cookie"] == {}

    def test_normalize_response_with_both_schema_and_headers(self):
        """Test response with both schema and headers."""
        responses = {
            "200": {
                "description": "Success",
                "schema": {"type": "array"},
                "headers": {
                    "X-Total-Count": {"type": "integer"},
                    "X-Page-Number": {"type": "integer"}
                }
            }
        }
        
        result = Normalizer._normalize_responses(responses, ["application/json"], is_openapi3=False)
        
        assert "content" in result["200"]
        assert "headers" in result["200"]
        assert len(result["200"]["headers"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
