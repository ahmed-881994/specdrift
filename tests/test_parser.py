"""Unit tests for OpenAPI/Swagger parser validation."""

import pytest

from app.core.parser import ParseError, Parser


def test_parse_openapi_31_allows_components_without_paths():
    """OpenAPI 3.1 documents can be component-only."""
    content = """
openapi: 3.1.0
info:
  title: Component Library
  version: 1.0.0
components:
  schemas:
    User:
      type: object
"""

    spec = Parser.parse(content, "yaml")

    assert spec["openapi"] == "3.1.0"
    assert "components" in spec


def test_parse_openapi_31_allows_webhooks_without_paths():
    """OpenAPI 3.1 documents can define webhooks without paths."""
    content = """
openapi: 3.1.0
info:
  title: Webhook API
  version: 1.0.0
webhooks:
  user.created:
    post:
      responses:
        '200':
          description: OK
"""

    spec = Parser.parse(content, "yaml")

    assert spec["openapi"] == "3.1.0"
    assert "webhooks" in spec


def test_parse_openapi_31_requires_paths_components_or_webhooks():
    """OpenAPI 3.1 still needs at least one API surface section."""
    content = """
openapi: 3.1.0
info:
  title: Empty API
  version: 1.0.0
"""

    with pytest.raises(ParseError, match="paths.*components.*webhooks"):
        Parser.parse(content, "yaml")


def test_parse_openapi_30_still_requires_paths():
    """OpenAPI 3.0 validation keeps the existing paths requirement."""
    content = """
openapi: 3.0.3
info:
  title: Component Library
  version: 1.0.0
components:
  schemas:
    User:
      type: object
"""

    with pytest.raises(ParseError, match="paths"):
        Parser.parse(content, "yaml")
