import os, time
from flask import current_app
from app.services import storage, windowing
from app.sse.broker import publish

# For now this writes placeholder files and emits events.
# Replace sleeps with calls to transcription/frames/summarization.

def run(video_id: str, master_path: str):
    v = storage.read_json(storage.video_json_path(video_id))
    if not v: return
    v["status"] = "processing"
    storage.write_video_state(v)

    seconds = v["window_seconds"]
    for win in windowing.windows(v["duration_sec"], seconds):
        idx = win["index"]
        wstate = {
            "id": f"w_{idx:03d}",
            "video_id": video_id,
            "index": idx,
            "t_start": win["t_start"],
            "t_end": win["t_end"],
            "status": "processing",
            "progress": {"phase": "start", "pct": 0}
        }
        storage.write_window_state(video_id, idx, wstate)
        publish(video_id, {"type":"window_started","index":idx})

        # ---- Transcription (placeholder) ----
        time.sleep(0.5)
        wstate["progress"] = {"phase":"transcribe","pct":100}
        # Write minimal transcript file
        tdir = os.path.join(storage.video_dir(video_id), "transcripts")
        os.makedirs(tdir, exist_ok=True)
        tpath = os.path.join(tdir, f"{idx}.json")
        storage._atomic_write_json(tpath, {"segments":[{"t_start": win["t_start"], "t_end": win["t_end"], "text":"(placeholder)"}]})
        wstate["transcript_uri"] = f"/media/videos/{video_id}/transcripts/{idx}.json"
        storage.write_window_state(video_id, idx, wstate)
        publish(video_id, {"type":"window_transcribed","index":idx})

        # ---- Vital frames (placeholder) ----
        time.sleep(0.5)
        fdir = os.path.join(storage.video_dir(video_id), "frames", str(idx))
        os.makedirs(fdir, exist_ok=True)
        # In real code: extract frames; here we just fake a list
        wstate["frames"] = []
        wstate["progress"] = {"phase":"frames","pct":100}
        storage.write_window_state(video_id, idx, wstate)
        publish(video_id, {"type":"window_frames","index":idx})

        # ---- Summarization (placeholder) ----
        time.sleep(0.5)
        sdir = os.path.join(storage.video_dir(video_id), "summaries")
        os.makedirs(sdir, exist_ok=True)
        spath = os.path.join(sdir, f"{idx}.json")
        storage._atomic_write_json(spath, {"summary": f"Summary for window {idx} (placeholder)."})
        wstate["summary_uri"] = f"/media/videos/{video_id}/summaries/{idx}.json"
        wstate["status"] = "done"
        wstate["progress"] = {"phase":"summarize","pct":100}
        storage.write_window_state(video_id, idx, wstate)
        publish(video_id, {"type":"window_done","index":idx,"summary_uri":wstate["summary_uri"]})

        # Update top-level video list
        v = storage.read_json(storage.video_json_path(video_id))
        found = next((w for w in v["windows"] if w["index"] == idx), None)
        brief = {"id": wstate["id"], "index": idx, "t_start": wstate["t_start"], "t_end": wstate["t_end"], "status": wstate["status"]}
        if found: v["windows"][idx] = brief
        else: v["windows"].append(brief)
        storage.write_video_state(v)

    v["status"] = "done"
    storage.write_video_state(v)
    publish(video_id, {"type":"video_done"})
