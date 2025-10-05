import queue, threading, json
from collections import defaultdict

_queues = defaultdict(list)
_lock = threading.Lock()

def publish(video_id: str, payload: dict):
    msg = json.dumps(payload)
    with _lock:
        for q in list(_queues[video_id]):
            try: q.put_nowait(msg)
            except: pass

def subscribe(video_id: str):
    q = queue.Queue(maxsize=100)
    with _lock:
        _queues[video_id].append(q)
    def gen():
        try:
            while True:
                yield q.get()
        finally:
            with _lock:
                if q in _queues[video_id]:
                    _queues[video_id].remove(q)
    return gen()
