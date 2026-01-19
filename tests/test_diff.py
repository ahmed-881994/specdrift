"""Unit tests for API diff logic."""

import pytest
from app.services.diff_service import DiffService


class TestDiffService:
    """Tests for the diff service."""

    def test_detect_removed_endpoint(self):
        """Test detection of removed endpoints."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {"summary": "Get users", "responses": {"200": {"description": "OK"}}}
                },
                "/posts": {
                    "get": {"summary": "Get posts", "responses": {"200": {"description": "OK"}}}
                },
            },
        }

        new_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {"summary": "Get users", "responses": {"200": {"description": "OK"}}}
                }
            },
        }

        result = DiffService.compare_specs(
            str(old_spec).replace("'", '"'),
            str(new_spec).replace("'", '"')
        )

        # Find endpoint removed change
        endpoint_changes = [
            c for c in result["changes"]
            if c["category"] == "endpoint" and c["type"] == "breaking"
        ]
        assert len(endpoint_changes) > 0
        assert any("/posts" in c["path"] for c in endpoint_changes)

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
                                        "properties": {
                                            "name": {"type": "string"},
                                        },
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

        result = DiffService.compare_specs(
            str(old_spec).replace("'", '"'),
            str(new_spec).replace("'", '"')
        )

        # Find breaking schema change
        schema_changes = [
            c for c in result["changes"]
            if c["category"] == "schema" and c["type"] == "breaking"
        ]
        assert len(schema_changes) > 0

    def test_detect_type_changes(self):
        """Test detection of parameter type changes."""
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
                            {
                                "name": "id",
                                "in": "query",
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        result = DiffService.compare_specs(
            str(old_spec).replace("'", '"'),
            str(new_spec).replace("'", '"')
        )

        # Find type change
        type_changes = [
            c for c in result["changes"]
            if c["type"] == "breaking" and "type" in c["message"].lower()
        ]
        assert len(type_changes) > 0

    def test_validate_summary_counts(self):
        """Test that summary counts are accurate."""
        old_spec = {
            "openapi": "3.0.0",
            "info": {"title": "API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {"responses": {"200": {"description": "OK"}}}
                }
            },
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

        result = DiffService.compare_specs(
            str(old_spec).replace("'", '"'),
            str(new_spec).replace("'", '"')
        )

        summary = result["summary"]
        assert summary["breaking"] + summary["potentially_breaking"] + summary["non_breaking"] == len(
            result["changes"]
        )
        assert summary["non_breaking"] > 0  # POST method added

    def test_invalid_spec_raises_error(self):
        """Test that invalid specs raise appropriate errors."""
        with pytest.raises(ValueError):
            DiffService.compare_specs("invalid json", "{}")

    def test_missing_required_fields_raises_error(self):
        """Test that specs missing required fields raise errors."""
        incomplete_spec = {
            "swagger": "2.0",
            "info": {"title": "API", "version": "1.0.0"}
            # Missing "paths"
        }

        with pytest.raises(ValueError):
            DiffService.compare_specs(
                str(incomplete_spec).replace("'", '"'),
                str(incomplete_spec).replace("'", '"')
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
