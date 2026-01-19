# SpecDrift - API Contract Drift Detector

A production-ready web tool that detects breaking, potentially breaking, and non-breaking changes between two OpenAPI v3 or Swagger v2 specifications.

## Features

- **OpenAPI/Swagger Support**: Compares OpenAPI 3.x and Swagger 2.0 specifications
- **Multiple Input Methods**: Upload YAML/JSON files or paste specifications directly
- **Comprehensive Change Detection**: Identifies breaking, potentially breaking, and non-breaking changes
- **Clean Web UI**: Minimal, developer-friendly interface with no JavaScript frameworks
- **Deterministic Diffing**: Rule-based diffing with no AI/ML overhead
- **Fast & Lightweight**: Pure Python with FastAPI backend

## What SpecDrift Detects

### Breaking Changes
- Endpoint removed
- HTTP method removed
- Required request parameter added
- Parameter removed
- Parameter type changed
- Required request body field added
- Request/response field removed
- Field type changed
- Enum value removed
- Success response (2xx) removed

### Potentially Breaking Changes
- Non-2xx response removed
- Enum value added
- Default value removed

### Non-Breaking Changes
- New endpoint
- New HTTP method
- New optional parameter
- New optional request field
- New response field
- Metadata-only changes

## Quick Start

### Local Development

1. **Clone and setup**:
   ```bash
   cd api-drift-detector
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run the application**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Access the web interface**:
   Open http://localhost:8000 in your browser

### Using Docker

1. **Build the image**:
   ```bash
   docker build -t specdrift .
   ```

2. **Run the container**:
   ```bash
   docker run -p 8000:8000 specdrift
   ```

3. **Access**:
   Open http://localhost:8000

## API Endpoints

### Web Interface
- `GET /` - Upload page with two file/paste inputs
- `POST /api/compare` - Compare two specifications (form data: old_spec, new_spec)
- `POST /api/compare-files` - Compare two specification files (multipart: old_file, new_file)
- `GET /health` - Health check

### Response Format

```json
{
  "summary": {
    "breaking": 5,
    "potentially_breaking": 2,
    "non_breaking": 3
  },
  "changes": [
    {
      "type": "breaking",
      "category": "endpoint",
      "path": "/api/users",
      "method": "GET",
      "field": null,
      "message": "Endpoint removed"
    },
    {
      "type": "breaking",
      "category": "parameter",
      "path": "/api/users",
      "method": "POST",
      "field": "email",
      "message": "Required request parameter added"
    }
  ]
}
```

## Example Usage

### Using the Web UI
1. Go to http://localhost:8000
2. Either upload two spec files or paste them directly
3. Click "Compare Specs"
4. Review the results

### Using the API
```bash
curl -X POST http://localhost:8000/api/compare \
  -F "old_spec=@old-spec.yaml" \
  -F "new_spec=@new-spec.yaml"
```

Or with text content:
```bash
curl -X POST http://localhost:8000/api/compare \
  -d "old_spec=$(cat old-spec.json)" \
  -d "new_spec=$(cat new-spec.json)"
```

## Project Structure

```
api-drift-detector/
├── app/
│   ├── main.py                 # FastAPI app and routes
│   ├── config.py               # Configuration
│   ├── core/
│   │   ├── parser.py           # OpenAPI/Swagger parsing
│   │   ├── normalizer.py       # Spec normalization
│   │   ├── differ.py           # Core diffing logic
│   │   ├── rules.py            # Classification rules
│   │   └── classifier.py       # Change classification
│   ├── models/
│   │   └── change.py           # Change data models
│   ├── services/
│   │   └── diff_service.py     # Business logic orchestration
│   ├── routes/
│   │   ├── compare.py          # Comparison endpoints
│   │   └── health.py           # Health check endpoint
│   ├── templates/
│   │   ├── upload.html         # Upload interface
│   │   └── result.html         # Results page
│   └── static/
│       └── style.css           # Minimal CSS styling
├── tests/
│   └── test_diff.py            # Unit tests
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
└── README.md                   # This file
```

## Technology Stack

- **Backend**: Python 3.11+, FastAPI
- **Parsing**: PyYAML (for YAML/JSON)
- **Templates**: Jinja2
- **Frontend**: HTML5, CSS3 (no frameworks)
- **Testing**: pytest
- **Deployment**: Docker

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

Tests cover:
- Removed endpoint detection
- Added required field detection
- Type change detection
- Summary count accuracy
- Error handling for invalid specs

## Limitations & Known Constraints

1. **No Database**: Results are not persisted. This is designed for immediate comparisons only.
2. **Simple Type Comparison**: Parameter/field type changes are detected at a basic level (comparing type strings).
3. **No Schema References**: `$ref` in JSON schemas are not deep-resolved. Referenced definitions are not compared.
4. **No Enum/Default Validation**: Detailed enum and default value changes require the schema to explicitly define these fields.
5. **No Semantic Validation**: Does not validate semantic correctness, only structural changes.
6. **No Authentication**: Public endpoint with no access control.

## Roadmap

- [ ] Support JSON Schema `$ref` resolution
- [ ] Detailed enum and default value tracking
- [ ] Batch comparison via CSV
- [ ] OpenAPI 3.1 full support
- [ ] Change history/comparison artifacts storage (optional DB)
- [ ] Integration with CI/CD pipelines (CLI mode)
- [ ] GraphQL schema support
- [ ] Custom rules engine
- [ ] Change impact analysis

## Contributing

This is an MVP. Feedback welcome on:
- Classification accuracy
- UI/UX improvements
- Performance optimizations
- Additional change types

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
1. Check limitations section above
2. Review test cases for expected behavior
3. Ensure specs are valid OpenAPI v3 or Swagger v2

---

Built with ❤️ as a production-ready MVP. Keep it simple, keep it fast.
