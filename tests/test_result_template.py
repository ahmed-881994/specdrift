"""Tests for the result-page rendering contract."""

from pathlib import Path


TEMPLATE = Path(__file__).parents[1] / "app" / "templates" / "result.html"
REPAINT_CSS = Path(__file__).parents[1] / "app" / "static" / "repaint.css"


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


def test_result_template_uses_phase_11_grouped_report_contract():
    """The result UI should render grouped report data with facet filters."""
    template = TEMPLATE.read_text()

    assert "normalizeReport(result)" in template
    assert "renderFilterPanel(report)" in template
    assert "report.facets.surfaces" in template
    assert "report.facets.categories" in template
    assert "renderFilterChips('surface'" in template
    assert "renderFilterChips('category'" in template
    assert "data-filter-kind=\"${kind}\"" in template
    assert "data-surface=\"${escapeHtml(group.surface)}\"" in template
    assert "id=\"emptyFilterMessage\"" in template


def test_result_template_uses_plain_language_filters_and_active_state():
    """Filters should be understandable and visibly selected."""
    template = TEMPLATE.read_text()

    assert "Where did it change?" in template
    assert "What changed?" in template
    assert "Reusable schemas" in template
    assert "Validation rule changed" in template
    assert "aria-pressed=\"false\"" in template
    assert "button.setAttribute('aria-pressed'" in template
    assert "filter-chip-check" in template
    assert "<em>Breaking</em>" in template
    assert "<em>Risky</em>" in template
    assert "<em>Safe</em>" in template


def test_result_template_filters_rows_and_marks_each_row_with_severity():
    """Severity filters should hide non-matching rows and keep per-row severity classes."""
    template = TEMPLATE.read_text()

    assert "row.classList.toggle('is-filter-hidden', !matches)" in template
    assert "group.classList.toggle('is-filter-hidden', !hasVisibleRows)" in template
    assert 'class="change-row ${typeClass(change.type)}"' in template
    assert "data-count-type=\"breaking\"" in template
    assert "count.classList.toggle('is-filter-hidden'" in template
    assert "setVisibleGroupSeverity" not in template


def test_result_css_colors_the_bar_on_each_change_row():
    """The left bar beside a change should reflect that row's own severity."""
    css = REPAINT_CSS.read_text()

    assert ".repaint-results-container .change-row.breaking .change-item" in css
    assert ".repaint-results-container .change-row.potentially-breaking .change-item" in css
    assert ".repaint-results-container .change-row.non-breaking .change-item" in css
    assert "border-left: 1px solid var(--rp-rule) !important;" in css
    assert ".repaint-results-container .change-group.breaking" not in css


def test_result_css_keeps_change_description_badge_readable():
    """The change description badge must override legacy risky-group dark text."""
    css = REPAINT_CSS.read_text()

    assert ".repaint-results-container .change-category" in css
    assert "color: var(--rp-text) !important;" in css


def test_result_template_shows_severity_in_breaking_risky_safe_order():
    """Severity labels should appear in the requested order."""
    template = TEMPLATE.read_text()

    breaking_index = template.index('<span class="label">Breaking</span>')
    risky_index = template.index('<span class="label">Risky</span>')
    safe_index = template.index('<span class="label">Safe</span>')

    assert breaking_index < risky_index < safe_index
    assert "RISKY" in template
    assert "Needs Review" not in template
    assert "Needs review" not in template


def test_result_template_sorts_rendered_groups_and_rows_by_severity():
    """Rendered changes should be ordered Breaking, Risky, Safe, not just the banners."""
    template = TEMPLATE.read_text()

    assert "sortGroupsBySeverity(report.groups)" in template
    assert "sortChangesBySeverity(group.changes)" in template
    assert "function severityRank(type)" in template
    assert "breaking: 0, potentially_breaking: 1, non_breaking: 2" in template
