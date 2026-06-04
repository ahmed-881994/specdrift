"""Presentation helpers for comparison results."""

from collections import Counter
from typing import Any, Dict, Iterable, List, Tuple


TYPE_LABELS = {
    "breaking": "Breaking",
    "potentially_breaking": "Risky",
    "non_breaking": "Safe",
}

TYPE_ORDER = {
    "breaking": 0,
    "potentially_breaking": 1,
    "non_breaking": 2,
}

SURFACE_LABELS = {
    "operations": "Endpoints",
    "components": "Reusable schemas",
    "webhooks": "Webhook events",
    "callbacks": "Callback requests",
    "global": "API settings",
}

CATEGORY_LABELS = {
    "endpoint": "Endpoint added/removed",
    "method": "HTTP method changed",
    "parameter": "Request parameter changed",
    "schema": "Request/response field changed",
    "response": "Response status changed",
    "request_body": "Request body changed",
    "component": "Reusable component changed",
    "component_schema": "Reusable schema field changed",
    "schema_constraint": "Validation rule changed",
    "media_type": "Content type changed",
    "header": "Header changed",
    "parameter_serialization": "Parameter format changed",
    "security": "Authentication changed",
    "server": "Server URL changed",
    "webhook": "Webhook changed",
    "callback": "Callback changed",
    "metadata": "Documentation changed",
}

SURFACE_ORDER = {
    "operations": 0,
    "components": 1,
    "webhooks": 2,
    "callbacks": 3,
    "global": 4,
}


def build_result_report(changes: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Build grouped, filterable presentation metadata for serialized changes."""
    change_list = list(changes)
    groups: Dict[str, Dict[str, Any]] = {}
    type_counts = Counter(change.get("type", "unknown") for change in change_list)
    category_counts = Counter(change.get("category", "unknown") for change in change_list)
    surface_counts = Counter()

    for index, change in enumerate(change_list):
        surface, group_key, title, subtitle = _group_identity(change)
        surface_counts[surface] += 1

        if group_key not in groups:
            groups[group_key] = {
                "key": group_key,
                "surface": surface,
                "surface_label": SURFACE_LABELS.get(surface, _format_label(surface)),
                "title": title,
                "subtitle": subtitle,
                "counts": {
                    "breaking": 0,
                    "potentially_breaking": 0,
                    "non_breaking": 0,
                    "total": 0,
                },
                "categories": [],
                "changes": [],
            }

        group = groups[group_key]
        change_type = change.get("type")
        if change_type in group["counts"]:
            group["counts"][change_type] += 1
        group["counts"]["total"] += 1
        group["changes"].append({**change, "_result_index": index})

    for group in groups.values():
        group["categories"] = sorted(
            {
                change.get("category", "unknown")
                for change in group["changes"]
                if change.get("category")
            }
        )
        group["changes"].sort(key=_change_sort_key)

    return {
        "total": len(change_list),
        "facets": {
            "types": _facet_items(type_counts, TYPE_LABELS, TYPE_ORDER),
            "categories": _facet_items(category_counts, CATEGORY_LABELS),
            "surfaces": _facet_items(surface_counts, SURFACE_LABELS, SURFACE_ORDER),
        },
        "groups": sorted(
            groups.values(),
            key=lambda group: (
                _group_severity_order(group),
                SURFACE_ORDER.get(group["surface"], 99),
                group["title"].lower(),
                group["key"],
            ),
        ),
    }


def _change_sort_key(change: Dict[str, Any]) -> Tuple[int, int]:
    return (
        TYPE_ORDER.get(change.get("type"), 99),
        change.get("_result_index", 0),
    )


def _group_severity_order(group: Dict[str, Any]) -> int:
    counts = group.get("counts", {})
    if counts.get("breaking", 0) > 0:
        return TYPE_ORDER["breaking"]
    if counts.get("potentially_breaking", 0) > 0:
        return TYPE_ORDER["potentially_breaking"]
    return TYPE_ORDER["non_breaking"]


def _group_identity(change: Dict[str, Any]) -> Tuple[str, str, str, str]:
    category = change.get("category", "unknown")
    path = change.get("path") or ""
    method = change.get("method") or ""
    field_name = change.get("field_name") or ""
    details = change.get("details") or {}
    schema_path = details.get("schema_path", "")

    if category == "webhook" or path.startswith("#/webhooks"):
        webhook_name = field_name or _path_part(path, "#/webhooks/", 0) or path or "Webhook"
        title = f"Webhook: {webhook_name}"
        subtitle = method or "Webhook contract"
        return "webhooks", f"webhook:{webhook_name}", title, subtitle

    if category == "callback" or path.startswith("#/components/callbacks"):
        callback_name = field_name or details.get("callback_name") or path or "Callback"
        title = f"Callback: {callback_name}"
        subtitle = method or details.get("callback_expression", "Callback contract")
        return "callbacks", f"callback:{callback_name}", title, subtitle

    if _is_component_change(category, path, schema_path):
        component_type, component_name = _component_identity(
            category, field_name, path, schema_path, details
        )
        title = f"{_format_label(component_type)}: {component_name}"
        subtitle = "Reusable component"
        return (
            "components",
            f"component:{component_type}:{component_name}",
            title,
            subtitle,
        )

    if category in {"security", "server", "metadata"} and not path.strip("/#"):
        title = _format_label(field_name or category)
        subtitle = "API-level setting"
        return "global", f"global:{category}:{field_name}", title, subtitle

    title = path or field_name or _format_label(category)
    subtitle = f"{method} operation" if method else _format_label(category)
    return "operations", f"operation:{method}:{path}", title, subtitle


def _facet_items(
    counts: Counter, labels: Dict[str, str] | None = None, order: Dict[str, int] | None = None
) -> List[Dict[str, Any]]:
    labels = labels or {}
    order = order or {}
    return [
        {
            "key": key,
            "label": labels.get(key, _format_label(key)),
            "count": counts[key],
        }
        for key in sorted(counts, key=lambda value: (order.get(value, 99), labels.get(value, value)))
    ]


def _is_component_change(category: str, path: str, schema_path: str) -> bool:
    return (
        category in {"component", "component_schema", "schema_constraint"}
        and (path.startswith("#/components") or schema_path.startswith("#/components"))
    )


def _component_identity(
    category: str,
    field_name: str,
    path: str,
    schema_path: str,
    details: Dict[str, Any],
) -> Tuple[str, str]:
    source = schema_path or path
    component_type = details.get("component_type") or _path_part(source, "#/components/", 0)
    component_name = _path_part(source, "#/components/", 1) or field_name or category
    return component_type or "component", component_name


def _path_part(value: str, prefix: str, index: int) -> str:
    if not value.startswith(prefix):
        return ""
    parts = [part for part in value[len(prefix) :].split("/") if part]
    if index >= len(parts):
        return ""
    return parts[index].replace("~1", "/").replace("~0", "~")


def _format_label(value: str) -> str:
    return str(value).replace("_", " ").replace("-", " ").strip().title()
