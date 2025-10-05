def windows(duration_sec: int, step_sec: int):
    idx, t = 0, 0
    while t < duration_sec:
        yield {"index": idx, "t_start": t, "t_end": min(t + step_sec, duration_sec)}
        idx += 1
        t += step_sec
