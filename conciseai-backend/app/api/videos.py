import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.services import storage, mediaio
from app.workers.runner import submit_stream_job
from app.sse.broker import publish

bp = Blueprint("videos", __name__)

def _allowed(filename, allowed):
    ext = filename.rsplit(".", 1)[-1].lower()
    return "." in filename and ext in allowed

@bp.post("")
def upload_video():
    f = request.files.get("file")
    if not f or f.filename == "":
        return jsonify({"error":"file required"}), 400
    if not _allowed(f.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        return jsonify({"error":"unsupported file type"}), 400

    vid = storage.new_id("v")
    vdir = storage.video_dir(vid)
    os.makedirs(vdir, exist_ok=True)
    master_path = os.path.join(vdir, "master." + f.filename.rsplit(".",1)[-1].lower())
    f.save(master_path)

    # Probe duration & init state
    duration = mediaio.probe_duration_sec(master_path)
    state = storage.init_video_state(vid, f.filename, duration, current_app.config["WINDOW_SECONDS"])
    publish(vid, {"type":"video_started","id":vid,"duration_sec":duration})

    # Kick pipeline
    submit_stream_job(vid, master_path)
    return jsonify({"id": vid, "status": state["status"], "window_seconds": state["window_seconds"]}), 201
