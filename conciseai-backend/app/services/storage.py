import os, json, uuid, tempfile
from flask import current_app, send_file

def media_root():
    return current_app.config["MEDIA_ROOT"]

def new_id(prefix="v"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def _atomic_write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def video_dir(video_id):
    return os.path.join(media_root(), "videos", video_id)

def video_json_path(video_id):
    return os.path.join(video_dir(video_id), "video.json")

def init_video_state(video_id, filename, duration_sec, window_seconds):
    vdir = video_dir(video_id)
    os.makedirs(vdir, exist_ok=True)
    state = {
        "id": video_id,
        "filename": filename,
        "status": "processing",
        "duration_sec": duration_sec,
        "window_seconds": window_seconds,
        "windows": []
    }
    _atomic_write_json(video_json_path(video_id), state)
    return state

def write_video_state(state):
    _atomic_write_json(video_json_path(state["id"]), state)

def window_json_path(video_id, index):
    return os.path.join(video_dir(video_id), "windows", f"{index}.json")

def write_window_state(video_id, index, data):
    _atomic_write_json(window_json_path(video_id, index), data)

def list_windows(video_id):
    wdir = os.path.join(video_dir(video_id), "windows")
    if not os.path.isdir(wdir): return []
    out = []
    for name in sorted(os.listdir(wdir), key=lambda x: int(x.split(".")[0])):
        w = read_json(os.path.join(wdir, name))
        if w: out.append(w)
    return out
