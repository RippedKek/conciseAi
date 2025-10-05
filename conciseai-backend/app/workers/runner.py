from concurrent.futures import ThreadPoolExecutor
from app.pipelines.stream_windows import run

_executor = ThreadPoolExecutor(max_workers=2)

def submit_stream_job(video_id: str, master_path: str):
    _executor.submit(run, video_id, master_path)
