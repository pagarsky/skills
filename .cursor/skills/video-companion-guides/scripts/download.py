"""Download a YouTube video as audio (wav 16k mono) and video (mp4) for frame work.

Two modes:
    Whole video (default): pulls the full audio + video stream — bandwidth-bound, fast.
    Section: pass --end (and optional --start) to download only [start, end). Uses
    yt-dlp's download_ranges which is slower per-second but useful for snippet tests.

Outputs to work/<video_id>/{audio.wav,video.mp4,download.json}.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

from static_ffmpeg import add_paths as _ffmpeg_add_paths
_ffmpeg_add_paths()  # exposes static-ffmpeg's bundled ffmpeg/ffprobe on PATH

import yt_dlp

FFMPEG = shutil.which("ffmpeg")
FFMPEG_DIR = str(Path(FFMPEG).parent) if FFMPEG else None


def download(video_id: str, out_dir: Path, start: int | None = None,
             end: int | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    url = f"https://www.youtube.com/watch?v={video_id}"
    section_mode = end is not None

    common = {
        "ffmpeg_location": FFMPEG_DIR,
        "quiet": True,
        "noprogress": True,
        # speeds whole-video pulls when YouTube serves DASH fragments
        "concurrent_fragment_downloads": 4,
    }
    if section_mode:
        common["download_ranges"] = yt_dlp.utils.download_range_func(None, [(start or 0, end)])
        common["force_keyframes_at_cuts"] = True

    t0 = time.time()
    audio_opts = {
        **common,
        "format": "bestaudio/best",
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "wav", "preferredquality": "0"},
        ],
        "outtmpl": str(out_dir / "audio.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(audio_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    audio_dl = time.time() - t0

    # Re-encode to mono 16 kHz so Parakeet can ingest directly.
    raw_wav = out_dir / "audio.wav"
    final_wav = out_dir / "audio_16k.wav"
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", str(raw_wav),
         "-ac", "1", "-ar", "16000", str(final_wav)],
        check=True,
    )
    raw_wav.unlink()
    final_wav.rename(out_dir / "audio.wav")

    t1 = time.time()
    video_opts = {
        **common,
        "format": "bestvideo[ext=mp4][height<=720]/best[ext=mp4][height<=720]/best",
        "outtmpl": str(out_dir / "video.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(video_opts) as ydl:
        ydl.extract_info(url, download=True)
    video_dl = time.time() - t1

    audio_path = out_dir / "audio.wav"
    video_path = next(out_dir.glob("video.*"))
    duration_full_sec = info.get("duration")

    meta = {
        "video_id": video_id,
        "title": info.get("title"),
        "duration_full_sec": duration_full_sec,
        "section": [start or 0, end] if section_mode else [0, duration_full_sec],
        "section_mode": section_mode,
        "audio_path": str(audio_path),
        "audio_size_mb": audio_path.stat().st_size / 1024 / 1024,
        "video_path": str(video_path),
        "video_size_mb": video_path.stat().st_size / 1024 / 1024,
        "audio_download_sec": round(audio_dl, 2),
        "video_download_sec": round(video_dl, 2),
    }
    (out_dir / "download.json").write_text(json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("video_id")
    p.add_argument("--start", type=int, default=None,
                   help="start second (only used with --end)")
    p.add_argument("--end", type=int, default=None,
                   help="end second; if omitted, downloads the whole video")
    p.add_argument("--out", default=None)
    args = p.parse_args()

    out = Path(args.out) if args.out else Path("work") / args.video_id
    if (args.start or 0) == 0 and out.exists():
        for f in ("audio.wav", "download.json"):
            (out / f).unlink(missing_ok=True)
        for v in out.glob("video.*"):
            v.unlink()

    meta = download(args.video_id, out, start=args.start, end=args.end)
    print(json.dumps(meta, indent=2))
