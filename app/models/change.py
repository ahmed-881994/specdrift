"""Data models for API changes."""

from typing import Literal, Optional, Dict, Any
from dataclasses import dataclass, field, asdict


ChangeType = Literal["breaking", "potentially_breaking", "non_breaking"]
ChangeCategory = Literal[
    "endpoint",
    "method",
    "parameter",
    "schema",
    "response",
    "request_body",
    "component",
    "component_schema",
    "schema_constraint",
    "media_type",
    "header",
    "parameter_serialization",
    "security",
    "server",
    "webhook",
    "callback",
    "metadata",
]


@dataclass
class Change:
    """
    Represents a single change detected between two API specifications.

    Attributes:
        type: Classification of the change (breaking, potentially_breaking, non_breaking)
        category: Category of change (endpoint, method, parameter, schema, response, request_body, etc.)
        path: API endpoint path (e.g., "/users")
        method: HTTP method (e.g., "GET", "POST")
        field: Optional field name for parameter/schema-level changes
        message: Human-readable explanation of the change
        details: Optional additional details about the change (e.g., schema_path, keyword, old_value, new_value)
    """

    type: ChangeType
    category: ChangeCategory
    path: str
    method: Optional[str] = None
    field_name: Optional[str] = (
        None  # Renamed from 'field' to avoid conflict with dataclasses.field
    )
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert change to dictionary."""
        result = asdict(self)
        # Remove details if empty
        if not result.get("details"):
            result.pop("details", None)
        # Remove None values for cleaner output
        return {k: v for k, v in result.items() if v is not None}

    def __str__(self) -> str:
        """String representation of the change."""
        parts = [f"[{self.type.upper()}]"]

        if self.method:
            parts.append(f"{self.method} {self.path}")
        else:
            parts.append(self.path)

        if self.field_name:
            parts.append(f"- Field: {self.field_name}")

        parts.append(f"- {self.message}")

        if self.details:
            for key, value in self.details.items():
                parts.append(f"  {key}: {value}")

        return " ".join(parts)


@dataclass
class DiffResult:
    """
    Complete diff result containing summary and all detected changes.

    Attributes:
        summary: Summary statistics of the changes
        changes: List of all detected changes
        old_version: Version info from the old spec
        new_version: Version info from the new spec
    """

    summary: Dict[str, Any]
    changes: list[Change]
    old_version: Optional[str] = None
    new_version: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        result = {
            "summary": self.summary,
            "changes": [change.to_dict() for change in self.changes],
        }

        if self.old_version:
            result["old_version"] = self.old_version
        if self.new_version:
            result["new_version"] = self.new_version

        return result

    def get_changes_by_type(self, change_type: str) -> list[Change]:
        """
        Get all changes of a specific type.

        Args:
            change_type: The type to filter by (breaking, potentially_breaking, non_breaking)

        Returns:
            List of changes matching the type
        """
        return [change for change in self.changes if change.type == change_type]

    def get_changes_by_category(self, category: str) -> list[Change]:
        """
        Get all changes of a specific category.

        Args:
            category: The category to filter by (endpoint, method, parameter, etc.)

        Returns:
            List of changes matching the category
        """
        return [change for change in self.changes if change.category == category]

    def get_changes_by_path(self, path: str) -> list[Change]:
        """
        Get all changes for a specific path.

        Args:
            path: The API path to filter by

        Returns:
            List of changes for the path
        """
        return [change for change in self.changes if change.path == path]

    def has_breaking_changes(self) -> bool:
        """Check if there are any breaking changes."""
        return any(change.type == "breaking" for change in self.changes)

    def has_potentially_breaking_changes(self) -> bool:
        """Check if there are any potentially breaking changes."""
        return any(change.type == "potentially_breaking" for change in self.changes)

    def __str__(self) -> str:
        """String representation of the diff result."""
        lines = ["Diff Summary:", "=" * 50]

        if self.old_version or self.new_version:
            lines.append(
                f"Comparing: {self.old_version or 'unknown'} → {self.new_version or 'unknown'}"
            )
            lines.append("")

        lines.append(f"Total changes: {len(self.changes)}")
        lines.append(f"Breaking: {self.summary.get('breaking', 0)}")
        lines.append(
            f"Potentially breaking: {self.summary.get('potentially_breaking', 0)}"
        )
        lines.append(f"Non-breaking: {self.summary.get('non_breaking', 0)}")
        lines.append("")

        if self.changes:
            lines.append("Changes:")
            lines.append("-" * 50)
            for change in self.changes:
                lines.append(str(change))

        return "\n".join(lines)
