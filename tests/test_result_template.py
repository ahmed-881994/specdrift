"""Tests for the result-page rendering contract."""

from pathlib import Path


TEMPLATE = Path(__file__).parents[1] / "app" / "templates" / "result.html"


def test_result_template_renders_structured_diff_details():
    """The result UI should expose rich diff details from serialized changes."""
    template = TEMPLATE.read_text()

    assert "renderStructuredDetails(change.details)" in template
    assert "details.schema_path" in template
    assert "details.old_value" in template
    assert "details.new_value" in template
    assert "details.impacted_operations" in template
    assert "formatValue(value)" in template


def test_result_template_labels_new_change_categories():
    """New Phase 10 fixture categories should have readable UI labels."""
    template = TEMPLATE.read_text()

    for category in (
        "schema_constraint",
        "media_type",
        "component_schema",
        "webhook",
        "callback",
        "parameter_serialization",
    ):
        assert category in template
