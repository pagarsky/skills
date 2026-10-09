"""Transcribe audio.wav with parakeet-mlx (NVIDIA Parakeet-TDT-0.6b-v3 on Apple MLX).

Outputs:
    transcript.json   words + segments with timestamps
    transcript.srt    human-readable subtitles
    transcribe.json   timing/meta
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from static_ffmpeg import add_paths as _ffmpeg_add_paths
_ffmpeg_add_paths()  # parakeet-mlx shells out to ffmpeg for audio load

from parakeet_mlx import from_pretrained


MODEL_ID = "mlx-community/parakeet-tdt-0.6b-v3"


def fmt_srt_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:
        ms, s = 0, s + 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(segments) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{fmt_srt_ts(seg.start)} --> {fmt_srt_ts(seg.end)}")
        lines.append(seg.text.strip())
        lines.append("")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("audio")
    p.add_argument("--out-dir", default=None)
    p.add_argument("--chunk-duration", type=float, default=120.0,
                   help="seconds per attention chunk (Parakeet default 120s)")
    p.add_argument("--overlap", type=float, default=15.0,
                   help="overlap seconds between chunks")
    args = p.parse_args()

    audio = Path(args.audio).resolve()
    out = Path(args.out_dir) if args.out_dir else audio.parent

    t0 = time.time()
    model = from_pretrained(MODEL_ID)
    load_sec = time.time() - t0

    t1 = time.time()
    result = model.transcribe(
        audio,
        chunk_duration=args.chunk_duration,
        overlap_duration=args.overlap,
    )
    transcribe_sec = time.time() - t1

    # The result has .text, .sentences (with start/end + tokens), and tokens (word-level).
    # Normalise into a stable JSON shape.
    sentences = []
    for s in getattr(result, "sentences", []) or []:
        sentences.append({
            "start": float(s.start),
            "end": float(s.end),
            "text": s.text.strip(),
            "duration": float(s.duration) if hasattr(s, "duration") else float(s.end - s.start),
        })

    words = []
    for tok in getattr(result, "tokens", []) or []:
        words.append({
            "start": float(tok.start),
            "end": float(tok.end),
            "text": tok.text,
        })

    transcript = {
        "model": MODEL_ID,
        "audio_path": str(audio),
        "text": result.text,
        "sentences": sentences,
        "words": words,
    }
    (out / "transcript.json").write_text(json.dumps(transcript, indent=2, ensure_ascii=False))

    # SRT from sentences (one cue per sentence is fine for our purpose).
    class _Seg:
        __slots__ = ("start", "end", "text")
        def __init__(self, s):
            self.start = s["start"]; self.end = s["end"]; self.text = s["text"]
    (out / "transcript.srt").write_text(to_srt([_Seg(s) for s in sentences]))

    audio_dur_sec = sentences[-1]["end"] if sentences else 0.0
    timings = {
        "model": MODEL_ID,
        "model_load_sec": round(load_sec, 2),
        "transcribe_sec": round(transcribe_sec, 2),
        "audio_duration_sec": round(audio_dur_sec, 2),
        "rtfx": round(audio_dur_sec / max(transcribe_sec, 1e-6), 2),
        "n_sentences": len(sentences),
        "n_words": len(words),
        "chars": len(result.text),
    }
    (out / "transcribe.json").write_text(json.dumps(timings, indent=2))
    print(json.dumps(timings, indent=2))


if __name__ == "__main__":
    main()
