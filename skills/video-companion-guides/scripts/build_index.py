"""Build guides/README.md — an index linking each per-video guide.

Reads work/<id>/pipeline.json + videos.py to build the table.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "scripts"))
from videos import COLLECTION_DESCRIPTION, COLLECTION_TITLE, VIDEOS, PLAYLIST_URL  # noqa: E402


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80]


def md_table_escape(s: str) -> str:
    return s.replace("|", "\\|")


def fmt_h(s: int) -> str:
    h, m = divmod(s // 60, 60)
    return f"{h}h{m:02d}m"


def fmt_dt(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds/60:.1f} min"
    return f"{seconds/3600:.2f} h"


def main():
    out = []
    out.append(f"# {COLLECTION_TITLE}")
    out.append("")
    out.append(COLLECTION_DESCRIPTION)
    out.append("")
    out.append("Each guide is a heavy rewrite of the audio transcript into long-form prose, "
               "with scene-detected frames embedded inline and YouTube timestamp links at section "
               "boundaries. Where canonical code sources are configured, code blocks are spliced "
               "verbatim from those sources rather than reconstructed from speech.")
    out.append("")
    out.append("## Pipeline summary")
    out.append("")
    out.append("- ASR: NVIDIA Parakeet-TDT-0.6b-v3 via [parakeet-mlx](https://github.com/senstella/parakeet-mlx) (Apple Silicon).")
    out.append("- Rewrite: Qwen3-30B-A3B-Instruct-2507 (Q4_K_M) via ollama, local.")
    out.append("- Frames: PySceneDetect ContentDetector.")
    out.append("")
    if PLAYLIST_URL:
        out.append(f"Source playlist: [{PLAYLIST_URL}]({PLAYLIST_URL})")
        out.append("")
    out.append("## Videos")
    out.append("")
    out.append("| # | Duration | Companion guide | Pipeline wall | Disk used |")
    out.append("|---|----------|-----------------|---------------|-----------|")

    for i, v in enumerate(VIDEOS, 1):
        slug = slugify(v.title)
        guide = PROJECT / "guides" / f"{slug}.md"
        title_cell = md_table_escape(v.title)
        guide_link = f"[{title_cell}]({slug}.md)" if guide.exists() else f"_{title_cell}_ (pending)"
        pipe = PROJECT / "work" / v.video_id / "pipeline.json"
        wall = "—"
        disk = "—"
        if pipe.exists():
            try:
                p = json.loads(pipe.read_text())
                wall = fmt_dt(p.get("total_pipeline_sec", 0))
                d = p.get("disk_mb", {})
                disk_mb = d.get("audio_mb", 0) + d.get("frames_mb", 0)
                disk = f"{disk_mb:.1f} MB"
            except Exception:
                pass
        out.append(f"| {i} | {fmt_h(v.duration_sec)} | {guide_link} | {wall} | {disk} |")

    out.append("")
    out.append("## Source video links")
    out.append("")
    for v in VIDEOS:
        out.append(f"- `{v.video_id}` — [{v.title}](https://www.youtube.com/watch?v={v.video_id})")
    out.append("")

    target = PROJECT / "guides" / "README.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(out))
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
