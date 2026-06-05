"""
API comparison routes.

Handles uploading specs and returning diff results.
"""

from pathlib import Path

from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from app.services.diff_service import DiffService
from app.services.spec_fetcher import SpecFetchError, fetch_spec_from_url

router = APIRouter()
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"
PETSTORE_SAMPLE = {
    "name": "Swagger Petstore",
    "description": "Well-known public Swagger/OpenAPI sample specs for a quick demo comparison.",
    "old": {
        "label": "Swagger Petstore 2.0",
        "source_url": "https://petstore.swagger.io/v2/swagger.json",
        "file": "petstore2.0.yml",
    },
    "new": {
        "label": "Swagger Petstore OpenAPI 3.1",
        "source_url": "https://petstore31.swagger.io/api/v31/openapi.json",
        "file": "petstore3.1.yml",
    },
}


@router.get("/api/sample-specs")
async def sample_specs():
    """
    Return demo specifications that can be loaded into the upload editors.
    """
    try:
        old_content = (SAMPLES_DIR / PETSTORE_SAMPLE["old"]["file"]).read_text(
            encoding="utf-8"
        )
        new_content = (SAMPLES_DIR / PETSTORE_SAMPLE["new"]["file"]).read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        raise HTTPException(
            status_code=500, detail="Sample specifications are unavailable"
        ) from exc

    return JSONResponse(
        content={
            "name": PETSTORE_SAMPLE["name"],
            "description": PETSTORE_SAMPLE["description"],
            "old": {
                "label": PETSTORE_SAMPLE["old"]["label"],
                "source_url": PETSTORE_SAMPLE["old"]["source_url"],
                "content": old_content,
            },
            "new": {
                "label": PETSTORE_SAMPLE["new"]["label"],
                "source_url": PETSTORE_SAMPLE["new"]["source_url"],
                "content": new_content,
            },
        }
    )


@router.post("/api/fetch-spec")
async def fetch_spec(
    url: str = Form(..., description="URL of a JSON or YAML API specification"),
):
    """
    Fetch an API specification from a URL.

    Args:
        url: Remote specification URL

    Returns:
        JSON with the fetched specification content
    """
    try:
        content = fetch_spec_from_url(url.strip())
        return JSONResponse(content={"content": content})
    except SpecFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/compare")
async def compare_specs(
    old_spec: str = Form(..., description="Old API specification content"),
    new_spec: str = Form(..., description="New API specification content"),
):
    """
    Compare two API specifications.
    
    Args:
        old_spec: The original API specification (JSON or YAML)
        new_spec: The new API specification (JSON or YAML)
        
    Returns:
        JSON with comparison results
    """
    if not old_spec or not new_spec:
        raise HTTPException(
            status_code=400, detail="Both old_spec and new_spec are required"
        )

    try:
        result = DiffService.compare_specs(old_spec, new_spec)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/compare-files")
async def compare_files(
    old_file: UploadFile = File(..., description="Old API specification file"),
    new_file: UploadFile = File(..., description="New API specification file"),
):
    """
    Compare two API specification files.
    
    Args:
        old_file: The original API specification file
        new_file: The new API specification file
        
    Returns:
        JSON with comparison results
    """
    try:
        old_content = (await old_file.read()).decode("utf-8")
        new_content = (await new_file.read()).decode("utf-8")

        result = DiffService.compare_specs(old_content, new_content)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
