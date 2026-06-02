"""Tests for schema utility helpers."""

import pytest

from app.core.schema_utils import (
    CIRCULAR_REF_MARKER,
    RefResolutionError,
    SchemaResolver,
    normalize_nullable_schema,
    schema_type_set,
)


class TestSchemaResolver:
    """Tests for local schema reference resolution."""

    def test_resolve_openapi_component_schema_ref(self):
        spec = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}},
                    }
                }
            },
        }

        resolver = SchemaResolver(spec)

        assert resolver.resolve_ref("#/components/schemas/User") == {
            "type": "object",
            "properties": {"id": {"type": "string"}},
        }

    def test_resolve_swagger_definition_ref(self):
        spec = {
            "swagger": "2.0",
            "definitions": {
                "User": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                }
            },
        }

        resolver = SchemaResolver(spec)

        assert resolver.resolve_ref("#/definitions/User")["properties"]["id"] == {
            "type": "string"
        }

    def test_resolve_swagger_definition_ref_after_normalization(self):
        spec = {
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}},
                    }
                }
            }
        }

        resolver = SchemaResolver(spec)

        assert resolver.resolve_ref("#/definitions/User")["properties"]["id"] == {
            "type": "string"
        }

    def test_resolve_component_ref_against_swagger_definitions(self):
        spec = {
            "definitions": {
                "User": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                }
            }
        }

        resolver = SchemaResolver(spec)

        assert resolver.resolve_ref("#/components/schemas/User")["properties"]["id"] == {
            "type": "string"
        }

    def test_resolve_json_pointer_escaped_ref(self):
        spec = {
            "components": {
                "schemas": {
                    "User/Profile~V1": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    }
                }
            }
        }

        resolver = SchemaResolver(spec)

        schema = resolver.resolve_ref("#/components/schemas/User~1Profile~0V1")

        assert schema["properties"]["name"] == {"type": "string"}

    def test_resolve_schema_replaces_nested_refs(self):
        spec = {
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "address": {"$ref": "#/components/schemas/Address"}
                        },
                    },
                    "Address": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                    },
                }
            }
        }

        resolver = SchemaResolver(spec)
        schema = resolver.resolve_schema({"$ref": "#/components/schemas/User"})

        assert schema["properties"]["address"]["properties"]["city"] == {
            "type": "string"
        }

    def test_resolve_schema_preserves_ref_siblings(self):
        spec = {
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "description": "Base user",
                    }
                }
            }
        }

        resolver = SchemaResolver(spec)
        schema = resolver.resolve_schema(
            {"$ref": "#/components/schemas/User", "description": "Overridden"}
        )

        assert schema["type"] == "object"
        assert schema["description"] == "Overridden"

    def test_resolve_schema_marks_circular_refs(self):
        spec = {
            "components": {
                "schemas": {
                    "Node": {
                        "type": "object",
                        "properties": {
                            "child": {"$ref": "#/components/schemas/Node"}
                        },
                    }
                }
            }
        }

        resolver = SchemaResolver(spec)
        schema = resolver.resolve_schema({"$ref": "#/components/schemas/Node"})

        child = schema["properties"]["child"]
        assert child["$ref"] == "#/components/schemas/Node"
        assert child[CIRCULAR_REF_MARKER] is True

    def test_resolve_missing_ref_raises(self):
        resolver = SchemaResolver({"components": {"schemas": {}}})

        with pytest.raises(RefResolutionError, match="Reference not found"):
            resolver.resolve_ref("#/components/schemas/Missing")

    def test_resolve_external_ref_raises(self):
        resolver = SchemaResolver({})

        with pytest.raises(RefResolutionError, match="Only local refs"):
            resolver.resolve_ref("common.yaml#/User")


class TestNormalizeNullableSchema:
    """Tests for nullable/type normalization helpers."""

    def test_normalize_nullable_scalar_type(self):
        schema = {"type": "string", "nullable": True}

        assert normalize_nullable_schema(schema) == {"type": ["string", "null"]}
        assert schema == {"type": "string", "nullable": True}

    def test_normalize_nullable_array_type(self):
        schema = {"type": ["string", "integer"], "nullable": True}

        assert normalize_nullable_schema(schema) == {
            "type": ["integer", "string", "null"]
        }

    def test_normalize_nullable_without_type(self):
        assert normalize_nullable_schema({"nullable": True}) == {"type": "null"}

    def test_normalize_nullable_nested_schemas(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "nullable": True},
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "nullable": True},
                },
            },
        }

        normalized = normalize_nullable_schema(schema)

        assert normalized["properties"]["name"]["type"] == ["string", "null"]
        assert normalized["properties"]["tags"]["items"]["type"] == [
            "string",
            "null",
        ]

    def test_schema_type_set_handles_scalar_and_array_types(self):
        assert schema_type_set({"type": "string"}) == {"string"}
        assert schema_type_set({"type": ["string", "null"]}) == {"string", "null"}
        assert schema_type_set({"format": "uuid"}) == set()
