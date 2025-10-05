import os
from flask import Flask, send_from_directory
from .config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Blueprints
    from app.api import videos, windows, health
    app.register_blueprint(videos.bp, url_prefix="/videos")
    app.register_blueprint(windows.bp, url_prefix="/")
    app.register_blueprint(health.bp, url_prefix="/")

    # Dev-only media serving (use nginx in prod)
    @app.route("/media/<path:filename>")
    def media(filename):
        return send_from_directory(app.config["MEDIA_ROOT"], filename)

    return app
