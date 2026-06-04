"""Fixture-backed OpenAPI 3.1 comparison tests."""

from pathlib import Path

from app.services.diff_service import DiffService


FIXTURES = Path(__file__).parent / "fixtures" / "openapi31"


def compare_fixture_pair(old_name: str, new_name: str) -> dict:
    """Compare fixture files through the public diff service."""
    return DiffService.compare_specs(
        (FIXTURES / old_name).read_text(),
        (FIXTURES / new_name).read_text(),
        old_format="yaml",
        new_format="yaml",
    )


def changes_with(result: dict, **criteria):
    """Return serialized changes matching all provided fields."""
    return [
        change
        for change in result["changes"]
        if all(change.get(key) == value for key, value in criteria.items())
    ]


def test_openapi31_fixture_pair_covers_core_diff_categories():
    """The realistic 3.1 fixture pair should exercise richer diff output."""
    result = compare_fixture_pair("api-old.yml", "api-new.yml")
    categories = {change["category"] for change in result["changes"]}

    assert result["summary"]["total"] == len(result["changes"])
    assert result["summary"]["breaking"] > 0
    assert result["summary"]["potentially_breaking"] > 0
    assert {
        "component_schema",
        "schema_constraint",
        "media_type",
        "metadata",
        "webhook",
        "schema",
    }.issubset(categories)


def test_openapi31_fixture_component_changes_include_schema_paths_and_impacts():
    """Component schema changes should be precise and operation-aware."""
    result = compare_fixture_pair("api-old.yml", "api-new.yml")

    id_type_change = next(
        change
        for change in changes_with(result, category="component_schema")
        if change["field_name"] == "User.id"
    )
    assert id_type_change["type"] == "breaking"
    assert (
        id_type_change["details"]["schema_path"]
        == "#/components/schemas/User/properties/id/type"
    )
    assert id_type_change["details"]["old_value"] == "string"
    assert id_type_change["details"]["new_value"] == "integer"
    assert "POST /users" in id_type_change["details"]["impacted_operations"]

    required_email = next(
        change
        for change in changes_with(result, category="component_schema")
        if change["field_name"] == "User.email"
    )
    assert required_email["type"] == "breaking"
    assert required_email["details"]["required"] is True


def test_openapi31_fixture_tracks_constraints_media_types_and_webhooks():
    """Fixture comparisons should include representative 3.1 surface changes."""
    result = compare_fixture_pair("api-old.yml", "api-new.yml")

    enum_change = next(
        change
        for change in changes_with(result, category="schema_constraint")
        if change["field_name"] == "User.status"
        and change["details"]["keyword"] == "enum"
    )
    assert enum_change["type"] == "breaking"
    assert enum_change["details"]["keyword"] == "enum"
    assert enum_change["details"]["old_value"] == "suspended"
    assert "new_value" not in enum_change["details"]

    media_type_change = next(
        change for change in changes_with(result, category="media_type")
    )
    assert media_type_change["type"] == "breaking"
    assert media_type_change["field_name"] == "text/plain"
    assert (
        media_type_change["details"]["schema_path"]
        == "#/paths/~1users/post/responses/201/content/text~1plain"
    )

    removed_webhook = next(
        change
        for change in changes_with(result, category="webhook")
        if change["path"] == "user.deleted"
    )
    assert removed_webhook["type"] == "breaking"
    assert removed_webhook["details"]["schema_path"] == "#/webhooks/user.deleted"

    added_webhook = next(
        change
        for change in changes_with(result, category="webhook")
        if change["path"] == "user.created"
    )
    assert added_webhook["type"] == "non_breaking"
    assert added_webhook["details"]["schema_path"] == "#/webhooks/user.created"


def test_openapi31_component_only_fixture_compares_without_paths():
    """Component-only OpenAPI 3.1 files should work through DiffService."""
    result = compare_fixture_pair("components-old.yml", "components-new.yml")

    assert result["summary"]["total"] >= 3
    assert changes_with(result, category="component_schema")
    assert changes_with(result, category="schema_constraint")
    assert any(
        change["field_name"] == "Money.currency"
        and change["details"]["keyword"] == "enum"
        and change["details"]["old_value"] == "GBP"
        for change in changes_with(result, category="schema_constraint")
    )
