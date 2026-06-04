"""Fixture-backed Swagger 2.0 comparison tests."""

from pathlib import Path

from app.services.diff_service import DiffService


FIXTURES = Path(__file__).parent / "fixtures" / "swagger20"


def compare_fixture_pair(old_name: str, new_name: str) -> dict:
    """Compare Swagger/OpenAPI fixture files through the public diff service."""
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


def test_swagger20_fixture_pair_covers_normalized_diff_categories():
    """Swagger 2.0 fixtures should exercise the OpenAPI-style diff model."""
    result = compare_fixture_pair("api-old.yml", "api-new.yml")
    categories = {change["category"] for change in result["changes"]}

    assert result["summary"]["total"] == len(result["changes"])
    assert result["summary"]["breaking"] > 0
    assert {
        "component_schema",
        "schema_constraint",
        "media_type",
        "parameter_serialization",
        "server",
    }.issubset(categories)


def test_swagger20_definition_changes_include_component_ref_impacts():
    """Swagger #/definitions refs should map to component impact details."""
    result = compare_fixture_pair("api-old.yml", "api-new.yml")

    id_type_change = next(
        change
        for change in changes_with(result, category="component_schema")
        if change["field_name"] == "User.id"
    )
    assert id_type_change["type"] == "breaking"
    assert id_type_change["details"]["ref"] == "#/components/schemas/User"
    assert "POST /users" in id_type_change["details"]["impacted_operations"]

    email_change = next(
        change
        for change in changes_with(result, category="component_schema")
        if change["field_name"] == "User.email"
    )
    assert email_change["type"] == "breaking"
    assert email_change["details"]["required"] is True


def test_swagger20_media_types_headers_and_collection_format_are_diffed():
    """Swagger consumes/produces, headers, and collectionFormat should survive normalization."""
    result = compare_fixture_pair("api-old.yml", "api-new.yml")

    request_xml = next(
        change
        for change in changes_with(result, category="media_type")
        if change["field_name"] == "application/xml"
    )
    assert request_xml["type"] == "breaking"
    assert request_xml["details"]["location"] == "request_body"

    response_text = next(
        change
        for change in changes_with(result, category="media_type")
        if change["field_name"] == "text/plain"
    )
    assert response_text["type"] == "breaking"
    assert response_text["details"]["location"] == "response"

    header_change = next(change for change in changes_with(result, category="header"))
    assert header_change["type"] == "potentially_breaking"
    assert header_change["field_name"] == "X-Trace-Id"

    serialization_change = next(
        change for change in changes_with(result, category="parameter_serialization")
    )
    assert serialization_change["field_name"] == "tags"
    assert serialization_change["details"]["keyword"] == "collectionFormat"
    assert serialization_change["details"]["old_value"] == "csv"
    assert serialization_change["details"]["new_value"] == "multi"


def test_swagger20_to_openapi31_cross_version_fixture_compares_components():
    """Swagger 2.0 and OpenAPI 3.1 fixtures should compare through normalization."""
    result = compare_fixture_pair("swagger-old.yml", "openapi-new.yml")

    assert result["old_version"] == "Cross Version Fixture v1.0.0"
    assert result["new_version"] == "Cross Version Fixture v2.0.0"
    assert changes_with(result, category="server")

    required_total = next(
        change
        for change in changes_with(result, category="component_schema")
        if change["field_name"] == "Order.total"
        and change["message"] == "Field made required"
    )
    assert required_total["type"] == "breaking"

    stricter_minimum = next(
        change
        for change in changes_with(result, category="schema_constraint")
        if change["field_name"] == "Order.total"
        and change["details"]["keyword"] == "minimum"
    )
    assert stricter_minimum["type"] == "breaking"
    assert stricter_minimum["details"]["old_value"] == 0
    assert stricter_minimum["details"]["new_value"] == 1
