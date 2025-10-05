import os
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

class Config:
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")
    MEDIA_URL = "/media"
    WINDOW_SECONDS = 600  # 10 minutes
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB
    ALLOWED_EXTENSIONS = {"mp4", "mov", "mkv"}
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
