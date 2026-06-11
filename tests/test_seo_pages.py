from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN_FILE = ROOT / "app" / "main.py"
TEMPLATES_DIR = Path(__file__).parents[1] / "app" / "templates"


def test_api_compatibility_guide_is_routable_and_indexed():
    main_file = MAIN_FILE.read_text()
    template = (TEMPLATES_DIR / "guide_api_compatibility.html").read_text()

    assert '"/guides/api-compatibility"' in main_file
    assert 'guide_api_compatibility.html' in main_file
    assert "API Compatibility Guide" in template
    assert "What is API compatibility?" in template
    assert "prevent contract regressions" in template


def test_sitemap_includes_api_compatibility_guide():
    main_file = MAIN_FILE.read_text()

    assert '"/guides/api-compatibility", "monthly", "0.8"' in main_file


def test_upload_page_targets_compare_swagger_files_online():
    template = (TEMPLATES_DIR / "upload.html").read_text()

    assert "Compare Swagger files online." in template
    assert "Swagger compare tool" in template
    assert "/guides/api-compatibility" in template


def test_guides_index_lists_api_compatibility_guide():
    template = (TEMPLATES_DIR / "guides.html").read_text()

    assert "API Compatibility Guide" in template
    assert "/guides/api-compatibility" in template


def test_swagger_openapi_guide_targets_versioning_queries():
    template = (TEMPLATES_DIR / "guide_swagger_openapi.html").read_text()

    assert "OpenAPI 2.0 vs 3.x" in template
    assert "Swagger vs OpenAPI" in template
    assert "Is Swagger 2.0 the same as OpenAPI 2.0?" in template


def test_contract_testing_guide_targets_ci_query_variants():
    template = (TEMPLATES_DIR / "guide_contract_testing_ci.html").read_text()

    assert "PR checks for API contract changes" in template
    assert "API contract testing CI CD" in template
    assert "prevent breaking API changes with contract tests" in template


def test_breaking_changes_guide_targets_detection_queries():
    template = (TEMPLATES_DIR / "guide_breaking_changes.html").read_text()

    assert "Breaking Changes Detection" in template
    assert "API breaking change detection" in template
    assert "What counts as a breaking API change?" in template
