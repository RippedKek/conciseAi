import os
from flask import current_app
from app.services import storage, windowing
from app.sse.broker import publish

# Import your service adapters
from app.services import frames as framesvc
try:
    from app.services import transcription as transcriptionsvc
except Exception:
    transcriptionsvc = None
try:
    from app.services import summarization as summarizationsvc
except Exception:
    summarizationsvc = None

def _ensure_dir(p):  # tiny helper
    os.makedirs(p, exist_ok=True)

def run(video_id: str, master_path: str):
    """
    For each 10-min window:
      1) Transcribe window audio (if available, else write placeholder)
      2) Extract vital frames using your frames.py adapter
      3) (Optional) Align frames<->transcript
      4) Summarize window (if available, else placeholder summary)
      5) Update window state JSON, emit SSE events
    """
    v = storage.read_json(storage.video_json_path(video_id))
    if not v:
        return

    v["status"] = "processing"
    storage.write_video_state(v)

    window_seconds = v.get("window_seconds", 600)

    for win in windowing.windows(v["duration_sec"], window_seconds):
        idx = win["index"]
        # Initialize window state
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
        publish(video_id, {"type": "window_started", "index": idx})

        try:
            # -----------------------
            # 1) TRANSCRIPTION
            # -----------------------
            tdir = os.path.join(storage.video_dir(video_id), "transcripts")
            _ensure_dir(tdir)

            if transcriptionsvc and hasattr(transcriptionsvc, "run"):
                t_result = transcriptionsvc.run(
                    master_path,
                    win["t_start"],
                    win["t_end"],
                    out_dir=tdir
                )
                # Expect t_result like: {"uri": "/media/.../transcripts/<idx>.json", "segments":[...]}
                wstate["transcript_uri"] = t_result.get("uri")
            else:
                # Placeholder transcript
                tpath = os.path.join(tdir, f"{idx}.json")
                storage._atomic_write_json(tpath, {
                    "segments": [
                        {"t_start": win["t_start"], "t_end": win["t_end"], "text": "(transcript placeholder)"}
                    ]
                })
                wstate["transcript_uri"] = f"/media/videos/{video_id}/transcripts/{idx}.json"

            wstate["progress"] = {"phase": "transcribe", "pct": 100}
            storage.write_window_state(video_id, idx, wstate)
            publish(video_id, {"type": "window_transcribed", "index": idx})

            # -----------------------
            # 2) VITAL FRAMES (YOUR NOTEBOOK LOGIC via frames.py)
            # -----------------------
            fdir = os.path.join(storage.video_dir(video_id), "frames", str(idx))
            _ensure_dir(fdir)

            keyframes = framesvc.select(
                master_path,
                win["t_start"],
                win["t_end"],
                fdir,
                candidate_fps=2.0,   # tune to your method
                top_k=6              # tune to your UI/summary needs
            )
            # Convert file names to web URIs
            wstate["frames"] = [
                {"t": fr["t"], "uri": f"/media/videos/{video_id}/frames/{idx}/{fr['name']}"}
                for fr in keyframes
            ]
            wstate["progress"] = {"phase": "frames", "pct": 100}
            storage.write_window_state(video_id, idx, wstate)
            publish(video_id, {"type": "window_frames", "index": idx})

            # -----------------------
            # 3) (Optional) ALIGNMENT
            # -----------------------
            # If you add an alignment service, call it here to attach frame timestamps to nearby transcript segments.
            # Example:
            # from app.services import alignment as alignsvc
            # pairs = alignsvc.attach(keyframes, transcript_json)
            # (Then pass `pairs` into summarization.)

            # -----------------------
            # 4) SUMMARIZATION
            # -----------------------
            sdir = os.path.join(storage.video_dir(video_id), "summaries")
            _ensure_dir(sdir)

            if summarizationsvc and hasattr(summarizationsvc, "summarize_window"):
                # Expected signature:
                # summarize_window(pairs_or_frames, transcript_obj, out_dir, index) -> {"uri": "..."}
                # If you don't have alignment yet, pass frames + transcript separately or adapt your function.
                # Load transcript JSON for convenience:
                transcript_abs = os.path.join(storage.media_root(), wstate["transcript_uri"].lstrip("/"))
                transcript_obj = storage.read_json(transcript_abs) or {}

                summ_res = summarizationsvc.summarize_window(
                    frames=wstate.get("frames", []),
                    transcript=transcript_obj,
                    out_dir=sdir,
                    index=idx
                )
                wstate["summary_uri"] = summ_res.get("uri")
            else:
                # Placeholder summary
                spath = os.path.join(sdir, f"{idx}.json")
                storage._atomic_write_json(spath, {
                    "summary": f"Summary for {int(win['t_start'])}–{int(win['t_end'])} s (placeholder).",
                    "frames": wstate.get("frames", []),
                    "transcript_uri": wstate.get("transcript_uri")
                })
                wstate["summary_uri"] = f"/media/videos/{video_id}/summaries/{idx}.json"

            wstate["status"] = "done"
            wstate["progress"] = {"phase": "summarize", "pct": 100}
            storage.write_window_state(video_id, idx, wstate)
            publish(video_id, {"type": "window_done", "index": idx, "summary_uri": wstate["summary_uri"]})

        except Exception as e:
            # Mark this window failed and continue with the next
            wstate["status"] = "failed"
            wstate["error"] = str(e)
            storage.write_window_state(video_id, idx, wstate)
            publish(video_id, {"type": "window_failed", "index": idx, "error": str(e)})

        # Update top-level video state (brief window list)
        v = storage.read_json(storage.video_json_path(video_id))
        brief = {
            "id": wstate["id"],
            "index": idx,
            "t_start": wstate["t_start"],
            "t_end": wstate["t_end"],
            "status": wstate["status"]
        }
        # Keep windows[] ordered by index
        if len(v.get("windows", [])) <= idx:
            # pad if needed
            while len(v["windows"]) < idx:
                v["windows"].append({"id": f"w_{len(v['windows']):03d}", "index": len(v["windows"]), "status": "skipped"})
            v["windows"].append(brief)
        else:
            v["windows"][idx] = brief
        storage.write_video_state(v)

    # All windows attempted
    v = storage.read_json(storage.video_json_path(video_id)) or {"id": video_id}
    # If any failed, you can keep status "processing" or set "done_with_errors"
    final_status = "done"
    if any(w.get("status") == "failed" for w in v.get("windows", [])):
        final_status = "done_with_errors"
    v["status"] = final_status
    storage.write_video_state(v)
    publish(video_id, {"type": "video_done", "status": final_status})
