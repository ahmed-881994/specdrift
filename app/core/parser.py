"""
OpenAPI/Swagger specification parser.

Handles parsing and basic validation of OpenAPI v3 and Swagger specifications
in both JSON and YAML formats.
"""

import json
import yaml
from typing import Any, Dict


class ParseError(Exception):
    """Raised when spec parsing fails."""
    pass


class Parser:
    """Parser for OpenAPI and Swagger specifications."""

    @staticmethod
    def parse(content: str, file_type: str = "json") -> Dict[str, Any]:
        """
        Parse API specification from string content.
        
        Args:
            content: The spec content (JSON or YAML string)
            file_type: Type of file ("json" or "yaml")
            
        Returns:
            Parsed specification as dictionary
            
        Raises:
            ParseError: If parsing or validation fails
        """
        if not content or not content.strip():
            raise ParseError("Specification is empty")

        try:
            if file_type.lower() == "json":
                spec = json.loads(content)
            elif file_type.lower() in ("yaml", "yml"):
                spec = yaml.safe_load(content)
            else:
                raise ParseError(f"Unsupported file type: {file_type}")
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {str(e)}")
        except yaml.YAMLError as e:
            raise ParseError(f"Invalid YAML: {str(e)}")
        except Exception as e:
            raise ParseError(f"Failed to parse specification: {str(e)}")

        if not isinstance(spec, dict):
            raise ParseError("Specification must be a JSON object")

        Parser._validate_spec(spec)
        return spec

    @staticmethod
    def _validate_spec(spec: Dict[str, Any]) -> None:
        """
        Validate basic OpenAPI/Swagger structure.
        
        Args:
            spec: The specification dictionary
            
        Raises:
            ParseError: If validation fails
        """
        # Check for OpenAPI 3.x or Swagger 2.0
        openapi_version = spec.get("openapi")
        swagger_version = spec.get("swagger")

        if not openapi_version and not swagger_version:
            raise ParseError(
                "Specification must include 'openapi' (v3.x) or 'swagger' (v2.0) field"
            )

        # Basic structure checks
        if not spec.get("info"):
            raise ParseError("Specification must include 'info' field")

        if not spec.get("paths"):
            raise ParseError("Specification must include 'paths' field")

    @staticmethod
    def detect_format(content: str) -> str:
        """
        Detect whether content is JSON or YAML.
        
        Args:
            content: The spec content
            
        Returns:
            "json" or "yaml"
        """
        content = content.strip()
        if content.startswith("{"):
            return "json"
        return "yaml"
