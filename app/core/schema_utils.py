"""
Schema utilities for OpenAPI/Swagger diffing.

This module keeps schema normalization and local reference resolution separate
from the differ so future comparison phases can build on a shared foundation.
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional, Set


CIRCULAR_REF_MARKER = "x-specdrift-circular-ref"


class RefResolutionError(ValueError):
    """Raised when an internal schema reference cannot be resolved."""


class SchemaResolver:
    """Resolve local JSON Pointer references in OpenAPI/Swagger documents."""

    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec

    def resolve_ref(self, ref: str) -> Any:
        """
        Resolve a local JSON Pointer reference.

        Supports normal JSON Pointers plus compatibility lookups between
        Swagger 2.0 definitions and OpenAPI components.schemas.
        """
        if not ref.startswith("#/"):
            raise RefResolutionError(f"Only local refs are supported: {ref}")

        try:
            return deepcopy(self._resolve_pointer(ref))
        except RefResolutionError:
            alternate_ref = self._alternate_schema_ref(ref)
            if not alternate_ref:
                raise
            return deepcopy(self._resolve_pointer(alternate_ref))

    def resolve_schema(
        self, schema: Dict[str, Any], seen_refs: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Resolve local refs inside a schema.

        Circular refs are retained as refs and marked so callers can avoid
        infinite recursion while still knowing a cycle was found.
        """
        if seen_refs is None:
            seen_refs = set()

        if not isinstance(schema, dict):
            return schema

        ref = schema.get("$ref")
        if ref:
            if ref in seen_refs:
                return {"$ref": ref, CIRCULAR_REF_MARKER: True}

            resolved = self.resolve_ref(ref)
            if not isinstance(resolved, dict):
                return resolved

            merged = deepcopy(resolved)
            for key, value in schema.items():
                if key != "$ref":
                    merged[key] = value

            return self.resolve_schema(merged, seen_refs | {ref})

        resolved_schema = {}
        for key, value in schema.items():
            if isinstance(value, dict):
                resolved_schema[key] = self.resolve_schema(value, seen_refs)
            elif isinstance(value, list):
                resolved_schema[key] = [
                    self.resolve_schema(item, seen_refs) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                resolved_schema[key] = value

        return resolved_schema

    def _resolve_pointer(self, ref: str) -> Any:
        current: Any = self.spec
        for part in ref[2:].split("/"):
            key = self._decode_pointer_part(part)
            if isinstance(current, list):
                try:
                    current = current[int(key)]
                except (ValueError, IndexError):
                    raise RefResolutionError(f"Reference not found: {ref}") from None
            elif isinstance(current, dict) and key in current:
                current = current[key]
            else:
                raise RefResolutionError(f"Reference not found: {ref}")
        return current

    @staticmethod
    def _decode_pointer_part(part: str) -> str:
        return part.replace("~1", "/").replace("~0", "~")

    @staticmethod
    def _alternate_schema_ref(ref: str) -> Optional[str]:
        definitions_prefix = "#/definitions/"
        components_prefix = "#/components/schemas/"

        if ref.startswith(definitions_prefix):
            return components_prefix + ref[len(definitions_prefix):]
        if ref.startswith(components_prefix):
            return definitions_prefix + ref[len(components_prefix):]
        return None


def normalize_nullable_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize OpenAPI 3.0 nullable schemas into a type set representation.

    The original schema is not mutated. Nested schemas are normalized as well.
    """
    if not isinstance(schema, dict):
        return schema

    normalized = {}
    for key, value in schema.items():
        if isinstance(value, dict):
            normalized[key] = normalize_nullable_schema(value)
        elif isinstance(value, list):
            normalized[key] = [
                normalize_nullable_schema(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            normalized[key] = value

    if normalized.get("nullable") is True:
        types = schema_type_set(normalized)
        types.add("null")
        normalized["type"] = _format_type_set(types)
        normalized.pop("nullable", None)

    return normalized


def schema_type_set(schema: Dict[str, Any]) -> Set[str]:
    """Return a schema's type as a set, supporting scalar and array forms."""
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return {item for item in schema_type if isinstance(item, str)}
    if isinstance(schema_type, str):
        return {schema_type}
    return set()


def _format_type_set(types: Set[str]) -> Any:
    if not types:
        return ["null"]
    ordered = sorted(type_name for type_name in types if type_name != "null")
    if "null" in types:
        ordered.append("null")
    if len(ordered) == 1:
        return ordered[0]
    return ordered
