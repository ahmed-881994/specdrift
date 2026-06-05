# SpecDrift Application Manual

## Purpose

SpecDrift is a FastAPI web application that compares two Swagger 2.0 or OpenAPI 3.x API specifications and reports contract drift. The application accepts an "old" specification and a "new" specification, parses both documents, normalizes them into a common internal shape, walks their API surfaces, classifies every detected difference, and displays the result as a grouped, filterable report.

The application is intentionally deterministic. It does not use AI, semantic guessing, or text-based diffing. It compares parsed API contract structures such as paths, methods, parameters, request bodies, responses, schemas, reusable components, webhooks, callbacks, security settings, and selected metadata.

## Main Runtime Pieces

The core application is organized around a small request pipeline:

| Layer | Files | Responsibility |
| --- | --- | --- |
| FastAPI app | `app/main.py` | Creates the app, registers routers, serves templates and static files. |
| Compare routes | `app/routes/compare.py` | Receives pasted specs, uploaded files, or URL fetch requests. |
| Fetch service | `app/services/spec_fetcher.py` | Safely fetches remote spec text from public HTTP or HTTPS URLs. |
| Diff service | `app/services/diff_service.py` | Orchestrates format detection, parsing, diffing, and report metadata. |
| Parser | `app/core/parser.py` | Parses JSON/YAML and validates basic Swagger/OpenAPI structure. |
| Normalizer | `app/core/normalizer.py` | Converts Swagger 2.0 and OpenAPI 3.x documents into a comparable shape. |
| Differ | `app/core/differ.py` | Performs the detailed comparison and emits change objects. |
| Classifier/rules | `app/core/classifier.py`, `app/core/rules.py` | Converts detected differences into breaking, risky, or safe classifications. |
| Result presenter | `app/services/result_presenter.py` | Builds grouped report metadata for the browser UI. |
| Templates | `app/templates/upload.html`, `app/templates/result.html` | Collect input and render comparison results. |

## How the Application Accepts Input

### Browser Pages

The public browser flow starts at `/upload`. The page presents two input panels:

- `spec[A] old`: the baseline or previously released API specification.
- `spec[B] new`: the candidate or updated API specification.

Each side supports three input modes:

1. Paste raw YAML or JSON into the textarea.
2. Upload a `.json`, `.yaml`, or `.yml` file.
3. Fetch a specification from a URL.

The page also includes convenience actions:

- `Beautify`: formats JSON with `JSON.stringify`; if JSON parsing fails, it tries YAML formatting through the browser-loaded `js-yaml` library.
- `Swap`: swaps the old and new textarea contents.
- `Clear`: resets the form.
- Live metadata: byte count, line count, and a best-effort version label from `info.version`.

Uploaded files and fetched URL content are copied into the same textarea-backed state before comparison. This means the submit path always sends textual spec content, regardless of whether the user pasted, uploaded, or fetched it.

### Compare Submission

When the user clicks `Compare specs`, JavaScript in `app/templates/upload.html`:

1. Calls `getSpecContent("old")` and `getSpecContent("new")`.
2. Reads active URL input if needed by calling `/api/fetch-spec`.
3. Reads selected files using the browser `File.text()` API if needed.
4. Falls back to the textarea content.
5. Creates a `FormData` payload with:
   - `old_spec`: old specification text.
   - `new_spec`: new specification text.
6. Sends the payload to `POST /api/compare`.

If the backend returns an error, the upload page displays it inline. If the backend succeeds, the browser stores the JSON response in `sessionStorage` under `comparisonResult` and navigates to `/result`.

### API Endpoints

SpecDrift exposes three comparison-related API endpoints.

#### `POST /api/fetch-spec`

Accepts form data:

| Field | Meaning |
| --- | --- |
| `url` | HTTP or HTTPS URL pointing to a JSON/YAML API specification. |

The route calls `fetch_spec_from_url(url.strip())` and returns:

```json
{
  "content": "raw specification text"
}
```

Remote fetching is deliberately constrained:

- Only `http://` and `https://` URLs are allowed.
- The URL must include a host.
- DNS resolution must succeed.
- Every resolved address must be public/global.
- Redirect destinations are revalidated before following them.
- The request times out after 10 seconds.
- The response is limited to 2 MB.
- The response must decode as text.

These checks reduce the risk of server-side request forgery and oversized downloads.

#### `POST /api/compare`

Accepts form data:

| Field | Meaning |
| --- | --- |
| `old_spec` | Raw old specification content. |
| `new_spec` | Raw new specification content. |

Both fields are required. The route passes both strings to `DiffService.compare_specs()` and returns the serialized diff result as JSON.

#### `POST /api/compare-files`

Accepts multipart file uploads:

| Field | Meaning |
| --- | --- |
| `old_file` | Old spec file. |
| `new_file` | New spec file. |

The route reads both files, decodes them as UTF-8 text, calls `DiffService.compare_specs()`, and returns the same JSON structure as `/api/compare`.

The browser UI currently submits to `/api/compare`; `/api/compare-files` exists as a direct API option.

## Input Parsing and Validation

Parsing happens in `Parser.parse()` after `DiffService.compare_specs()` detects each format.

### Format Detection

`Parser.detect_format()` uses a simple rule:

- If trimmed content starts with `{`, treat it as JSON.
- Otherwise, treat it as YAML.

The caller can also provide explicit formats to `DiffService.compare_specs()` using `old_format` and `new_format`, as the tests do for fixture files.

### Supported Document Types

The parser accepts:

- OpenAPI 3.x documents using the root `openapi` field.
- Swagger 2.0 documents using the root `swagger` field.

The parsed value must be a JSON object, represented internally as a Python dictionary.

### Required Top-Level Structure

All specs must include:

- `info`
- Either `openapi` or `swagger`

For most specs, `paths` is required. OpenAPI 3.1 receives special handling: it can be accepted when it has at least one of:

- `paths`
- `components`
- `webhooks`

This allows component-only OpenAPI 3.1 files to be compared.

### Parsing Errors

Invalid JSON, invalid YAML, empty content, unsupported file types, missing required root fields, or non-object documents raise `ParseError`. `DiffService` converts parser errors into `ValueError`, and the compare routes return HTTP 400 with a user-readable message.

## How the Comparison Pipeline Works

The main backend pipeline is implemented by `DiffService.compare_specs()`:

1. Detect old and new formats when format is `auto`.
2. Parse the old and new content.
3. Create a `Differ`.
4. Call `Differ.diff(old_spec, new_spec)`.
5. Convert the `DiffResult` to a dictionary.
6. Add a `report` object from `build_result_report()`.
7. Return the complete result to the route.

The comparison itself is not a textual diff. The app parses both specs, normalizes them, then compares the resulting structures.

## Normalization

The normalizer converts Swagger 2.0 and OpenAPI 3.x into a shared internal model so the differ can use one comparison algorithm.

### OpenAPI 3.x Normalization

For OpenAPI 3.x, the normalizer preserves or normalizes:

- `version`
- `info`
- `servers`
- `security`
- `tags`
- `externalDocs`
- `jsonSchemaDialect`
- `paths`
- `path_metadata`
- `components`
- `webhooks`

Path items are reduced to supported HTTP operations:

- `get`
- `post`
- `put`
- `delete`
- `patch`
- `options`
- `head`

Each operation preserves key metadata such as summary, description, operation ID, tags, deprecation status, security, servers, callbacks, and external docs.

### Swagger 2.0 Normalization

Swagger 2.0 documents are converted toward OpenAPI 3-style shapes:

- `host`, `basePath`, and `schemes` become an OpenAPI-style `servers` list.
- `definitions` become `components.schemas`.
- `securityDefinitions` become `components.securitySchemes`.
- Body parameters become `requestBody`.
- Response schemas become response `content` entries.
- Parameter schemas are wrapped under `schema`.
- Response headers are normalized into a shared schema-bearing shape.

This allows Swagger 2.0 and OpenAPI 3.x specs to be compared with the same downstream logic.

### Nullable and Type Normalization

OpenAPI 3.0 `nullable: true` is normalized into a type set that includes `null`. For example:

```yaml
type: string
nullable: true
```

is treated like:

```yaml
type:
  - string
  - null
```

This lets type comparisons handle nullable transitions consistently.

### Local Reference Utilities

`app/core/schema_utils.py` includes a `SchemaResolver` for local JSON Pointer references. It supports:

- Local refs beginning with `#/`.
- Compatibility between `#/definitions/...` and `#/components/schemas/...`.
- Circular reference detection using `x-specdrift-circular-ref`.

The differ also builds a component reference index from operations and webhooks. That index lets component-level changes include `impacted_operations` when a changed reusable component is referenced by specific operations.

## What the Differ Compares

`Differ.diff()` is the central comparison method. It resets state, extracts version labels, builds component reference information, normalizes both specs, and then compares the following surfaces.

### Root Metadata

The differ compares API-level metadata:

- `servers`
- `security`
- `tags`
- `externalDocs`
- `info.contact`
- `info.license`
- OpenAPI 3.1 `jsonSchemaDialect`

Metadata changes are classified conservatively:

- Adding security requirements is breaking.
- Removing security requirements is non-breaking.
- Changing security requirements is risky.
- Adding servers is safe.
- Removing or changing servers is risky.
- General documentation metadata changes are safe.
- JSON Schema dialect changes are risky.

### Endpoints and Methods

The differ compares path keys under `paths`.

Endpoint rules:

- Removed endpoint: breaking.
- Added endpoint: safe.

For common paths, it compares HTTP methods.

Method rules:

- Removed method: breaking.
- Added method: safe.

### Operation Metadata

For operations that exist in both specs, the differ compares:

- `summary`
- `description`
- `operationId`
- `tags`
- `deprecated`
- `security`
- `servers`
- `externalDocs`
- `callbacks`

Important classifications:

- Operation ID changes are risky.
- Marking an operation deprecated is risky.
- Removing deprecation is safe.
- Security/server changes follow the metadata rules above.
- General metadata changes are safe.

### Parameters

Parameters are grouped by location:

- `query`
- `path`
- `header`
- `cookie`

For each location, the differ compares parameter names, required flags, schema types, validation constraints, and serialization settings.

Parameter rules:

- Removed parameter: breaking.
- Added required parameter: breaking.
- Added optional parameter: safe.
- Type change: breaking.
- Optional parameter made required: breaking.
- Required parameter made optional: risky.
- Serialization changes such as `style`, `explode`, `allowReserved`, `allowEmptyValue`, `collectionFormat`, or parameter `content`: breaking.

### Request Bodies

The differ compares request body presence, required status, media types, and schemas.

Request body rules:

- Removed request body: breaking.
- Added required request body: breaking.
- Added optional request body: safe.
- Existing request body made required: breaking.
- Existing request body made optional: risky.
- Removed request media type: breaking.
- Added request media type: safe.

For content types present in both specs, it recursively compares the schemas.

### Responses

The differ compares response status codes, response media types, response schemas, and response headers.

Response rules:

- Removed 2xx response: breaking.
- Removed non-2xx response: risky.
- Added response status: safe.
- Removed response media type: breaking.
- Added response media type: safe.
- Removed response header: risky.
- Added response header: safe.
- Changed response header object: risky.

For response schemas present in both specs, it recursively compares fields and constraints.

### Schemas and Fields

Schema comparison is recursive. It compares:

- Type values.
- Object `properties`.
- Required property lists.
- Array `items`.
- Tuple-style OpenAPI 3.1 / JSON Schema `prefixItems`.
- Map-like `additionalProperties`.
- Composition keywords `allOf`, `oneOf`, `anyOf`, and `not`.
- Validation keywords and constraints.

Schema field rules:

- Removed field: breaking.
- Added required request field: breaking.
- Added optional request field: safe.
- Added response field: safe.
- Field type change: breaking.
- Request field made required: breaking.
- Response field made required: risky.
- Field made optional: risky.

Field names are built as paths such as `schema.user.email`, `User.email`, `schema[]`, `schema.*`, or `schema.oneOf[0]` depending on where the change occurs.

### Schema Constraints

The differ compares JSON Schema and OpenAPI validation keywords, including:

- `enum`
- `default`
- numeric limits such as `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`
- string constraints such as `minLength`, `maxLength`, `pattern`, `format`
- array constraints such as `minItems`, `maxItems`, `uniqueItems`, `contains`, `minContains`, `maxContains`
- object constraints such as `minProperties`, `maxProperties`, `propertyNames`, `dependentRequired`, `dependentSchemas`
- conditional and unevaluated keywords such as `if`, `then`, `else`, `unevaluatedProperties`, `unevaluatedItems`
- content keywords such as `contentEncoding`, `contentMediaType`, `contentSchema`
- OpenAPI 3.0 `example` and OpenAPI 3.1 `examples`, compared through a shared representation

Constraint rules:

- Removed enum value: breaking.
- Added enum value: risky.
- Added enum where none existed: breaking because the schema became stricter.
- Removed enum entirely: safe because the schema became looser.
- Removed default: risky.
- Added default: safe.
- Changed default: risky.
- Constraint made stricter: breaking.
- Constraint made looser: safe.
- Ambiguous constraint change: risky.

The differ decides stricter vs looser for comparable numeric constraints. For example, raising `minimum` is stricter; raising `maximum` is looser.

### Reusable Components

The differ compares reusable component maps:

- `schemas`
- `parameters`
- `responses`
- `requestBodies`
- `headers`
- `securitySchemes`
- `examples`
- `callbacks`
- `pathItems`

Component rules:

- Added component: safe.
- Removed referenced component: breaking.
- Removed unreferenced component: risky.
- Changed non-schema component: risky.
- Changed reusable schema: recursively compared like any other schema.

When a changed schema component is referenced by operations, nested schema changes include `impacted_operations`, such as `POST /users`.

### Webhooks

For OpenAPI 3.1 `webhooks`, the differ compares webhook names and nested operations.

Webhook rules:

- Removed webhook: breaking.
- Added webhook: safe.
- Removed webhook operation: breaking.
- Added webhook operation: safe.
- Existing webhook operations are compared with the same operation-level logic used for normal paths.

### Callbacks

For operation callbacks, the differ compares:

- Callback names.
- Runtime-expression path items.
- Callback operations.
- Nested callback operation contracts.

Callback rules:

- Removed callback: breaking.
- Added callback: safe.
- Changed callback object: risky.
- Removed callback URL expression: breaking.
- Added callback URL expression: safe.
- Removed callback operation: breaking.
- Added callback operation: safe.

## Classification Model

Every detected change becomes a `Change` object with:

| Field | Meaning |
| --- | --- |
| `type` | `breaking`, `potentially_breaking`, or `non_breaking`. |
| `category` | The surface category, such as `endpoint`, `parameter`, `schema`, or `response`. |
| `path` | API path, component pointer, webhook name, or related location. |
| `method` | HTTP method when the change belongs to an operation. |
| `field_name` | Parameter, schema node, response, component, media type, header, or metadata field. |
| `message` | Human-readable rule message. |
| `details` | Optional structured context such as spec path, keyword, old value, new value, content type, or impacted operations. |

The three classification levels mean:

- `breaking`: likely to break existing clients or integrations.
- `potentially_breaking`: requires review because client impact depends on behavior, tooling, or usage.
- `non_breaking`: generally additive or less restrictive.

Unknown or ambiguous rules default to `potentially_breaking`.

## Result JSON Shape

The backend returns a JSON object like this:

```json
{
  "summary": {
    "breaking": 1,
    "potentially_breaking": 2,
    "non_breaking": 3,
    "total": 6
  },
  "changes": [
    {
      "type": "breaking",
      "category": "parameter",
      "path": "/users",
      "method": "GET",
      "field_name": "id",
      "message": "Required request parameter added",
      "details": {
        "location": "query",
        "required": true,
        "schema_path": "#/paths/~1users/get/parameters/0"
      }
    }
  ],
  "old_version": "Example API v1.0.0",
  "new_version": "Example API v2.0.0",
  "report": {
    "total": 6,
    "facets": {
      "types": [],
      "categories": [],
      "surfaces": []
    },
    "groups": []
  }
}
```

`old_version` and `new_version` are included only when `info.version` exists. If `info.title` also exists, the label is formatted as `Title vVersion`; otherwise it is `vVersion`.

## How Results Are Prepared for Display

Before returning the response, `DiffService` calls `build_result_report()` from `app/services/result_presenter.py`. This creates presentation metadata that helps the frontend render a readable report without reimplementing all grouping logic.

The report includes:

- `total`: total number of changes.
- `facets.types`: counts for Breaking, Risky, and Safe.
- `facets.categories`: counts for categories such as request parameters, response statuses, content types, headers, and reusable components.
- `facets.surfaces`: counts for higher-level surfaces.
- `groups`: grouped changes with per-group counts.

Surfaces are inferred as:

| Surface | Meaning |
| --- | --- |
| `operations` | Endpoint and operation-level changes. |
| `components` | Reusable schemas and components. |
| `webhooks` | OpenAPI webhook changes. |
| `callbacks` | Callback request changes. |
| `global` | API-level settings such as security, servers, and metadata. |

Groups are sorted by severity first:

1. Breaking groups.
2. Risky groups.
3. Safe groups.

Within the same severity, groups are sorted by surface and title.

## How the Browser Displays Results

The `/result` page reads `comparisonResult` from `sessionStorage`. If no result exists, it displays an error asking the user to run a comparison first.

When a result exists, `displayResults()` renders:

1. A summary header.
2. Version comparison text when available.
3. Three summary metric buttons:
   - Breaking
   - Risky
   - Safe
4. A filter panel for:
   - API surface.
   - Change category.
5. Grouped change sections.
6. A "Compare another spec" link back to `/upload`.

After rendering, the page removes `comparisonResult` from `sessionStorage`. The result is therefore intended as a one-time browser handoff, not persistent history.

### Filtering

Metric cards and filter chips are interactive. The user can filter by:

- Classification type.
- Surface.
- Category.

Filters are combined. For example, choosing `Breaking` and `Reusable schemas` shows only breaking component changes. The `Show All` button clears active filters.

### Change Rows

Each change row displays:

- Impact label: `BREAKING`, `RISKY`, or `SAFE`.
- Category label.
- Method and path when available.
- Field, parameter, component, header, media type, or schema node when available.
- Human-readable message.
- Structured details.

Structured details may include:

- `schema_path`: JSON Pointer to the affected spec location.
- Metadata chips such as keyword, location, content type, status code, required flag, callback name, and ref.
- `impacted_operations` for referenced component changes.
- Old and new values, with complex objects shown inside expandable `<details>` blocks.

## Error Handling

The backend returns:

- HTTP 400 for invalid input, failed parsing, unsupported spec shape, or URL fetch validation/fetch errors.
- HTTP 500 for unexpected route-level failures.

The compare route wraps unexpected diff errors as `ValueError`, so most comparison-time failures surface as HTTP 400 with a message beginning `Unexpected error during comparison:`.

The browser displays errors in the upload page's error panel and keeps the user on the input screen.

## Privacy and Persistence

SpecDrift does not store comparisons in a database. The current browser flow keeps results only in `sessionStorage` long enough to move from `/upload` to `/result`. Backend routes process the submitted content for the request and return the result immediately.

URL-based fetching happens server-side, so the backend temporarily retrieves the remote specification text. The fetch service does not persist the fetched content.

## Known Functional Boundaries

SpecDrift is strongest at structural contract comparison. It does not attempt to prove runtime behavior compatibility.

Important boundaries:

- Format detection is simple: leading `{` means JSON, otherwise YAML.
- Parsing validates only basic Swagger/OpenAPI structure, not full schema compliance.
- Remote URL fetches are limited to public HTTP/HTTPS resources up to 2 MB.
- Comparison is deterministic and rule-based.
- Ambiguous changes are classified as risky.
- The app compares many schema keywords but does not execute validators or test real API behavior.
- Results are not persisted or versioned.
- Authentication is not implemented in the app routes.

## End-to-End Example Flow

1. A user opens `/upload`.
2. The user pastes an old OpenAPI spec into `spec[A]`.
3. The user uploads a new YAML spec into `spec[B]`.
4. The browser reads the uploaded file as text and copies it into the new spec textarea.
5. The user clicks `Compare specs`.
6. The browser sends `old_spec` and `new_spec` as `FormData` to `/api/compare`.
7. FastAPI validates that both fields are present.
8. `DiffService` detects JSON/YAML formats.
9. `Parser` parses and validates both specs.
10. `Differ` extracts version labels, builds component reference context, and normalizes both specs.
11. The differ compares metadata, components, endpoints, operations, parameters, request bodies, responses, webhooks, callbacks, and schemas.
12. Each detected difference is classified by `Classifier` and `rules.py`.
13. `DiffResult` calculates summary counts.
14. `result_presenter` builds filterable report groups.
15. The backend returns JSON.
16. The browser stores the JSON in `sessionStorage` and navigates to `/result`.
17. `/result` renders summary metrics, filters, grouped changes, spec paths, old/new values, and impacted operations.
18. The browser clears the stored result after display.

## Developer Notes

Useful commands:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
pytest tests/ -v
```

Representative tests live in:

- `tests/test_diff.py`
- `tests/test_parser.py`
- `tests/test_normalizer.py`
- `tests/test_result_presenter.py`
- `tests/test_spec_fetcher.py`
- `tests/test_openapi31_fixtures.py`
- `tests/test_swagger20_fixtures.py`

These tests document expected behavior for core diffing, parsing, normalization, URL fetching, result grouping, Swagger 2.0 compatibility, and OpenAPI 3.1 fixture comparisons.
