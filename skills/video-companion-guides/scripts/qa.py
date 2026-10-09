"""Sanity-check the artifacts produced by run_all (or a single pipeline run).

Reports per-video: guide exists, headings count, code blocks, embedded images,
citations, and any chunk file under 200 chars (likely empty/junk).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "scripts"))
from videos import VIDEOS  # noqa: E402


def slugify(s: str) -> str:
    s = s.lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:80]


def main():
    if not VIDEOS:
        print("videos.py has no entries; nothing to QA.")
        print("Tip: for a single ad-hoc video, just inspect guides/<slug>.md and "
              "work/<video_id>/rewrites/ directly.")
        return

    print(f"{'video_id':<14} {'lines':>6} {'H2':>3} {'imgs':>5} {'cites':>5} "
          f"{'code':>5} {'small_chunks':>13}  status")
    print("-" * 90)

    n_total = len(VIDEOS)
    n_ok = 0
    issues = []

    for v in VIDEOS:
        slug = slugify(v.title)
        guide = PROJECT / "guides" / f"{slug}.md"
        work = PROJECT / "work" / v.video_id
        rewrites = work / "rewrites"

        if not guide.exists():
            print(f"{v.video_id:<14} {'MISSING':<70}")
            issues.append((v.video_id, "guide missing"))
            continue

        text = guide.read_text()
        n_lines = text.count("\n")
        n_h2 = sum(1 for line in text.splitlines() if line.startswith("## "))
        n_img = sum(1 for line in text.splitlines() if line.startswith("!["))
        n_cite = text.count("watch from")
        n_code = text.count("```python")

        small = 0
        if rewrites.exists():
            for f in rewrites.glob("chunk_*.md"):
                if f.stat().st_size < 200:
                    small += 1
                    issues.append((v.video_id, f"small chunk {f.name} ({f.stat().st_size} B)"))

        status = "OK"
        if n_h2 < 3:
            status = "FEW_HEADINGS"
            issues.append((v.video_id, f"only {n_h2} H2 headings"))
        elif small > 0:
            status = f"SMALL_CHUNKS:{small}"

        if status == "OK":
            n_ok += 1
        print(f"{v.video_id:<14} {n_lines:>6} {n_h2:>3} {n_img:>5} {n_cite:>5} "
              f"{n_code:>5} {small:>13}  {status}")

    print("-" * 90)
    print(f"{n_ok}/{n_total} guides OK")
    if issues:
        print(f"\n{len(issues)} issue(s):")
        for v_id, msg in issues:
            print(f"  {v_id}: {msg}")


if __name__ == "__main__":
    main()
