"""Main FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from datetime import date
from xml.sax.saxutils import escape
from app.routes import health, compare
from app.config import ADSENSE_PUBLISHER_ID, SITE_URL

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
templates.env.globals["site_url"] = SITE_URL


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the landing page."""
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
async def upload(request: Request):
    """Render the upload page."""
    return templates.TemplateResponse("upload.html", {"request": request, "enable_ads": False})


@app.get("/result", response_class=HTMLResponse)
async def result_page(request: Request):
    """Render the result page."""
    return templates.TemplateResponse("result.html", {"request": request, "enable_ads": False})

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    """Render the privacy policy page."""
    return templates.TemplateResponse("privacypolicy.html", {"request": request})


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """Render the about page."""
    return templates.TemplateResponse("about.html", {"request": request, "enable_ads": False})


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    """Render the contact page."""
    return templates.TemplateResponse("contact.html", {"request": request, "enable_ads": False})


@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    """Render the terms page."""
    return templates.TemplateResponse("terms.html", {"request": request, "enable_ads": False})


@app.get("/guides", response_class=HTMLResponse)
async def guides(request: Request):
    """Render the guides index."""
    return templates.TemplateResponse("guides.html", {"request": request, "enable_ads": False})


@app.get("/guides/how-specdrift-works", response_class=HTMLResponse)
async def how_specdrift_works(request: Request):
    """Render the SpecDrift working principle guide."""
    return templates.TemplateResponse("guide_how_specdrift_works.html", {"request": request, "enable_ads": False})


@app.get("/guides/openapi-breaking-changes", response_class=HTMLResponse)
async def openapi_breaking_changes(request: Request):
    """Render the OpenAPI breaking changes guide."""
    return templates.TemplateResponse("guide_breaking_changes.html", {"request": request, "enable_ads": False})


@app.get("/guides/api-versioning-checklist", response_class=HTMLResponse)
async def api_versioning_checklist(request: Request):
    """Render the API versioning checklist."""
    return templates.TemplateResponse("guide_versioning_checklist.html", {"request": request, "enable_ads": False})


@app.get("/guides/api-contract-testing-ci", response_class=HTMLResponse)
async def api_contract_testing_ci(request: Request):
    """Render the API contract testing CI guide."""
    return templates.TemplateResponse("guide_contract_testing_ci.html", {"request": request, "enable_ads": False})


@app.get("/guides/swagger-vs-openapi-compatibility", response_class=HTMLResponse)
async def swagger_vs_openapi_compatibility(request: Request):
    """Render the Swagger and OpenAPI compatibility guide."""
    return templates.TemplateResponse("guide_swagger_openapi.html", {"request": request, "enable_ads": False})


@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots_txt():
    """Expose crawler instructions."""
    return PlainTextResponse(
        "\n".join(
            [
                "User-agent: *",
                "Allow: /",
                "Disallow: /result",
                f"Sitemap: {SITE_URL}/sitemap.xml",
                "",
            ]
        )
    )


@app.get("/ads.txt", response_class=PlainTextResponse, include_in_schema=False)
async def ads_txt():
    """Declare the authorized Google ad seller account."""
    return PlainTextResponse(f"google.com, {ADSENSE_PUBLISHER_ID}, DIRECT, f08c47fec0942fa0\n")


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    """Expose indexable public pages."""
    today = date.today().isoformat()
    pages = [
        ("/", "daily", "1.0"),
        ("/upload", "weekly", "0.8"),
        ("/guides", "weekly", "0.9"),
        ("/guides/how-specdrift-works", "monthly", "0.8"),
        ("/guides/openapi-breaking-changes", "monthly", "0.8"),
        ("/guides/api-versioning-checklist", "monthly", "0.8"),
        ("/guides/api-contract-testing-ci", "monthly", "0.8"),
        ("/guides/swagger-vs-openapi-compatibility", "monthly", "0.8"),
        ("/about", "monthly", "0.6"),
        ("/privacy", "yearly", "0.4"),
        ("/terms", "yearly", "0.4"),
        ("/contact", "yearly", "0.3"),
    ]
    urls = "\n".join(
        "  <url>"
        f"<loc>{escape(SITE_URL + path)}</loc>"
        f"<lastmod>{today}</lastmod>"
        f"<changefreq>{changefreq}</changefreq>"
        f"<priority>{priority}</priority>"
        "</url>"
        for path, changefreq, priority in pages
    )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n"
    )
    return Response(content=body, media_type="application/xml")

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
