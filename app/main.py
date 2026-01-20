"""Main FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.routes import health, compare

# Create FastAPI app
app = FastAPI(
    title="SpecDrift",
    description="API Contract Drift Detector",
    version="0.1.0",
)

# Include routers
app.include_router(health.router)
app.include_router(compare.router)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Template rendering
from fastapi.templating import Jinja2Templates

template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the landing page."""
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
async def upload(request: Request):
    """Render the upload page."""
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/result", response_class=HTMLResponse)
async def result_page(request: Request):
    """Render the result page."""
    return templates.TemplateResponse("result.html", {"request": request})

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    """Render the privacy policy page."""
    return templates.TemplateResponse("privacypolicy.html", {"request": request})

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve favicon."""
    favicon_path = static_dir / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    return {"status": "not found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
