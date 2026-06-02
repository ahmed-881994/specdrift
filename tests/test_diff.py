"""Unit tests for API diff logic."""

import pytest
from app.core.differ import Differ
from app.models.change import Change, DiffResult


class TestDiffer:
    """Tests for the Differ class."""

    def test_diff_returns_diff_result(self):
        """Test that diff() returns a DiffResult object."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {},
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {},
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        assert isinstance(result, DiffResult)
        assert "summary" in result.to_dict()
        assert "changes" in result.to_dict()

    def test_extract_version_with_title(self):
        """Test version extraction with title and version."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "My API", "version": "2.1.0"},
            "paths": {},
        }

        version = Differ._extract_version(spec)
        assert version == "My API v2.1.0"

    def test_extract_version_without_title(self):
        """Test version extraction with only version."""
        spec = {
            "openapi": "3.0.0",
            "info": {"version": "1.5.2"},
            "paths": {},
        }

        version = Differ._extract_version(spec)
        assert version == "v1.5.2"

    def test_extract_version_missing(self):
        """Test version extraction when version is missing."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "My API"},
            "paths": {},
        }

        version = Differ._extract_version(spec)
        assert version is None

    def test_create_summary(self):
        """Test summary creation."""
        differ = Differ()
        differ.changes = [
            Change(category="endpoint", type="breaking", message="", path="/test"),
            Change(category="endpoint", type="breaking", message="", path="/test"),
            Change(
                category="endpoint",
                type="potentially_breaking",
                message="",
                path="/test",
            ),
            Change(category="endpoint", type="non_breaking", message="", path="/test"),
        ]

        summary = differ._create_summary()

        assert summary["breaking"] == 2
        assert summary["potentially_breaking"] == 1
        assert summary["non_breaking"] == 1
        assert summary["total"] == 4

    def test_detect_removed_endpoint(self):
        """Test detection of removed endpoints."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {"get": {"responses": {"200": {"description": "OK"}}}},
                "/posts": {"get": {"responses": {"200": {"description": "OK"}}}},
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        endpoint_changes = [
            c
            for c in result.changes
            if c.category == "endpoint" and c.type == "breaking"
        ]
        assert len(endpoint_changes) == 1
        assert endpoint_changes[0].path == "/posts"

    def test_detect_added_endpoint(self):
        """Test detection of added endpoints."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {"get": {"responses": {"200": {"description": "OK"}}}},
                "/posts": {"get": {"responses": {"200": {"description": "OK"}}}},
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        endpoint_changes = [
            c
            for c in result.changes
            if c.category == "endpoint" and c.type == "non_breaking"
        ]
        assert len(endpoint_changes) == 1
        assert endpoint_changes[0].path == "/posts"

    def test_detect_removed_method(self):
        """Test detection of removed HTTP methods."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {"responses": {"200": {"description": "OK"}}},
                    "post": {"responses": {"201": {"description": "Created"}}},
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        method_changes = [
            c for c in result.changes if c.category == "method" and c.type == "breaking"
        ]
        assert len(method_changes) == 1
        assert method_changes[0].method == "POST"

    def test_detect_added_method(self):
        """Test detection of added HTTP methods."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {"responses": {"200": {"description": "OK"}}},
                    "post": {"responses": {"201": {"description": "Created"}}},
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        method_changes = [
            c
            for c in result.changes
            if c.category == "method" and c.type == "non_breaking"
        ]
        assert len(method_changes) == 1
        assert method_changes[0].method == "POST"

    def test_detect_removed_parameter(self):
        """Test detection of removed parameters."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {"name": "id", "in": "query", "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        param_changes = [
            c
            for c in result.changes
            if c.category == "parameter" and c.type == "breaking"
        ]
        assert len(param_changes) == 1
        assert param_changes[0].field_name == "id"
        assert param_changes[0].details.get("location") == "query"

    def test_detect_added_required_parameter(self):
        """Test detection of added required parameters."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "id",
                                "in": "query",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        param_changes = [
            c
            for c in result.changes
            if c.category == "parameter" and c.type == "breaking"
        ]
        assert len(param_changes) == 1
        assert param_changes[0].details.get("required") is True
        assert param_changes[0].details.get("location") == "query"

    def test_detect_added_optional_parameter(self):
        """Test detection of added optional parameters."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        param_changes = [
            c
            for c in result.changes
            if c.category == "parameter" and c.type == "non_breaking"
        ]
        assert len(param_changes) == 1
        assert param_changes[0].details.get("required") is False

    def test_detect_parameter_type_change(self):
        """Test detection of parameter type changes."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {"name": "id", "in": "query", "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {"name": "id", "in": "query", "schema": {"type": "integer"}}
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        param_changes = [
            c
            for c in result.changes
            if c.category == "parameter" and c.type == "breaking"
        ]
        assert len(param_changes) == 1
        assert param_changes[0].details.get("old_type") == "string"
        assert param_changes[0].details.get("new_type") == "integer"

    def test_detect_openapi31_parameter_type_array_change(self):
        """Test comparing OpenAPI 3.1 type arrays as schema type sets."""
        old_spec = {
            "openapi": "3.1.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "id",
                                "in": "query",
                                "schema": {"type": ["string", "null"]},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.1.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "id",
                                "in": "query",
                                "schema": {"type": ["integer", "null"]},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        param_changes = [
            c
            for c in result.changes
            if c.category == "parameter" and c.type == "breaking"
        ]
        assert len(param_changes) == 1
        assert param_changes[0].details.get("old_type") == ["string", "null"]
        assert param_changes[0].details.get("new_type") == ["integer", "null"]

    def test_parameter_type_change_includes_reporting_details(self):
        """Test that parameter changes include stable reporting metadata."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users/{userId}": {
                    "get": {
                        "parameters": [
                            {
                                "name": "include/profile",
                                "in": "query",
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users/{userId}": {
                    "get": {
                        "parameters": [
                            {
                                "name": "include/profile",
                                "in": "query",
                                "schema": {"type": "boolean"},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.category == "parameter")
        assert change.details["schema_path"] == (
            "#/paths/~1users~1{userId}/get/parameters/query/include~1profile/schema/type"
        )
        assert change.details["keyword"] == "type"
        assert change.details["old_value"] == "string"
        assert change.details["new_value"] == "boolean"

    def test_detect_parameter_made_required(self):
        """Test detection of parameter made required."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {"name": "id", "in": "query", "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "id",
                                "in": "query",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        param_changes = [
            c
            for c in result.changes
            if c.category == "parameter" and "required" in c.message.lower()
        ]
        assert len(param_changes) == 1
        assert param_changes[0].type == "breaking"

    def test_detect_parameter_made_optional(self):
        """Test detection of parameter made optional."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "id",
                                "in": "query",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {"name": "id", "in": "query", "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        param_changes = [
            c
            for c in result.changes
            if c.category == "parameter" and "optional" in c.message.lower()
        ]
        assert len(param_changes) == 1
        assert param_changes[0].type == "potentially_breaking"

    def test_detect_removed_request_body(self):
        """Test detection of removed request body."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {"post": {"responses": {"201": {"description": "Created"}}}}
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        body_changes = [
            c
            for c in result.changes
            if c.category == "request_body" and c.type == "breaking"
        ]
        assert len(body_changes) == 1
        assert body_changes[0].details.get("content_type") == "application/json"

    def test_detect_added_required_request_body(self):
        """Test detection of added required request body."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {"post": {"responses": {"201": {"description": "Created"}}}}
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        body_changes = [
            c
            for c in result.changes
            if c.category == "request_body" and c.type == "breaking"
        ]
        assert len(body_changes) == 1
        assert body_changes[0].details.get("required") is True

    def test_detect_added_required_field(self):
        """Test detection of added required fields in request body."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"name": {"type": "string"}},
                                        "required": ["name"],
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "email": {"type": "string"},
                                        },
                                        "required": ["name", "email"],
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        schema_changes = [
            c for c in result.changes if c.category == "schema" and c.type == "breaking"
        ]
        assert len(schema_changes) == 1
        assert schema_changes[0].field_name == "email"
        assert schema_changes[0].details.get("required") is True
        assert schema_changes[0].details.get("location") == "request_body"

    def test_detect_field_type_change(self):
        """Test detection of field type changes."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"age": {"type": "string"}},
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"age": {"type": "integer"}},
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        schema_changes = [
            c
            for c in result.changes
            if c.category == "schema" and c.field_name == "age"
        ]
        assert len(schema_changes) == 1
        assert schema_changes[0].details.get("old_type") == "string"
        assert schema_changes[0].details.get("new_type") == "integer"

    def test_detect_openapi30_nullable_field_type_change(self):
        """Test that OpenAPI 3.0 nullable is compared as a type set."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"nickname": {"type": "string"}},
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "nickname": {
                                                "type": "string",
                                                "nullable": True,
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        schema_changes = [
            c
            for c in result.changes
            if c.category == "schema" and c.field_name == "nickname"
        ]
        assert len(schema_changes) == 1
        assert schema_changes[0].details.get("old_type") == "string"
        assert schema_changes[0].details.get("new_type") == ["string", "null"]

    def test_schema_change_includes_reporting_details(self):
        """Test that schema property changes include stable reporting metadata."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"age": {"type": "string"}},
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"age": {"type": "integer"}},
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.category == "schema")
        assert change.details["schema_path"] == (
            "#/paths/~1users/post/requestBody/content/application~1json/schema/properties/age/type"
        )
        assert change.details["keyword"] == "type"
        assert change.details["old_value"] == "string"
        assert change.details["new_value"] == "integer"

    def test_detect_nested_object_field_removal(self):
        """Test recursive detection of removed nested object fields."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "address": {
                                                "type": "object",
                                                "properties": {
                                                    "city": {"type": "string"},
                                                    "country": {"type": "string"},
                                                },
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "address": {
                                                "type": "object",
                                                "properties": {
                                                    "country": {"type": "string"}
                                                },
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.field_name == "address.city")
        assert change.type == "breaking"
        assert change.details["schema_path"] == (
            "#/paths/~1users/post/requestBody/content/application~1json/schema/"
            "properties/address/properties/city"
        )

    def test_detect_array_item_type_change(self):
        """Test recursive detection of array item schema changes."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "tags": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "tags": {
                                                "type": "array",
                                                "items": {"type": "integer"},
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.field_name == "tags[]")
        assert change.type == "breaking"
        assert change.details["schema_path"] == (
            "#/paths/~1users/post/requestBody/content/application~1json/schema/"
            "properties/tags/items/type"
        )
        assert change.details["old_value"] == "string"
        assert change.details["new_value"] == "integer"

    def test_detect_prefix_item_type_change(self):
        """Test recursive detection of tuple-style prefixItems changes."""
        old_spec = {
            "openapi": "3.1.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/points": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "point": {
                                                "type": "array",
                                                "prefixItems": [
                                                    {"type": "number"},
                                                    {"type": "number"},
                                                ],
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.1.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/points": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "point": {
                                                "type": "array",
                                                "prefixItems": [
                                                    {"type": "number"},
                                                    {"type": "string"},
                                                ],
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.field_name == "point[1]")
        assert change.type == "breaking"
        assert change.details["schema_path"] == (
            "#/paths/~1points/post/requestBody/content/application~1json/schema/"
            "properties/point/prefixItems/1/type"
        )

    def test_detect_additional_properties_value_type_change(self):
        """Test recursive detection of map value schema changes."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "metadata": {
                                                "type": "object",
                                                "additionalProperties": {
                                                    "type": "string"
                                                },
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "metadata": {
                                                "type": "object",
                                                "additionalProperties": {
                                                    "type": "integer"
                                                },
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.field_name == "metadata.*")
        assert change.type == "breaking"
        assert change.details["schema_path"] == (
            "#/paths/~1users/post/requestBody/content/application~1json/schema/"
            "properties/metadata/additionalProperties/type"
        )

    def test_detect_composed_schema_branch_change(self):
        """Test recursive detection inside composed schema branches."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "allOf": [
                                            {
                                                "type": "object",
                                                "properties": {
                                                    "id": {"type": "string"}
                                                },
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "allOf": [
                                            {
                                                "type": "object",
                                                "properties": {
                                                    "id": {"type": "integer"}
                                                },
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.field_name == "schema.allOf[0].id")
        assert change.type == "breaking"
        assert change.details["schema_path"] == (
            "#/paths/~1users/post/requestBody/content/application~1json/schema/"
            "allOf/0/properties/id/type"
        )

    def test_detect_request_enum_value_removed(self):
        """Test detection of removed enum values."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string",
                                                "enum": ["active", "inactive"],
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string",
                                                "enum": ["active"],
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.category == "schema_constraint")
        assert change.type == "breaking"
        assert change.field_name == "status"
        assert change.message == "Enum value removed"
        assert change.details["keyword"] == "enum"
        assert change.details["old_value"] == "inactive"
        assert change.details["schema_path"] == (
            "#/paths/~1users/post/requestBody/content/application~1json/schema/"
            "properties/status/enum"
        )

    def test_detect_enum_value_added(self):
        """Test detection of added enum values."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string",
                                                "enum": ["active"],
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string",
                                                "enum": ["active", "inactive"],
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.category == "schema_constraint")
        assert change.type == "potentially_breaking"
        assert change.message == "Enum value added"
        assert change.details["new_value"] == "inactive"

    def test_detect_default_value_removed(self):
        """Test detection of removed defaults."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "role": {
                                                "type": "string",
                                                "default": "reader",
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"role": {"type": "string"}},
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.category == "schema_constraint")
        assert change.type == "potentially_breaking"
        assert change.message == "Default value removed"
        assert change.details["keyword"] == "default"
        assert change.details["old_value"] == "reader"

    def test_detect_request_max_length_made_stricter(self):
        """Test detection of stricter validation constraints."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "maxLength": 100,
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "maxLength": 50,
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.category == "schema_constraint")
        assert change.type == "breaking"
        assert change.message == "Schema constraint made stricter"
        assert change.details["keyword"] == "maxLength"
        assert change.details["old_value"] == 100
        assert change.details["new_value"] == 50

    def test_detect_request_minimum_made_looser(self):
        """Test detection of looser validation constraints."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "age",
                                "in": "query",
                                "schema": {"type": "integer", "minimum": 18},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "age",
                                "in": "query",
                                "schema": {"type": "integer", "minimum": 13},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.category == "schema_constraint")
        assert change.type == "non_breaking"
        assert change.message == "Schema constraint made less restrictive"
        assert change.details["location"] == "parameter_query"
        assert change.details["schema_path"] == (
            "#/paths/~1users/get/parameters/query/age/schema/minimum"
        )

    def test_detect_pattern_constraint_changed(self):
        """Test detection of ambiguous constraint changes."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "code": {
                                                "type": "string",
                                                "pattern": "^[A-Z]+$",
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "code": {
                                                "type": "string",
                                                "pattern": "^[0-9]+$",
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.category == "schema_constraint")
        assert change.type == "potentially_breaking"
        assert change.message == "Schema constraint changed"
        assert change.details["keyword"] == "pattern"

    def test_detect_nested_array_item_constraint_change(self):
        """Test detection of constraints inside recursive schema nodes."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "tags": {
                                                "type": "array",
                                                "items": {
                                                    "type": "string",
                                                    "minLength": 2,
                                                },
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "tags": {
                                                "type": "array",
                                                "items": {
                                                    "type": "string",
                                                    "minLength": 4,
                                                },
                                            }
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.category == "schema_constraint")
        assert change.type == "breaking"
        assert change.field_name == "tags[]"
        assert change.details["schema_path"] == (
            "#/paths/~1users/post/requestBody/content/application~1json/schema/"
            "properties/tags/items/minLength"
        )

    def test_detect_removed_response(self):
        """Test detection of removed responses."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {"description": "OK"},
                            "404": {"description": "Not Found"},
                        }
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        response_changes = [
            c
            for c in result.changes
            if c.category == "response" and "404" in c.field_name
        ]
        assert len(response_changes) == 1
        assert response_changes[0].type == "potentially_breaking"
        assert response_changes[0].details.get("status_code") == "404"

    def test_detect_removed_success_response(self):
        """Test detection of removed success responses."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {"description": "OK"},
                            "201": {"description": "Created"},
                        }
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        response_changes = [
            c
            for c in result.changes
            if c.category == "response" and c.type == "breaking"
        ]
        assert len(response_changes) == 1
        assert "201" in response_changes[0].field_name

    def test_detect_added_response(self):
        """Test detection of added responses."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {"description": "OK"},
                            "404": {"description": "Not Found"},
                        }
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        response_changes = [
            c
            for c in result.changes
            if c.category == "response" and c.type == "non_breaking"
        ]
        assert len(response_changes) == 1
        assert "404" in response_changes[0].field_name

    def test_summary_accuracy(self):
        """Test that summary counts are accurate."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {"responses": {"200": {"description": "OK"}}},
                    "post": {"responses": {"201": {"description": "Created"}}},
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        summary = result.summary
        total_changes = (
            summary["breaking"]
            + summary["potentially_breaking"]
            + summary["non_breaking"]
        )
        assert total_changes == len(result.changes)
        assert summary["non_breaking"] > 0

    def test_version_info_in_result(self):
        """Test that version info is included in result."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "My API", "version": "1.0.0"},
            "paths": {},
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "My API", "version": "2.0.0"},
            "paths": {},
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        assert result.old_version == "My API v1.0.0"
        assert result.new_version == "My API v2.0.0"

    def test_swagger_2_to_openapi_3_diff(self):
        """Test diffing between Swagger 2.0 and OpenAPI 3.x specs."""
        old_spec = {
            "swagger": "2.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "produces": ["application/json"],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "2.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "OK",
                                "content": {
                                    "application/json": {"schema": {"type": "object"}}
                                },
                            }
                        }
                    }
                }
            },
        }

        differ = Differ()
        result = differ.diff(old_spec, new_spec)

        # Should successfully compare normalized specs
        assert isinstance(result, DiffResult)
        assert result.old_version is not None
        assert result.new_version is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
