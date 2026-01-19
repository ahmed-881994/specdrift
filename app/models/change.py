"""Data models for API changes."""

from typing import Literal, Optional
from dataclasses import dataclass, asdict


@dataclass
class Change:
    """
    Represents a single change detected between two API specifications.
    
    Attributes:
        type: Classification of the change (breaking, potentially_breaking, non_breaking)
        category: Category of change (endpoint, method, parameter, schema, response)
        path: API endpoint path (e.g., "/users")
        method: HTTP method (e.g., "GET", "POST")
        field: Optional field name for schema-level changes
        message: Human-readable explanation of the change
    """
    type: Literal["breaking", "potentially_breaking", "non_breaking"]
    category: Literal["endpoint", "method", "parameter", "schema", "response"]
    path: str
    method: Optional[str] = None
    field: Optional[str] = None
    message: str = ""

    def to_dict(self) -> dict:
        """Convert change to dictionary."""
        return asdict(self)


@dataclass
class DiffResult:
    """
    Complete diff result containing summary and all detected changes.
    """
    summary: dict
    changes: list[Change]

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "summary": self.summary,
            "changes": [change.to_dict() for change in self.changes]
        }
