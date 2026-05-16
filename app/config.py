"""Application configuration."""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Upload directory
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# App settings
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_FILE_TYPES = {"application/json", "application/x-yaml", "text/yaml", "text/plain"}
SITE_URL = os.getenv("SITE_URL", "https://specdrift.dev").rstrip("/")
ADSENSE_PUBLISHER_ID = os.getenv("ADSENSE_PUBLISHER_ID", "pub-3858220107949234")
