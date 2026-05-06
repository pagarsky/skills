"""End-to-end pipeline driver: download -> transcribe -> scenes -> chunk -> rewrite -> render.

Usage:
    # Full video, using videos.py config (or ad-hoc if not registered there):
    uv run python scripts/pipeline.py <video_id>

    # Snippet (testing):
    uv run python scripts/pipeline.py <video_id> --end 600 --suffix 10min

Captures per-stage wall-time + disk usage and writes work/<id>/pipeline.json.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "scripts"))
from videos import by_id, Video  # noqa: E402


def run(stage: str, cmd: list[str]) -> dict:
    print(f"\n=== {stage} ===", flush=True)
    print(" ".join(cmd), flush=True)
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=False)
    dt = time.time() - t0
    if result.returncode != 0:
        print(f"!! {stage} failed (exit {result.returncode})", flush=True)
        sys.exit(result.returncode)
    return {"stage": stage, "wall_sec": round(dt, 2)}


def dir_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    out = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True)
    return float(out.stdout.split()[0]) / 1024.0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video_id")
    p.add_argument("--end", type=int, default=None,
                   help="end second of snippet; if omitted, processes the whole video")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--suffix", default="")
    p.add_argument("--target-sec", type=float, default=180.0)
    p.add_argument("--max-sec", type=float, default=300.0)
    p.add_argument("--scene-threshold", type=float, default=12.0)
    p.add_argument("--keep-video", action="store_true",
                   help="don't delete video.mp4 after frame extraction (default: delete)")
    p.add_argument("--skip-download", action="store_true")
    p.add_argument("--skip-transcribe", action="store_true")
    p.add_argument("--skip-scenes", action="store_true")
    args = p.parse_args()

    vid: Video | None
    try:
        vid = by_id(args.video_id)
    except KeyError:
        vid = None
        print(f"[info] video_id {args.video_id} not registered in videos.py — running without code splicing", flush=True)

    work = PROJECT / "work" / args.video_id
    work.mkdir(parents=True, exist_ok=True)

    timings: list[dict] = []
    base = ["uv", "run", "python"]

    if not args.skip_download:
        cmd = base + ["scripts/download.py", args.video_id]
        if args.end is not None:
            cmd += ["--end", str(args.end)]
            if args.start:
                cmd += ["--start", str(args.start)]
        timings.append(run("download", cmd))

    if not args.skip_transcribe:
        timings.append(run("transcribe", base + [
            "scripts/transcribe.py", str(work / "audio.wav")
        ]))

    if not args.skip_scenes:
        timings.append(run("scenes", base + [
            "scripts/scenes.py", str(work / "video.mp4"),
            "--threshold", str(args.scene_threshold),
        ]))

    # Re-chunking invalidates rewrite cache (chunk boundaries differ between runs).
    if (work / "rewrites").exists():
        shutil.rmtree(work / "rewrites")

    chunk_cmd = base + [
        "scripts/chunk.py", str(work),
        "--target-sec", str(args.target_sec),
        "--max-sec", str(args.max_sec),
    ]
    if vid and vid.code_sources:
        chunk_cmd += ["--code-sources"] + [str(p) for p in vid.absolute_sources()]
    if args.end is not None and vid is not None:
        # snippet of a longer video — pass full duration so cell positional matching is honest
        chunk_cmd += ["--full-audio-sec", str(vid.duration_sec)]
    timings.append(run("chunk", chunk_cmd))

    timings.append(run("rewrite", base + ["scripts/rewrite.py", str(work)]))
    render_cmd = base + ["scripts/render.py", str(work)]
    if args.suffix:
        render_cmd += ["--suffix", args.suffix]
    timings.append(run("render", render_cmd))

    # Optional: drop video.mp4 to save disk after frames are out
    video_files = list(work.glob("video.*"))
    pre_delete_video_mb = sum(f.stat().st_size for f in video_files) / 1024 / 1024
    if not args.keep_video:
        for f in video_files:
            f.unlink()
        print(f"\n[cleanup] deleted {len(video_files)} video file(s) ({pre_delete_video_mb:.1f} MB)", flush=True)

    sizes = {
        "audio_mb": (work / "audio.wav").stat().st_size / 1024 / 1024 if (work / "audio.wav").exists() else 0,
        "video_mb_before_cleanup": round(pre_delete_video_mb, 2),
        "frames_mb": dir_size_mb(work / "frames"),
        "rewrites_mb": dir_size_mb(work / "rewrites"),
        "guide_assets_mb": dir_size_mb(PROJECT / "guides" / "assets"),
    }
    total_pipeline_sec = sum(t["wall_sec"] for t in timings)

    summary = {
        "video_id": args.video_id,
        "title": vid.title if vid else None,
        "section": [args.start or 0, args.end] if args.end is not None else None,
        "duration_sec_processed": (args.end - (args.start or 0)) if args.end else (vid.duration_sec if vid else None),
        "stages": timings,
        "total_pipeline_sec": round(total_pipeline_sec, 2),
        "disk_mb": {k: round(v, 2) if isinstance(v, (int, float)) else v for k, v in sizes.items()},
    }
    (work / "pipeline.json").write_text(json.dumps(summary, indent=2))
    print("\n" + json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
