# app/services/frames.py
"""
Hybrid vital-frame extractor for lecture videos (windowed).
Signals:
  - Entropy: measures visual information (slides/board changes).
  - OCR length: text density proxy (more text ⇒ likely important slide).
  - Optional semantic relevance: sentence-transformers similarity to lecture prompts.

Usage:
  select(video_path, t_start, t_end, out_dir, candidate_fps=2.0, top_k=6)
Returns:
  [{"t": <seconds>, "name": "000.jpg"}, ...]   # sorted by time
"""

import os, subprocess, glob, tempfile
from typing import List, Dict, Tuple, Optional
import numpy as np

# Optional deps
try:
    import cv2
except Exception:
    cv2 = None

try:
    import pytesseract
except Exception:
    pytesseract = None

_ST_MODEL = None
try:
    # small & fast; adjust if you prefer a different one from your notebook
    from sentence_transformers import SentenceTransformer, util as st_util
    _ST_MODEL = None  # lazy init below
except Exception:
    SentenceTransformer = None
    st_util = None

# ---------------- ffmpeg helpers ----------------

def _ensure_dir(p: str): os.makedirs(p, exist_ok=True)

def _extract_window_pngs(video_path: str, t_start: float, t_end: float, tmp_dir: str, fps: float):
    """
    Decode ONLY [t_start, t_end) into PNGs at `fps` using ffmpeg input seeking.
    """
    _ensure_dir(tmp_dir)
    for f in glob.glob(os.path.join(tmp_dir, "*.png")):
        try: os.remove(f)
        except: pass
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(t_start), "-to", str(t_end), "-i", video_path,
        "-vf", f"fps={fps}",
        "-q:v", "2",
        os.path.join(tmp_dir, "%06d.png"),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _timestamp_from_index(idx_zero_based: int, t_start: float, fps: float) -> float:
    return t_start + (idx_zero_based / fps)

# ---------------- scoring primitives ----------------

def _entropy_score(img: np.ndarray) -> float:
    """Shannon entropy on grayscale histogram (0..~8)."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray],[0],None,[256],[0,256]).ravel()
    p = hist / (hist.sum() + 1e-8)
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())

def _ocr_len_score(img: np.ndarray) -> float:
    """
    OCR character count as a proxy for slide/board density.
    Requires Tesseract installed; returns 0 if pytesseract is unavailable.
    """
    if pytesseract is None:
        return 0.0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # light denoise → binarize helps on lecture slides
    gray = cv2.medianBlur(gray, 3)
    text = pytesseract.image_to_string(gray)
    return float(len(text.strip()))

def _semantic_score(
    img: np.ndarray,
    prompt_emb: Optional[np.ndarray]
) -> float:
    """
    Optional semantic relevance using sentence-transformers.
    We embed OCR text and compare to a lecture-like prompt.
    If ST model or pytesseract missing, returns 0.
    """
    if SentenceTransformer is None or st_util is None or pytesseract is None:
        return 0.0
    global _ST_MODEL
    if _ST_MODEL is None:
        # small model keeps latency low; align with your notebook if different
        _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    # Extract text
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    text = pytesseract.image_to_string(gray).strip()
    if not text:
        return 0.0
    emb = _ST_MODEL.encode([text], convert_to_tensor=True, normalize_embeddings=True)
    if prompt_emb is None:
        # Build a default “lecture summary relevance” prompt
        prompt = "lecture slide key points equations definitions theorems summary topic headings"
        prompt_emb = _ST_MODEL.encode([prompt], convert_to_tensor=True, normalize_embeddings=True)
    sim = st_util.cos_sim(emb, prompt_emb)[0][0].item()
    return float(sim)

# ---------------- hybrid score ----------------

def _hybrid_score(
    img: np.ndarray,
    prompt_emb: Optional[np.ndarray],
    ocr_norm: float = 200.0,
    w_entropy: float = 0.55,
    w_ocr: float = 0.30,
    w_sem: float = 0.15,
) -> float:
    """
    Weighted combination. Tune weights to match your notebook.
    """
    e = _entropy_score(img)                     # ~[0..8]
    o = _ocr_len_score(img) / max(ocr_norm, 1)  # normalize OCR length
    s = _semantic_score(img, prompt_emb)        # ~[-1..1], usually [0..1]
    # Clamp semantics into [0,1] for stability
    s = max(0.0, min(1.0, s))
    return w_entropy * e + w_ocr * o + w_sem * s

# ---------------- main API ----------------

def select(
    video_path: str,
    t_start: float,
    t_end: float,
    out_dir: str,
    candidate_fps: float = 2.0,
    top_k: int = 6,
    min_gap_factor: float = 1.5,
    lecture_prompt: Optional[str] = None
) -> List[Dict]:
    """
    1) Extract candidate frames at `candidate_fps` within [t_start, t_end)
    2) Score via hybrid entropy+OCR(+semantic)
    3) Select top_k with temporal spacing
    4) Save to out_dir as JPGs
    Returns: [{"t": seconds, "name": "000.jpg"}, ...] sorted by t
    """
    if cv2 is None:
        raise RuntimeError("OpenCV (cv2) is required. `pip install opencv-python`")

    _ensure_dir(out_dir)

    # Optional: prepare a semantic prompt embedding once
    st_prompt_emb = None
    if lecture_prompt and SentenceTransformer is not None:
        global _ST_MODEL
        if _ST_MODEL is None:
            _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        st_prompt_emb = _ST_MODEL.encode([lecture_prompt], convert_to_tensor=True, normalize_embeddings=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        _extract_window_pngs(video_path, t_start, t_end, tmp_dir, fps=candidate_fps)
        pngs = sorted(glob.glob(os.path.join(tmp_dir, "*.png")))
        if not pngs:
            return []

        # Score each candidate
        scored: List[Tuple[str, float]] = []
        for p in pngs:
            img = cv2.imread(p)
            if img is None:
                continue
            s = _hybrid_score(img, prompt_emb=st_prompt_emb)
            scored.append((p, float(s)))

        # Sort desc by score
        scored.sort(key=lambda x: x[1], reverse=True)

        # Temporal spacing
        keep: List[Dict] = []
        min_gap_seconds = max(5.0, (t_end - t_start) / (top_k * min_gap_factor))

        def idx_from_png(path: str) -> int:
            base = os.path.splitext(os.path.basename(path))[0]
            return int(base)  # %06d

        for p, s in scored:
            if len(keep) >= top_k:
                break
            idx0 = idx_from_png(p) - 1
            t_est = _timestamp_from_index(idx0, t_start, candidate_fps)
            if any(abs(t_est - k["t"]) < min_gap_seconds for k in keep):
                continue
            keep.append({"path": p, "score": s, "t": t_est})

        # Ensure chronological order for UX
        keep.sort(key=lambda d: d["t"])

        # Write final JPGs to out_dir and return names
        results: List[Dict] = []
        for i, item in enumerate(keep):
            name = f"{i:03d}.jpg"
            out_path = os.path.join(out_dir, name)
            # Convert PNG->JPG with ffmpeg for consistency
            subprocess.run(
                ["ffmpeg", "-y", "-i", item["path"], out_path],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            results.append({"t": round(float(item["t"]), 3), "name": name})

        return results
