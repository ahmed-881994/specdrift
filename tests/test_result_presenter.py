"""Tests for comparison result presentation metadata."""

from app.services.result_presenter import build_result_report


def test_result_report_groups_changes_by_api_surface():
    changes = [
        {
            "type": "breaking",
            "category": "schema",
            "path": "/users",
            "method": "GET",
            "field_name": "profile.email",
            "message": "Field removed",
            "details": {
                "schema_path": "#/paths/~1users/get/responses/200/content/application~1json/schema/properties/profile/properties/email"
            },
        },
        {
            "type": "potentially_breaking",
            "category": "component_schema",
            "path": "#/components/schemas/User",
            "field_name": "status",
            "message": "Enum value added",
            "details": {"schema_path": "#/components/schemas/User/properties/status"},
        },
        {
            "type": "non_breaking",
            "category": "webhook",
            "path": "#/webhooks/user.created",
            "method": "POST",
            "field_name": "user.created",
            "message": "Webhook added",
        },
    ]

    report = build_result_report(changes)

    assert report["total"] == 3
    assert [group["surface"] for group in report["groups"]] == [
        "operations",
        "components",
        "webhooks",
    ]
    assert report["groups"][0]["title"] == "/users"
    assert report["groups"][1]["title"] == "Schemas: User"
    assert report["groups"][2]["title"] == "Webhook: user.created"


def test_result_report_builds_filter_facets_and_group_counts():
    changes = [
        {
            "type": "breaking",
            "category": "media_type",
            "path": "/users",
            "method": "POST",
            "message": "Request media type removed",
        },
        {
            "type": "breaking",
            "category": "schema_constraint",
            "path": "#/components/schemas/User",
            "field_name": "maxLength",
            "message": "Constraint tightened",
            "details": {"schema_path": "#/components/schemas/User/properties/name/maxLength"},
        },
        {
            "type": "non_breaking",
            "category": "metadata",
            "path": "",
            "field_name": "info.description",
            "message": "Description changed",
        },
    ]

    report = build_result_report(changes)

    type_counts = {item["key"]: item["count"] for item in report["facets"]["types"]}
    category_counts = {item["key"]: item["count"] for item in report["facets"]["categories"]}
    surface_counts = {item["key"]: item["count"] for item in report["facets"]["surfaces"]}

    assert type_counts == {"breaking": 2, "non_breaking": 1}
    assert category_counts["schema_constraint"] == 1
    assert category_counts["media_type"] == 1
    assert surface_counts == {"operations": 1, "components": 1, "global": 1}

    component_group = next(group for group in report["groups"] if group["surface"] == "components")
    assert component_group["counts"]["breaking"] == 1
    assert component_group["categories"] == ["schema_constraint"]


def test_result_report_orders_severity_facets_breaking_risky_safe():
    changes = [
        {"type": "non_breaking", "category": "endpoint", "path": "/users", "message": "Added"},
        {
            "type": "potentially_breaking",
            "category": "parameter",
            "path": "/users",
            "method": "GET",
            "message": "Made optional",
        },
        {"type": "breaking", "category": "method", "path": "/users", "message": "Removed"},
    ]

    report = build_result_report(changes)

    assert [(item["key"], item["label"]) for item in report["facets"]["types"]] == [
        ("breaking", "Breaking"),
        ("potentially_breaking", "Risky"),
        ("non_breaking", "Safe"),
    ]


def test_result_report_orders_groups_and_changes_by_severity():
    changes = [
        {
            "type": "non_breaking",
            "category": "schema",
            "path": "/users",
            "method": "GET",
            "field_name": "nickname",
            "message": "Optional field added",
        },
        {
            "type": "potentially_breaking",
            "category": "schema",
            "path": "/users",
            "method": "GET",
            "field_name": "status",
            "message": "Enum value added",
        },
        {
            "type": "breaking",
            "category": "schema",
            "path": "/users",
            "method": "GET",
            "field_name": "email",
            "message": "Field removed",
        },
        {
            "type": "breaking",
            "category": "component_schema",
            "path": "#/components/schemas/Pet",
            "field_name": "id",
            "message": "Type changed",
            "details": {"schema_path": "#/components/schemas/Pet/properties/id"},
        },
    ]

    report = build_result_report(changes)
    users_group = next(group for group in report["groups"] if group["title"] == "/users")

    assert [change["type"] for change in users_group["changes"]] == [
        "breaking",
        "potentially_breaking",
        "non_breaking",
    ]
    assert report["groups"][0]["counts"]["breaking"] > 0
