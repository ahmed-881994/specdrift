```
├── 📄 README.md                       # Complete documentation
├── 📄 QUICKSTART.md                   # Setup and run guide
├── 📄 IMPLEMENTATION_SUMMARY.md        # Detailed checklist
├── 📄 requirements.txt                 # Python dependencies
├── 🐳 Dockerfile                      # Container configuration
├── 📋 .gitignore                      # Git ignore rules
│
└── 📁 app/                            # Main application
    ├── __init__.py                    # Package marker
    ├── main.py                        # FastAPI entry point
    ├── config.py                      # Configuration
    │
    ├── 📁 core/                       # Core diffing logic
    │   ├── __init__.py
    │   ├── parser.py                  # Parse OpenAPI/Swagger specs
    │   ├── normalizer.py              # Normalize spec formats
    │   ├── differ.py                  # Core diff algorithm (★ Main logic)
    │   ├── rules.py                   # Classification rules (10+3+6 rules)
    │   └── classifier.py              # Classify changes
    │
    ├── 📁 models/                     # Data models
    │   ├── __init__.py
    │   └── change.py                  # Change data structure
    │
    ├── 📁 services/                   # Business logic
    │   ├── __init__.py
    │   └── diff_service.py            # Service orchestration
    │
    ├── 📁 routes/                     # API endpoints
    │   ├── __init__.py
    │   ├── compare.py                 # /api/compare endpoints
    │   └── health.py                  # /health endpoint
    │
    ├── 📁 templates/                  # HTML templates
    │   ├── layout.html                # Base layout
    │   ├── upload.html                # Main interface (★ Web UI)
    │   └── result.html                # Results page
    │
    └── 📁 static/                     # Static assets
        └── style.css                  # Minimal CSS styling

└── 📁 tests/                          # Test suite
    ├── __init__.py
    └── test_diff.py                   # Unit tests
```

## File Purpose Reference

### Root Level
- **README.md** - Full documentation with examples and limitations
- **QUICKSTART.md** - Get started in 5 minutes
- **IMPLEMENTATION_SUMMARY.md** - Detailed completion checklist
- **requirements.txt** - FastAPI, PyYAML, pytest, etc.
- **Dockerfile** - Production container with health checks
- **.gitignore** - Ignore __pycache__, .venv, etc.

### app/main.py
Entry point. Sets up FastAPI, includes routers, mounts static files, renders templates.

### app/core/ (★ The Brain)
- **parser.py** - Reads JSON/YAML specs and validates structure
- **normalizer.py** - Converts Swagger 2.0 and OpenAPI 3.x to common format
- **differ.py** - Compares normalized specs, detects all changes
- **rules.py** - Defines 19 classification rules
- **classifier.py** - Applies rules to create structured Change objects

### app/models/change.py
Data class representing a single detected change with type, category, path, method, field, message.

### app/services/diff_service.py
Orchestrates: Parse → Normalize → Diff → Classify → Return JSON

### app/routes/
- **compare.py** - POST /api/compare (text), POST /api/compare-files (files)
- **health.py** - GET /health

### app/templates/upload.html (★ The UI)
Single-page form with:
- Tab switching (Upload/Paste)
- File inputs for both old and new specs
- Client-side file reading
- AJAX request to /api/compare
- Real-time result display with severity colors

### app/static/style.css
Responsive design, color-coded by severity, minimal and clean.

### tests/test_diff.py
6 test cases covering:
- Endpoint removal detection
- Required field addition detection
- Type change detection
- Summary accuracy
- Error handling

## Key Features

✅ **10 Breaking Rules**
  - Endpoint removed, Method removed, Required param/field added, Type changes, Response removed

✅ **3 Potentially Breaking Rules**
  - Non-2xx response removed, Enum added, Default removed

✅ **6 Non-Breaking Rules**
  - New endpoint, New method, Optional param/field added, New response

✅ **Deterministic Diffing**
  - Rule-based classification (no AI/ML)
  - Consistent, predictable behavior

✅ **Production Ready**
  - Error handling
  - Input validation
  - Docker support
  - Unit tests
  - Documentation

## Quick Statistics

| Metric | Count |
|--------|-------|
| Python files | 16 |
| HTML templates | 3 |
| Test files | 1 |
| Classification rules | 19 |
| Diff categories | 5 |
| Total files | 28 |
| Lines of code | ~2,500 |

## Running the App

```bash
# Development
cd api-drift-detector
pip install -r requirements.txt
uvicorn app.main:app --reload

# Production (Docker)
docker build -t specdrift .
docker run -p 8000:8000 specdrift

# Testing
pytest tests/ -v
```

Visit: **http://localhost:8000**
