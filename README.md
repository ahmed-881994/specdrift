# SpecDrift

SpecDrift is a lightweight web app for comparing two Swagger/OpenAPI specifications and finding API contract drift before it reaches clients.

Paste, upload, or fetch an old spec and a new spec. SpecDrift parses the documents, normalizes Swagger 2.0 and OpenAPI 3.x into a shared model, compares the actual API contract structure, and reports each change as:

- **Breaking**: likely to break existing clients.
- **Risky**: potentially breaking and worth review.
- **Safe**: generally additive or less restrictive.

It is deterministic, rule-based, and built with FastAPI, Jinja2, vanilla browser JavaScript, and PyYAML.

## Why SpecDrift Exists

API diffs are rarely useful when they stop at text changes. A moved YAML block, reformatted JSON, or reordered schema key should not be treated the same as a removed endpoint or a newly required request field.

SpecDrift compares parsed API semantics instead:

- Did an endpoint disappear?
- Did a method get removed?
- Did a query parameter become required?
- Did a response schema lose a field?
- Did a reusable component change in a way that affects real operations?
- Did a media type, webhook, callback, validation rule, or security requirement change?

The result is a release-focused report that helps decide what needs fixing, documenting, testing, or migration planning.

## Highlights

- Compare Swagger 2.0 and OpenAPI 3.x specs.
- Accept JSON or YAML.
- Paste specs, upload files, or fetch public spec URLs.
- Detect endpoint, method, parameter, request body, response, schema, component, webhook, callback, security, server, metadata, media type, header, and validation constraint changes.
- Normalize Swagger 2.0 into OpenAPI-style structures before diffing.
- Support OpenAPI 3.1 component-only specs, webhooks, `jsonSchemaDialect`, and JSON Schema keywords.
- Track referenced reusable components and show impacted operations when possible.
- Return structured JSON for automation.
- Render a grouped, filterable browser report.
- Store no comparison history by default.

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Run Locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000](http://localhost:8000), then go to `/upload` to compare specs.

### Run With Docker

```bash
docker build -t specdrift .
docker run -p 8000:8000 specdrift
```

Open [http://localhost:8000](http://localhost:8000).

### Run With Docker Compose

```bash
docker compose up --build
```

## Using The Web App

1. Open `/upload`.
2. Add the old spec on the left.
3. Add the new spec on the right.
4. Use paste, file upload, or URL fetch for either side.
5. Click **Compare specs**.
6. Review the `/result` report.

The result page shows:

- Summary counts for breaking, risky, and safe changes.
- Version labels from `info.title` and `info.version` when available.
- Filters by severity, API surface, and change category.
- Grouped changes for endpoints, reusable components, webhooks, callbacks, and global settings.
- Spec paths, old/new values, schema keywords, content types, status codes, and impacted operations where available.

The browser passes results from `/upload` to `/result` with `sessionStorage`, then clears them after display.

## Short Examples

### Compare Two Spec Files

```bash
curl -X POST http://localhost:8000/api/compare-files \
  -F "old_file=@old.yaml" \
  -F "new_file=@new.yaml"
```

### Compare Raw Spec Text

```bash
curl -X POST http://localhost:8000/api/compare \
  --form-string "old_spec=$(cat old.yaml)" \
  --form-string "new_spec=$(cat new.yaml)"
```

### Fetch A Public Spec URL

```bash
curl -X POST http://localhost:8000/api/fetch-spec \
  -F "url=https://example.com/openapi.yaml"
```

For fuller examples with complete specs, expected changes, Python requests, JavaScript fetch, Swagger 2.0, OpenAPI 3.1, and component examples, see [EXAMPLES.md](EXAMPLES.md).

## Response Shape

Comparison endpoints return summary counts, raw changes, optional version labels, and grouped report metadata:

```json
{
  "summary": {
    "breaking": 1,
    "potentially_breaking": 0,
    "non_breaking": 1,
    "total": 2
  },
  "changes": [
    {
      "type": "breaking",
      "category": "parameter",
      "path": "/users",
      "method": "GET",
      "field_name": "offset",
      "message": "Required request parameter added"
    }
  ],
  "old_version": "Users API v1.0.0",
  "new_version": "Users API v1.1.0",
  "report": {}
}
```

The `changes` list is the automation-friendly output. The `report` object is used by the browser UI for grouping and filtering.

## What SpecDrift Detects

### Breaking Changes

- Endpoint removed.
- HTTP method removed.
- Required parameter added.
- Parameter removed.
- Parameter type changed.
- Parameter serialization changed.
- Request body removed.
- Required request body added.
- Request body made required.
- Required request field added.
- Request or response field removed.
- Field type changed.
- Request field made required.
- Enum value removed.
- Validation constraint made stricter.
- Referenced reusable component removed.
- Request or response media type removed.
- Security requirement added.
- Success response removed.
- Webhook, callback, or nested callback operation removed.

### Risky Changes

- Non-2xx response removed.
- Enum value added.
- Default value removed or changed.
- Ambiguous validation constraint changed.
- Unreferenced reusable component removed.
- Reusable component changed.
- Response header removed or changed.
- Operation ID changed.
- Operation deprecated.
- Security requirement changed.
- Server removed or changed.
- Parameter, field, or request body made optional.
- JSON Schema dialect changed.
- Webhook or callback changed in an ambiguous way.

### Safe Changes

- Endpoint added.
- HTTP method added.
- Optional parameter added.
- Optional request body added.
- Optional request field added.
- Response field added.
- Response status added.
- Default value added.
- Validation constraint made less restrictive.
- Reusable component added.
- Request or response media type added.
- Response header added.
- Security requirement removed.
- Server added.
- Webhook, callback, or nested callback operation added.
- Operation undeprecated.
- Documentation-only metadata changed.

## How It Works

The comparison pipeline is:

1. `DiffService` detects JSON vs YAML unless a caller provides explicit formats.
2. `Parser` parses each spec and validates basic Swagger/OpenAPI structure.
3. `Normalizer` converts Swagger 2.0 and OpenAPI 3.x into a shared internal representation.
4. `Differ` compares API surfaces and recursively walks schemas.
5. `Classifier` applies deterministic rules from `rules.py`.
6. `DiffResult` calculates summary counts.
7. `result_presenter` groups and labels changes for the web UI.

For a deeper technical walk-through, see [APPLICATION_MANUAL.md](APPLICATION_MANUAL.md).

## Project Structure

```text
specdrift/
├── app/
│   ├── main.py                    # FastAPI application setup
│   ├── config.py                  # Runtime configuration
│   ├── core/
│   │   ├── parser.py              # JSON/YAML parsing and basic validation
│   │   ├── normalizer.py          # Swagger/OpenAPI normalization
│   │   ├── differ.py              # Core comparison engine
│   │   ├── classifier.py          # Change object classification
│   │   ├── rules.py               # Rule messages and severity mapping
│   │   └── schema_utils.py        # Schema helpers and local ref utilities
│   ├── models/
│   │   └── change.py              # Change and DiffResult dataclasses
│   ├── routes/
│   │   ├── compare.py             # Compare and fetch endpoints
│   │   └── health.py              # Health check
│   ├── services/
│   │   ├── diff_service.py        # Comparison orchestration
│   │   ├── result_presenter.py    # Grouped report metadata
│   │   └── spec_fetcher.py        # Safe remote spec fetching
│   ├── templates/                 # Jinja2 pages
│   └── static/                    # CSS and static assets
├── samples/                       # Example specs
├── tests/                         # pytest suite
├── APPLICATION_MANUAL.md          # Detailed technical manual
├── EXAMPLES.md                    # Example specs and API calls
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Configuration

Configuration lives in `app/config.py` and is read from environment variables where applicable. Notable values include:

- `SITE_URL`: used for sitemap and structured metadata.
- `ADSENSE_PUBLISHER_ID`: used for `ads.txt`.
- `DEBUG`: optional boolean-style runtime flag.

## Testing

Run the full test suite:

```bash
pytest tests/ -v
```

The tests cover:

- Parser validation.
- Swagger 2.0 normalization.
- OpenAPI 3.1 fixtures and component-only specs.
- Core diff categories.
- Schema utilities.
- URL fetch safeguards.
- Result presentation grouping.
- Template result behavior.

## Health Check

```bash
curl http://localhost:8000/health
```

## Current Boundaries

- Results are not persisted.
- The app validates basic spec shape, not full OpenAPI compliance.
- The diff is structural and rule-based; it does not execute schema validators or test live API behavior.
- URL fetching is capped at 2 MB and public HTTP/HTTPS only.
- There is no built-in authentication.
- Ambiguous compatibility questions are intentionally classified as risky.

## Documentation

- [APPLICATION_MANUAL.md](APPLICATION_MANUAL.md): detailed explanation of input handling, comparison internals, and result rendering.
- [EXAMPLES.md](EXAMPLES.md): sample specs and API request examples.

## License

MIT License.
