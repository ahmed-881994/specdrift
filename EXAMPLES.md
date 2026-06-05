# SpecDrift Examples

This document is the example cookbook for SpecDrift. The README keeps examples short; this file shows complete request patterns, compact spec pairs, expected change highlights, and a few richer cases that exercise the comparison engine.

Run the app locally before trying the API examples:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Example 1: Request Parameter And Response Additions

This pair shows three common release changes:

- A query parameter changes type.
- A new required query parameter is added.
- A response field and response status are added.

### Old Spec

Save as `old-users.yaml`:

```yaml
openapi: 3.0.0
info:
  title: Users API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
      parameters:
        - name: limit
          in: query
          required: false
          schema:
            type: integer
      responses:
        "200":
          description: Users returned
          content:
            application/json:
              schema:
                type: object
                properties:
                  users:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: integer
                        name:
                          type: string
```

### New Spec

Save as `new-users.yaml`:

```yaml
openapi: 3.0.0
info:
  title: Users API
  version: 1.1.0
paths:
  /users:
    get:
      summary: List users
      parameters:
        - name: limit
          in: query
          required: false
          schema:
            type: string
        - name: offset
          in: query
          required: true
          schema:
            type: integer
      responses:
        "200":
          description: Users returned
          content:
            application/json:
              schema:
                type: object
                properties:
                  users:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: integer
                        name:
                          type: string
                        email:
                          type: string
                  total:
                    type: integer
        "400":
          description: Bad request
```

### Compare

```bash
curl -X POST http://localhost:8000/api/compare-files \
  -F "old_file=@old-users.yaml" \
  -F "new_file=@new-users.yaml"
```

### Expected Highlights

| Type | Category | Location | Why |
| --- | --- | --- | --- |
| Breaking | `parameter` | `GET /users limit` | `limit` changed from integer to string. |
| Breaking | `parameter` | `GET /users offset` | Required request parameter was added. |
| Safe | `schema` | `GET /users response_200 users[].email` | Response field was added. |
| Safe | `schema` | `GET /users response_200 total` | Response field was added. |
| Safe | `response` | `GET /users 400` | New response status was added. |

## Example 2: Required Request Field Added

This pair shows one of the most important breaking changes: an existing request body now requires a new field.

### Old Spec

```yaml
openapi: 3.0.0
info:
  title: Signup API
  version: 1.0.0
paths:
  /signup:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - name
              properties:
                name:
                  type: string
                email:
                  type: string
      responses:
        "201":
          description: Created
```

### New Spec

```yaml
openapi: 3.0.0
info:
  title: Signup API
  version: 1.1.0
paths:
  /signup:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - name
                - email
              properties:
                name:
                  type: string
                email:
                  type: string
      responses:
        "201":
          description: Created
```

### Expected Highlight

SpecDrift reports `email` as breaking because an existing request field became required.

Relevant result shape:

```json
{
  "type": "breaking",
  "category": "schema",
  "path": "/signup",
  "method": "POST",
  "field_name": "schema.email",
  "message": "Field made required"
}
```

## Example 3: Schema Constraints And Enum Drift

This pair shows validation-rule changes. SpecDrift reports stricter constraints as breaking, looser constraints as safe, and ambiguous constraint changes as risky.

### Old Spec

```yaml
openapi: 3.1.0
info:
  title: Orders API
  version: 1.0.0
paths:
  /orders:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - status
                - quantity
              properties:
                status:
                  type: string
                  enum:
                    - pending
                    - paid
                    - cancelled
                quantity:
                  type: integer
                  minimum: 1
                  maximum: 100
      responses:
        "201":
          description: Created
```

### New Spec

```yaml
openapi: 3.1.0
info:
  title: Orders API
  version: 1.1.0
paths:
  /orders:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - status
                - quantity
              properties:
                status:
                  type: string
                  enum:
                    - pending
                    - paid
                    - refunded
                quantity:
                  type: integer
                  minimum: 5
                  maximum: 250
      responses:
        "201":
          description: Created
```

### Expected Highlights

| Type | Field | Why |
| --- | --- | --- |
| Breaking | `schema.status` | Enum value `cancelled` was removed. |
| Risky | `schema.status` | Enum value `refunded` was added. |
| Breaking | `schema.quantity` | `minimum` increased from `1` to `5`, making validation stricter. |
| Safe | `schema.quantity` | `maximum` increased from `100` to `250`, making validation looser. |

## Example 4: Reusable Component Impact

When reusable schemas change, SpecDrift can attach impacted operations when those components are referenced from paths or webhooks.

### Old Spec

```yaml
openapi: 3.1.0
info:
  title: Catalog API
  version: 1.0.0
paths:
  /products:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/Product"
      responses:
        "201":
          description: Created
components:
  schemas:
    Product:
      type: object
      required:
        - name
      properties:
        id:
          type: string
        name:
          type: string
        sku:
          type: string
```

### New Spec

```yaml
openapi: 3.1.0
info:
  title: Catalog API
  version: 1.1.0
paths:
  /products:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/Product"
      responses:
        "201":
          description: Created
components:
  schemas:
    Product:
      type: object
      required:
        - name
        - sku
      properties:
        id:
          type: integer
        name:
          type: string
        sku:
          type: string
```

### Expected Highlights

SpecDrift compares `components.schemas.Product` and reports:

- `Product.id` type changed from string to integer: breaking.
- `Product.sku` became required: breaking.
- `details.impacted_operations` includes `POST /products`.

Example result fragment:

```json
{
  "type": "breaking",
  "category": "component_schema",
  "path": "#/components/schemas/Product",
  "field_name": "Product.id",
  "message": "Field type changed",
  "details": {
    "schema_path": "#/components/schemas/Product/properties/id/type",
    "old_value": "string",
    "new_value": "integer",
    "impacted_operations": ["POST /products"]
  }
}
```

## Example 5: Swagger 2.0 Compatibility

Swagger 2.0 specs are normalized into OpenAPI-style structures before diffing. Body parameters become request bodies, `definitions` become `components.schemas`, and response schemas become content schemas.

### Old Swagger 2.0 Spec

```yaml
swagger: "2.0"
info:
  title: Pets API
  version: 1.0.0
host: api.example.com
basePath: /v1
schemes:
  - https
paths:
  /pets:
    post:
      consumes:
        - application/json
      produces:
        - application/json
      parameters:
        - in: body
          name: body
          required: true
          schema:
            $ref: "#/definitions/Pet"
      responses:
        "201":
          description: Created
          schema:
            $ref: "#/definitions/Pet"
definitions:
  Pet:
    type: object
    required:
      - name
    properties:
      id:
        type: string
      name:
        type: string
```

### New Swagger 2.0 Spec

```yaml
swagger: "2.0"
info:
  title: Pets API
  version: 1.1.0
host: api.example.com
basePath: /v1
schemes:
  - https
paths:
  /pets:
    post:
      consumes:
        - application/json
      produces:
        - application/json
      parameters:
        - in: body
          name: body
          required: true
          schema:
            $ref: "#/definitions/Pet"
      responses:
        "201":
          description: Created
          schema:
            $ref: "#/definitions/Pet"
definitions:
  Pet:
    type: object
    required:
      - name
      - tag
    properties:
      id:
        type: string
      name:
        type: string
      tag:
        type: string
```

### Expected Highlight

The added required `tag` field is reported as breaking under the reusable schema component.

## Example 6: OpenAPI 3.1 Webhook Drift

SpecDrift compares OpenAPI 3.1 `webhooks` as first-class API surfaces.

### Old Spec

```yaml
openapi: 3.1.0
info:
  title: Event API
  version: 1.0.0
webhooks:
  order.created:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - id
              properties:
                id:
                  type: string
      responses:
        "200":
          description: Accepted
```

### New Spec

```yaml
openapi: 3.1.0
info:
  title: Event API
  version: 1.1.0
webhooks:
  order.paid:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - id
              properties:
                id:
                  type: string
      responses:
        "200":
          description: Accepted
```

### Expected Highlights

- Removed `order.created` webhook: breaking.
- Added `order.paid` webhook: safe.

## Example 7: Built-In Sample Pair

The repository includes two larger sample specs:

- `samples/petstore2.0.yml`
- `samples/petstore3.1.yml`

Compare them with:

```bash
curl -X POST http://localhost:8000/api/compare-files \
  -F "old_file=@samples/petstore2.0.yml" \
  -F "new_file=@samples/petstore3.1.yml"
```

This is intentionally a noisy comparison because it crosses Swagger 2.0 and OpenAPI 3.1. It is useful for seeing route-level, metadata, response, request body, component, and schema changes in one result.

To inspect only counts:

```bash
curl -s -X POST http://localhost:8000/api/compare-files \
  -F "old_file=@samples/petstore2.0.yml" \
  -F "new_file=@samples/petstore3.1.yml" \
  | python -m json.tool
```

## Request Examples

### Compare Files

```bash
curl -X POST http://localhost:8000/api/compare-files \
  -F "old_file=@old.yaml" \
  -F "new_file=@new.yaml"
```

### Compare Text Content

Use `--form-string` when passing file contents as form fields so curl treats the spec as literal text.

```bash
curl -X POST http://localhost:8000/api/compare \
  --form-string "old_spec=$(cat old.yaml)" \
  --form-string "new_spec=$(cat new.yaml)"
```

### Fetch A Public Remote Spec

```bash
curl -X POST http://localhost:8000/api/fetch-spec \
  -F "url=https://example.com/openapi.yaml"
```

URL fetch safeguards:

- URL must start with `http://` or `https://`.
- Host must resolve to public internet addresses.
- Redirect destinations are revalidated.
- Response size is capped at 2 MB.
- Response text must decode successfully.
- Request timeout is 10 seconds.

### Python Requests

```python
import requests

with open("old.yaml", "r", encoding="utf-8") as old_file:
    old_spec = old_file.read()

with open("new.yaml", "r", encoding="utf-8") as new_file:
    new_spec = new_file.read()

response = requests.post(
    "http://localhost:8000/api/compare",
    data={
        "old_spec": old_spec,
        "new_spec": new_spec,
    },
    timeout=30,
)
response.raise_for_status()

result = response.json()
print("Breaking:", result["summary"]["breaking"])
print("Risky:", result["summary"]["potentially_breaking"])
print("Safe:", result["summary"]["non_breaking"])

for change in result["changes"]:
    print(change["type"], change["category"], change.get("method"), change["path"], change["message"])
```

### JavaScript Fetch

```javascript
async function compareSpecs(oldSpec, newSpec) {
  const formData = new FormData();
  formData.append("old_spec", oldSpec);
  formData.append("new_spec", newSpec);

  const response = await fetch("/api/compare", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Comparison failed");
  }

  return response.json();
}
```

## Reading Result Objects

Each item in `changes` follows this shape:

```json
{
  "type": "breaking",
  "category": "schema_constraint",
  "path": "/orders",
  "method": "POST",
  "field_name": "schema.quantity",
  "message": "Schema constraint made stricter",
  "details": {
    "location": "request_body",
    "keyword": "minimum",
    "old_value": 1,
    "new_value": 5,
    "schema_path": "#/paths/~1orders/post/requestBody/content/application~1json/schema/properties/quantity/minimum"
  }
}
```

Important fields:

| Field | Meaning |
| --- | --- |
| `type` | `breaking`, `potentially_breaking`, or `non_breaking`. |
| `category` | Change surface such as `parameter`, `schema`, `response`, `component_schema`, `webhook`, or `metadata`. |
| `path` | Endpoint path, component pointer, webhook name, or related API surface. |
| `method` | HTTP method when the change belongs to an operation. |
| `field_name` | Changed parameter, schema node, response, media type, component, or metadata field. |
| `message` | Human-readable rule message. |
| `details.schema_path` | JSON Pointer to the relevant spec location. |
| `details.old_value` / `details.new_value` | Values before and after the change when useful. |
| `details.impacted_operations` | Operations that reference a changed reusable component. |

## Quick Validation Checklist

Use these small scenarios to sanity-check a running SpecDrift instance:

| Scenario | Expected classification |
| --- | --- |
| Remove `/users` from the new spec | Breaking |
| Add `GET /users/{id}` to the new spec | Safe |
| Add required query parameter `offset` | Breaking |
| Add optional query parameter `sort` | Safe |
| Change `id` from `string` to `integer` | Breaking |
| Add response field `email` | Safe |
| Remove response field `name` | Breaking |
| Remove a `200` response | Breaking |
| Remove a `404` response | Risky |
| Add enum value `archived` | Risky |
| Remove enum value `draft` | Breaking |
| Increase `minimum` from `1` to `5` | Breaking |
| Increase `maximum` from `100` to `250` | Safe |
