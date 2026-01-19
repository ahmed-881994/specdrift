"""
Diff service that orchestrates the diff process.

Coordinates parsing, normalization, and diffing of specifications.
"""

from typing import Dict, Any
from app.core.parser import Parser, ParseError
from app.core.differ import Differ
from app.models.change import Change, DiffResult


class DiffService:
    """Service for orchestrating API spec diffs."""

    @staticmethod
    def compare_specs(
        old_content: str, new_content: str, old_format: str = "json", new_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Compare two API specifications and return diff result.
        
        Args:
            old_content: Content of the original spec
            new_content: Content of the new spec
            old_format: Format of old spec ("json" or "yaml")
            new_format: Format of new spec ("json" or "yaml")
            
        Returns:
            Dictionary with summary and list of changes
            
        Raises:
            ValueError: If specs cannot be parsed
        """
        try:
            # Auto-detect format if not specified
            if not old_format or old_format == "auto":
                old_format = Parser.detect_format(old_content)
            if not new_format or new_format == "auto":
                new_format = Parser.detect_format(new_content)

            # Parse specifications
            old_spec = Parser.parse(old_content, old_format)
            new_spec = Parser.parse(new_content, new_format)

            # Perform diff
            differ = Differ()
            changes = differ.diff(old_spec, new_spec)

            # Build result
            result = DiffService._build_result(changes)
            return result

        except ParseError as e:
            raise ValueError(f"Specification parsing error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error during comparison: {str(e)}")

    @staticmethod
    def _build_result(changes: list[Change]) -> Dict[str, Any]:
        """
        Build the final diff result with summary and changes.
        
        Args:
            changes: List of detected changes
            
        Returns:
            Dictionary with summary and changes
        """
        summary = {
            "breaking": 0,
            "potentially_breaking": 0,
            "non_breaking": 0,
        }

        for change in changes:
            if change.type == "breaking":
                summary["breaking"] += 1
            elif change.type == "potentially_breaking":
                summary["potentially_breaking"] += 1
            elif change.type == "non_breaking":
                summary["non_breaking"] += 1

        return {
            "summary": summary,
            "changes": [change.to_dict() for change in changes],
        }
