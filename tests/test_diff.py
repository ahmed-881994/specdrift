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

    def test_detect_removed_request_media_type(self):
        """Test detection of removed request body media types."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/uploads": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {"schema": {"type": "object"}},
                                "multipart/form-data": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "file": {
                                                "type": "string",
                                                "format": "binary",
                                            }
                                        },
                                    }
                                },
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
                "/uploads": {
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

        result = Differ().diff(old_spec, new_spec)

        media_changes = [c for c in result.changes if c.category == "media_type"]
        assert len(media_changes) == 1
        assert media_changes[0].type == "breaking"
        assert media_changes[0].field_name == "multipart/form-data"
        assert media_changes[0].details["location"] == "request_body"

    def test_detect_added_response_media_type(self):
        """Test detection of added response media types."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
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
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "OK",
                                "content": {
                                    "application/json": {"schema": {"type": "object"}},
                                    "application/xml": {"schema": {"type": "object"}},
                                },
                            }
                        }
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        media_changes = [c for c in result.changes if c.category == "media_type"]
        assert len(media_changes) == 1
        assert media_changes[0].type == "non_breaking"
        assert media_changes[0].field_name == "application/xml"
        assert media_changes[0].details["status_code"] == "200"

    def test_diffs_each_common_response_media_type_schema(self):
        """Test that shared response content types are diffed independently."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "OK",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"id": {"type": "string"}},
                                        }
                                    },
                                    "application/xml": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "legacyId": {"type": "string"}
                                            },
                                        }
                                    },
                                },
                            }
                        }
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
                        "responses": {
                            "200": {
                                "description": "OK",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"id": {"type": "string"}},
                                        }
                                    },
                                    "application/xml": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "legacyId": {"type": "integer"}
                                            },
                                        }
                                    },
                                },
                            }
                        }
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        schema_changes = [
            c
            for c in result.changes
            if c.category == "schema" and c.field_name == "legacyId"
        ]
        assert len(schema_changes) == 1
        assert (
            schema_changes[0]
            .details["schema_path"]
            .endswith("/content/application~1xml/schema/properties/legacyId/type")
        )

    def test_detect_response_header_add_remove_and_schema_change(self):
        """Test response header additions, removals, and schema changes."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "OK",
                                "headers": {
                                    "X-Rate-Limit": {"schema": {"type": "integer"}},
                                    "X-Deprecated": {"schema": {"type": "string"}},
                                },
                            }
                        }
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
                        "responses": {
                            "200": {
                                "description": "OK",
                                "headers": {
                                    "X-Rate-Limit": {"schema": {"type": "string"}},
                                    "X-Trace-Id": {"schema": {"type": "string"}},
                                },
                            }
                        }
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        removed_header = [
            c
            for c in result.changes
            if c.category == "header" and c.field_name == "X-Deprecated"
        ]
        added_header = [
            c
            for c in result.changes
            if c.category == "header" and c.field_name == "X-Trace-Id"
        ]
        changed_header_schema = [
            c
            for c in result.changes
            if c.category == "schema" and c.field_name == "X-Rate-Limit"
        ]
        assert len(removed_header) == 1
        assert removed_header[0].type == "potentially_breaking"
        assert len(added_header) == 1
        assert added_header[0].type == "non_breaking"
        assert len(changed_header_schema) == 1
        assert changed_header_schema[0].details["location"] == "response_200_header"

    def test_detect_parameter_serialization_change(self):
        """Test OpenAPI parameter serialization attribute changes."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [
                            {
                                "name": "ids",
                                "in": "query",
                                "style": "form",
                                "explode": True,
                                "schema": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
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
                                "name": "ids",
                                "in": "query",
                                "style": "spaceDelimited",
                                "explode": False,
                                "schema": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        serialization_changes = [
            c for c in result.changes if c.category == "parameter_serialization"
        ]
        assert len(serialization_changes) == 2
        assert {c.details["keyword"] for c in serialization_changes} == {
            "style",
            "explode",
        }
        assert all(c.type == "breaking" for c in serialization_changes)

    def test_detect_openapi_31_json_schema_dialect_change(self):
        """Test detection of root JSON Schema dialect changes."""
        old_spec = {
            "openapi": "3.1.0",
            "info": {"title": "API", "version": "1.0.0"},
            "jsonSchemaDialect": "https://json-schema.org/draft/2020-12/schema",
            "paths": {},
        }
        new_spec = {
            "openapi": "3.1.0",
            "info": {"title": "API", "version": "1.0.0"},
            "jsonSchemaDialect": "https://spec.openapis.org/oas/3.1/dialect/base",
            "paths": {},
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.field_name == "jsonSchemaDialect")
        assert change.category == "metadata"
        assert change.type == "potentially_breaking"
        assert change.details["schema_path"] == "#/jsonSchemaDialect"
        assert (
            change.details["old_value"]
            == "https://json-schema.org/draft/2020-12/schema"
        )
        assert (
            change.details["new_value"]
            == "https://spec.openapis.org/oas/3.1/dialect/base"
        )

    def test_detect_openapi_31_schema_keyword_change(self):
        """Test detection of 3.1 JSON Schema keyword changes."""
        old_spec = {
            "openapi": "3.1.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/uploads": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "payload": {
                                                "type": "string",
                                                "contentMediaType": "application/json",
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
                "/uploads": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "payload": {
                                                "type": "string",
                                                "contentMediaType": "application/cbor",
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

        change = next(
            c
            for c in result.changes
            if c.category == "schema_constraint"
            and c.details["keyword"] == "contentMediaType"
        )
        assert change.type == "potentially_breaking"
        assert change.field_name == "payload"
        assert change.details["schema_path"] == (
            "#/paths/~1uploads/post/requestBody/content/application~1json/schema/"
            "properties/payload/contentMediaType"
        )
        assert change.details["old_value"] == "application/json"
        assert change.details["new_value"] == "application/cbor"

    def test_openapi_30_example_and_openapi_31_examples_are_equivalent(self):
        """Test that OpenAPI 3.0 example and 3.1 examples compare cleanly."""
        old_spec = {
            "openapi": "3.0.3",
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
                                                "example": "Ada",
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
                                                "examples": ["Ada"],
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

        assert not [
            c
            for c in result.changes
            if c.category == "schema_constraint"
            and c.details.get("keyword") == "examples"
        ]

    def test_detect_openapi_31_examples_change(self):
        """Test detection of 3.1 examples changes."""
        old_spec = {
            "openapi": "3.1.0",
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
                                                "examples": ["Ada"],
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
                                                "examples": ["Grace"],
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

        change = next(
            c
            for c in result.changes
            if c.category == "schema_constraint" and c.details["keyword"] == "examples"
        )
        assert change.type == "potentially_breaking"
        assert change.field_name == "name"
        assert change.details["old_value"] == ["Ada"]
        assert change.details["new_value"] == ["Grace"]

    def test_detect_openapi_31_dependent_required_change(self):
        """Test detection of JSON Schema 2020-12 dependentRequired changes."""
        old_spec = {
            "openapi": "3.1.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/payments": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "dependentRequired": {"card": ["billingZip"]},
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
                "/payments": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "dependentRequired": {
                                            "card": ["billingZip", "cvv"]
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

        change = next(
            c
            for c in result.changes
            if c.category == "schema_constraint"
            and c.details["keyword"] == "dependentRequired"
        )
        assert change.type == "potentially_breaking"
        assert change.details["schema_path"] == (
            "#/paths/~1payments/post/requestBody/content/application~1json/schema/"
            "dependentRequired"
        )

    def test_detect_removed_referenced_component_schema(self):
        """Test detection of removed reusable schemas and impacted operations."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "OK",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/User"}
                                    }
                                },
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "2.0.0"},
            "paths": old_spec["paths"],
            "components": {"schemas": {}},
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(
            c
            for c in result.changes
            if c.category == "component_schema" and c.field_name == "User"
        )
        assert change.type == "breaking"
        assert change.message == "Referenced reusable component removed"
        assert change.details["component_type"] == "schemas"
        assert change.details["ref"] == "#/components/schemas/User"
        assert change.details["impacted_operations"] == ["GET /users"]

    def test_detect_component_schema_property_change(self):
        """Test recursive diffing inside reusable schema components."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {"/users": {"get": {"responses": {"200": {"description": "OK"}}}}},
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"},
                            "name": {"type": "string"},
                        },
                        "required": ["name"],
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "2.0.0"},
            "paths": old_spec["paths"],
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "integer"},
                            "name": {"type": "string"},
                        },
                        "required": ["name", "email"],
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        type_change = next(
            c
            for c in result.changes
            if c.field_name == "User.email" and c.message == "Field type changed"
        )
        assert type_change.category == "component_schema"
        assert type_change.path == "#/components/schemas/User"
        assert type_change.details["schema_path"] == (
            "#/components/schemas/User/properties/email/type"
        )
        assert type_change.details["old_value"] == "string"
        assert type_change.details["new_value"] == "integer"

        required_change = next(
            c
            for c in result.changes
            if c.field_name == "User.email" and c.message == "Field made required"
        )
        assert required_change.category == "component_schema"
        assert required_change.details["schema_path"] == (
            "#/components/schemas/User/required"
        )

    def test_detect_reusable_component_map_changes(self):
        """Test additions, removals, and changes in non-schema component maps."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [{"$ref": "#/components/parameters/TraceId"}],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
            "components": {
                "parameters": {
                    "TraceId": {
                        "name": "X-Trace-Id",
                        "in": "header",
                        "schema": {"type": "string"},
                    },
                    "Locale": {
                        "name": "locale",
                        "in": "query",
                        "schema": {"type": "string"},
                    },
                },
                "securitySchemes": {
                    "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-Key"}
                },
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "2.0.0"},
            "paths": old_spec["paths"],
            "components": {
                "parameters": {
                    "TraceId": {
                        "name": "X-Trace-Id",
                        "in": "header",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    "Page": {
                        "name": "page",
                        "in": "query",
                        "schema": {"type": "integer"},
                    },
                },
                "securitySchemes": {"ApiKeyAuth": {"type": "http", "scheme": "bearer"}},
            },
        }

        result = Differ().diff(old_spec, new_spec)

        removed = next(c for c in result.changes if c.field_name == "Locale")
        assert removed.category == "component"
        assert removed.type == "potentially_breaking"
        assert removed.details["component_type"] == "parameters"

        added = next(c for c in result.changes if c.field_name == "Page")
        assert added.category == "component"
        assert added.type == "non_breaking"

        changed = next(c for c in result.changes if c.field_name == "TraceId")
        assert changed.category == "component"
        assert changed.type == "potentially_breaking"
        assert changed.details["impacted_operations"] == ["GET /users"]

        security_change = next(
            c for c in result.changes if c.field_name == "ApiKeyAuth"
        )
        assert security_change.category == "component"
        assert security_change.details["component_type"] == "securitySchemes"

    def test_detect_removed_referenced_request_body_component(self):
        """Test impacted operation reporting for reusable request body refs."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "$ref": "#/components/requestBodies/CreateUser"
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
            "components": {
                "requestBodies": {
                    "CreateUser": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UserInput"}
                            }
                        },
                    }
                },
                "schemas": {
                    "UserInput": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    }
                },
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "2.0.0"},
            "paths": old_spec["paths"],
            "components": {
                "requestBodies": {},
                "schemas": old_spec["components"]["schemas"],
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.field_name == "CreateUser")
        assert change.category == "component"
        assert change.type == "breaking"
        assert change.details["component_type"] == "requestBodies"
        assert change.details["impacted_operations"] == ["POST /users"]

    def test_detect_root_security_requirement_added(self):
        """Test root security additions are classified as breaking."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {},
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "security": [{"ApiKeyAuth": []}],
            "paths": {},
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.field_name == "security")
        assert change.category == "security"
        assert change.type == "breaking"
        assert change.message == "Security requirement added"
        assert change.details["schema_path"] == "#/security"
        assert change.details["metadata_scope"] == "root"

    def test_detect_root_server_removed(self):
        """Test root server removals are potentially breaking."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com/v1"}],
            "paths": {},
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {},
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.field_name == "servers")
        assert change.category == "server"
        assert change.type == "potentially_breaking"
        assert change.message == "Server removed"
        assert change.details["schema_path"] == "#/servers"

    def test_detect_path_server_changed(self):
        """Test path-level server changes are reported with path scope."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "servers": [{"url": "https://api.example.com/v1"}],
                    "get": {"responses": {"200": {"description": "OK"}}},
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "servers": [{"url": "https://edge.example.com/v1"}],
                    "get": {"responses": {"200": {"description": "OK"}}},
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.field_name == "servers")
        assert change.category == "server"
        assert change.type == "potentially_breaking"
        assert change.details["schema_path"] == "#/paths/~1users/servers"
        assert change.details["metadata_scope"] == "path"

    def test_detect_operation_metadata_changes(self):
        """Test operation IDs and deprecation changes are reported."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "deprecated": False,
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
                        "operationId": "searchUsers",
                        "deprecated": True,
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        operation_id = next(c for c in result.changes if c.field_name == "operationId")
        deprecated = next(c for c in result.changes if c.field_name == "deprecated")
        assert operation_id.category == "metadata"
        assert operation_id.type == "potentially_breaking"
        assert operation_id.message == "Operation ID changed"
        assert operation_id.details["schema_path"] == "#/paths/~1users/get/operationId"
        assert deprecated.type == "potentially_breaking"
        assert deprecated.message == "Operation deprecated"

    def test_detect_operation_callback_removed(self):
        """Test operation callback removals are classified as breaking."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/subscriptions": {
                    "post": {
                        "callbacks": {
                            "onEvent": {
                                "{$request.body#/callbackUrl}": {
                                    "post": {
                                        "responses": {"200": {"description": "OK"}}
                                    }
                                }
                            }
                        },
                        "responses": {"202": {"description": "Accepted"}},
                    }
                }
            },
        }
        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/subscriptions": {
                    "post": {"responses": {"202": {"description": "Accepted"}}}
                }
            },
        }

        result = Differ().diff(old_spec, new_spec)

        change = next(c for c in result.changes if c.field_name == "onEvent")
        assert change.category == "callback"
        assert change.type == "breaking"
        assert change.message == "Callback removed"
        assert (
            change.details["schema_path"]
            == "#/paths/~1subscriptions/post/callbacks/onEvent"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
