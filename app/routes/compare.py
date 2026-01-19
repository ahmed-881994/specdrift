"""
API comparison routes.

Handles uploading specs and returning diff results.
"""

from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from app.services.diff_service import DiffService

router = APIRouter()


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
