import asyncio
import json

from app.routes.compare import sample_specs


def test_sample_specs_returns_petstore_pair():
    response = asyncio.run(sample_specs())

    assert response.status_code == 200
    payload = json.loads(response.body)
    assert payload["name"] == "Swagger Petstore"
    assert payload["old"]["label"] == "Swagger Petstore 2.0"
    assert payload["old"]["source_url"] == "https://petstore.swagger.io/v2/swagger.json"
    assert payload["old"]["content"].startswith('swagger: "2.0"')
    assert payload["new"]["label"] == "Swagger Petstore OpenAPI 3.1"
    assert (
        payload["new"]["source_url"]
        == "https://petstore31.swagger.io/api/v31/openapi.json"
    )
    assert payload["new"]["content"].startswith("openapi: 3.1.0")
