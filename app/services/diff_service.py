"""
Diff service that orchestrates the diff process.

Coordinates parsing, normalization, and diffing of specifications.
"""

from typing import Dict, Any
from app.core.parser import Parser, ParseError
from app.core.differ import Differ
from app.services.result_presenter import build_result_report


class DiffService:
    """Service for orchestrating API spec diffs."""

    @staticmethod
    def compare_specs(
        old_content: str, new_content: str, old_format: str = "auto", new_format: str = "auto"
    ) -> Dict[str, Any]:
        """
        Compare two API specifications and return diff result.
        
        Args:
            old_content: Content of the original spec
            new_content: Content of the new spec
            old_format: Format of old spec ("json", "yaml", or "auto")
            new_format: Format of new spec ("json", "yaml", or "auto")
            
        Returns:
            Dictionary with summary, changes, and version info
            
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
            diff_result = differ.diff(old_spec, new_spec)

            # Return DiffResult as dictionary with presentation metadata
            result = diff_result.to_dict()
            result["report"] = build_result_report(result.get("changes", []))
            return result

        except ParseError as e:
            raise ValueError(f"Specification parsing error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error during comparison: {str(e)}")
