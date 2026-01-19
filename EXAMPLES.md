# Example Configurations and Test Data

## Test OpenAPI Specifications

### Example 1: Simple Old Specification
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "User API v1",
    "version": "1.0.0"
  },
  "paths": {
    "/users": {
      "get": {
        "summary": "List users",
        "parameters": [
          {
            "name": "limit",
            "in": "query",
            "schema": { "type": "integer" }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "users": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "id": { "type": "integer" },
                          "name": { "type": "string" }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "summary": "Create user",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "name": { "type": "string" }
                },
                "required": ["name"]
              }
            }
          }
        },
        "responses": {
          "201": { "description": "Created" }
        }
      }
    }
  }
}
```

### Example 2: Modified New Specification (with changes)
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "User API v2",
    "version": "2.0.0"
  },
  "paths": {
    "/users": {
      "get": {
        "summary": "List users",
        "parameters": [
          {
            "name": "limit",
            "in": "query",
            "schema": { "type": "string" }
          },
          {
            "name": "offset",
            "in": "query",
            "required": true,
            "schema": { "type": "integer" }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "users": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "id": { "type": "integer" },
                          "name": { "type": "string" },
                          "email": { "type": "string" }
                        }
                      }
                    },
                    "total": { "type": "integer" }
                  }
                }
              }
            }
          },
          "400": { "description": "Bad Request" }
        }
      },
      "post": {
        "summary": "Create user",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "name": { "type": "string" },
                  "email": { "type": "string" }
                },
                "required": ["name", "email"]
              }
            }
          }
        },
        "responses": {
          "201": { "description": "Created" }
        }
      }
    },
    "/users/{id}": {
      "get": {
        "summary": "Get user by ID",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "schema": { "type": "integer" }
          }
        ],
        "responses": {
          "200": { "description": "User found" }
        }
      }
    }
  }
}
```

### Expected Changes When Comparing Above:

1. **BREAKING** - Parameter type changed: `/users` GET `limit` (string → integer) ✗ Actually it was integer→string, so BREAKING
2. **BREAKING** - Required parameter added: `/users` GET `offset`
3. **BREAKING** - Required field added: `/users` POST `email` (now required)
4. **BREAKING** - New endpoint: `/users/{id}` GET ✓ Actually this is NON-BREAKING
5. **NON-BREAKING** - New response field: `/users` GET `total`
6. **NON-BREAKING** - New response field: users[].`email`
7. **NON-BREAKING** - New response: `400` error response

## Swagger 2.0 Example

```json
{
  "swagger": "2.0",
  "info": {
    "title": "Pet Store API",
    "version": "1.0.0"
  },
  "paths": {
    "/pets": {
      "get": {
        "parameters": [
          {
            "name": "limit",
            "in": "query",
            "type": "integer"
          }
        ],
        "responses": {
          "200": {
            "description": "List of pets"
          }
        }
      }
    }
  }
}
```

## Docker Environment

```dockerfile
# .env (optional for Docker Compose)
DEBUG=false
```

```bash
# Docker Compose example
version: '3.8'
services:
  specdrift:
    build: .
    ports:
      - "8000:8000"
    environment:
      DEBUG: "false"
```

## API Request Examples

### cURL with Files
```bash
curl -X POST http://localhost:8000/api/compare-files \
  -F "old_file=@old-spec.yaml" \
  -F "new_file=@new-spec.json"
```

### cURL with JSON Strings
```bash
curl -X POST http://localhost:8000/api/compare \
  -d "old_spec={...json...}" \
  -d "new_spec={...json...}"
```

### Python Requests
```python
import requests

old_spec = open('old.json').read()
new_spec = open('new.json').read()

response = requests.post('http://localhost:8000/api/compare', data={
    'old_spec': old_spec,
    'new_spec': new_spec
})

result = response.json()
print(f"Breaking: {result['summary']['breaking']}")
print(f"Potentially Breaking: {result['summary']['potentially_breaking']}")
print(f"Non-Breaking: {result['summary']['non_breaking']}")
```

### JavaScript Fetch
```javascript
const oldSpec = document.getElementById('oldSpec').value;
const newSpec = document.getElementById('newSpec').value;

const formData = new FormData();
formData.append('old_spec', oldSpec);
formData.append('new_spec', newSpec);

fetch('/api/compare', {
  method: 'POST',
  body: formData
})
.then(r => r.json())
.then(result => {
  console.log('Breaking changes:', result.summary.breaking);
})
```

## Test Cases for Validation

### Test: Endpoint Removed (BREAKING)
**Old**: `/users` endpoint exists  
**New**: `/users` endpoint removed  
**Expected**: 1 breaking change

### Test: Required Parameter Added (BREAKING)
**Old**: `GET /users?limit=10` (optional)  
**New**: `GET /users?limit=10&offset=0` (required)  
**Expected**: 1 breaking change (required parameter added)

### Test: Optional Parameter Added (NON-BREAKING)
**Old**: `GET /users` (no parameters)  
**New**: `GET /users?sort=name` (optional)  
**Expected**: 1 non-breaking change

### Test: Response Field Added (NON-BREAKING)
**Old**: Response contains `{ "id", "name" }`  
**New**: Response contains `{ "id", "name", "email" }`  
**Expected**: 1 non-breaking change

### Test: Required Field Added (BREAKING)
**Old**: POST body requires `{ "name" }`  
**New**: POST body requires `{ "name", "email" }`  
**Expected**: 1 breaking change

### Test: Type Changed (BREAKING)
**Old**: `"id": { "type": "string" }`  
**New**: `"id": { "type": "integer" }`  
**Expected**: 1 breaking change

---

Use these examples to test SpecDrift locally and verify all change types are detected correctly!
