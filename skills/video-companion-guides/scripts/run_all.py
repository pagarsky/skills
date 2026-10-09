"""Run the full pipeline across the videos config, sequentially.

Per-video failures are logged but don't abort the run — we continue and report
at the end.

Usage:
    uv run python scripts/run_all.py                     # all videos in videos.py
    uv run python scripts/run_all.py --skip <video_id>   # everything except this
    uv run python scripts/run_all.py --only <video_id>   # just one
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "scripts"))
from videos import VIDEOS  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--skip", action="append", default=[],
                   help="video_id(s) to skip; can be repeated")
    p.add_argument("--only", action="append", default=[],
                   help="video_id(s) to include exclusively; can be repeated")
    p.add_argument("--keep-video", action="store_true",
                   help="keep video.mp4 files (default: delete after frame extraction)")
    args = p.parse_args()

    queue = []
    for v in VIDEOS:
        if args.only and v.video_id not in args.only:
            continue
        if v.video_id in args.skip:
            continue
        queue.append(v)

    print(f"\nRunning {len(queue)} video(s):", flush=True)
    for v in queue:
        h, m = divmod(v.duration_sec // 60, 60)
        print(f"  - {v.video_id} ({h}h{m:02d}m)  {v.title[:60]}", flush=True)

    results = []
    overall_t0 = time.time()
    for i, v in enumerate(queue, 1):
        print(f"\n\n{'='*70}\n[{i}/{len(queue)}] {v.video_id} — {v.title}\n{'='*70}", flush=True)
        t0 = time.time()
        cmd = ["uv", "run", "python", "scripts/pipeline.py", v.video_id]
        if args.keep_video:
            cmd.append("--keep-video")
        rc = subprocess.run(cmd).returncode
        dt = time.time() - t0

        pipe = PROJECT / "work" / v.video_id / "pipeline.json"
        if pipe.exists():
            stats = json.loads(pipe.read_text())
        else:
            stats = {"total_pipeline_sec": dt}

        results.append({
            "video_id": v.video_id,
            "title": v.title,
            "duration_sec": v.duration_sec,
            "wall_sec": round(dt, 2),
            "exit_code": rc,
            "ok": rc == 0,
            "stages": stats.get("stages", []),
            "disk_mb": stats.get("disk_mb", {}),
        })

    overall_dt = time.time() - overall_t0
    summary = {
        "n_videos": len(queue),
        "n_ok": sum(1 for r in results if r["ok"]),
        "overall_wall_sec": round(overall_dt, 2),
        "overall_wall_h": round(overall_dt / 3600, 2),
        "results": results,
    }
    out = PROJECT / "docs" / "batch_run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    print(f"\n\nSaved {out}\n")
    print(json.dumps({
        "n_ok": summary["n_ok"],
        "n_videos": summary["n_videos"],
        "overall_wall_h": summary["overall_wall_h"],
    }, indent=2))


if __name__ == "__main__":
    main()
