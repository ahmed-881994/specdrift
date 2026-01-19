# SpecDrift Setup & Run Guide

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- pip (or your favorite package manager)

### 1. Setup Environment
```bash
cd api-drift-detector
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the Application
```bash
uvicorn app.main:app --reload
```

The app will be available at: **http://localhost:8000**

### 3. Test the Application
```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_diff.py::TestDiffService::test_detect_removed_endpoint -v
```

## Docker Deployment

### Build
```bash
docker build -t specdrift .
```

### Run
```bash
docker run -p 8000:8000 specdrift
```

## Project Structure Overview

```
api-drift-detector/
├── app/                          # Main application package
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Configuration settings
│   ├── core/                    # Core diffing logic
│   │   ├── parser.py            # Parse OpenAPI/Swagger specs
│   │   ├── normalizer.py        # Normalize spec formats
│   │   ├── differ.py            # Core diff algorithm
│   │   ├── rules.py             # Classification rules
│   │   └── classifier.py        # Classify changes
│   ├── models/                  # Data models
│   │   └── change.py            # Change data structure
│   ├── services/                # Business logic
│   │   └── diff_service.py      # Orchestration service
│   ├── routes/                  # API endpoints
│   │   ├── compare.py           # Comparison endpoints
│   │   └── health.py            # Health check
│   ├── templates/               # HTML templates
│   │   └── upload.html          # Main web interface
│   └── static/                  # Static files
│       └── style.css            # Styling
├── tests/                        # Unit tests
│   └── test_diff.py             # Diff logic tests
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container config
├── README.md                    # Full documentation
└── QUICKSTART.md               # This file
```

## Key Features Implemented

✅ **OpenAPI/Swagger Parsing** - Handles YAML and JSON formats  
✅ **Deterministic Diffing** - Rule-based, no AI/ML  
✅ **Breaking Change Detection** - All 10 breaking change types  
✅ **Potentially Breaking** - 3 rule types  
✅ **Non-Breaking Changes** - 6 rule types  
✅ **Web UI** - Upload and paste options  
✅ **REST API** - JSON endpoints  
✅ **Test Suite** - Comprehensive unit tests  
✅ **Docker Support** - Production-ready containerization  

## API Usage Examples

### Compare via Web Interface
1. Go to http://localhost:8000
2. Upload or paste two specs
3. Click "Compare Specs"

### Via cURL (Text)
```bash
curl -X POST http://localhost:8000/api/compare \
  -d "old_spec=$(cat old.json)" \
  -d "new_spec=$(cat new.json)"
```

### Via cURL (Files)
```bash
curl -X POST http://localhost:8000/api/compare-files \
  -F "old_file=@old.yaml" \
  -F "new_file=@new.yaml"
```

## Response Example

```json
{
  "summary": {
    "breaking": 2,
    "potentially_breaking": 1,
    "non_breaking": 3
  },
  "changes": [
    {
      "type": "breaking",
      "category": "endpoint",
      "path": "/api/users",
      "method": null,
      "field": null,
      "message": "Endpoint removed"
    },
    {
      "type": "non_breaking",
      "category": "method",
      "path": "/api/posts",
      "method": "POST",
      "field": null,
      "message": "New HTTP method"
    }
  ]
}
```

## Troubleshooting

### Port Already in Use
```bash
# Use a different port
uvicorn app.main:app --port 8001
```

### Module Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Tests Failing
```bash
# Install test dependencies explicitly
pip install pytest
pytest tests/ -v
```

## Next Steps

- Try comparing two real OpenAPI specs
- Review the [README.md](README.md) for comprehensive documentation
- Check [tests/test_diff.py](tests/test_diff.py) for expected behavior
- Explore the [app/core/differ.py](app/core/differ.py) for the diff algorithm
