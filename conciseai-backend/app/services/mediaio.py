import subprocess, json

def probe_duration_sec(video_path: str) -> int:
    # Uses ffprobe to get duration in seconds (int)
    cmd = [
        "ffprobe","-v","error","-show_entries","format=duration",
        "-of","json", video_path
    ]
    out = subprocess.check_output(cmd)
    duration = float(json.loads(out)["format"]["duration"])
    return int(duration)
   

