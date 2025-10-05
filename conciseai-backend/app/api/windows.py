from flask import Blueprint, Response, jsonify, stream_with_context
from app.sse.broker import subscribe
from app.services.storage import list_windows, read_json, video_json_path

bp = Blueprint("windows", __name__)

@bp.get("/videos/<video_id>/events")
def events(video_id):
    def stream():
        for msg in subscribe(video_id):
            yield f"data: {msg}\n\n"
    return Response(stream_with_context(stream()), mimetype="text/event-stream")

@bp.get("/videos/<video_id>")
def video_state(video_id):
    v = read_json(video_json_path(video_id))
    if not v: return jsonify({"error":"not found"}), 404
    return jsonify(v)

@bp.get("/videos/<video_id>/windows")
def windows(video_id):
    return jsonify(list_windows(video_id))
