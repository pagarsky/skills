"""Per-video configuration: video IDs, titles, durations, and (optional)
canonical code sources.

Edit COLLECTION_TITLE / COLLECTION_DESCRIPTION / PLAYLIST_URL to taste, then
add `Video(...)` entries to `VIDEOS`. Scripts that drive the pipeline
(`pipeline.py`, `run_all.py`, `build_index.py`, `qa.py`) all read this.

For a one-off video (a single conference talk, a podcast episode, etc.), the
quickest path is `pipeline.py <video_id>` — that works even with `VIDEOS = []`.
You only need to populate this file if you want a multi-video index, or if
you want to splice canonical code from the speaker's repos.

A minimal entry is just `video_id`, `title`, `duration_sec`. Pass `code_sources`
to splice canonical code from the speaker's repos: any `.ipynb` (each code
cell becomes a candidate), `.py` (split into ~60-line pseudo-cells), or `.md`
(Python fenced blocks). Each source is mapped *independently* across the
audio, so a README's first block lands near the start of the video even if
the file is listed after a notebook.

Most non-lecture videos (talks, interviews, panels) won't have associated
code repos — leave `code_sources=[]` and the rewrite will rely on the
transcript alone.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


PROJECT = Path(__file__).resolve().parent.parent


# ──────────── collection-level metadata (used by build_index.py) ────────────

COLLECTION_TITLE = "Companion guides"
COLLECTION_DESCRIPTION = (
    "Auto-generated long-form companion guides for a set of videos."
)
PLAYLIST_URL = ""  # optional; e.g. "https://www.youtube.com/playlist?list=..."


# ──────────── per-video config ────────────

@dataclass
class Video:
    video_id: str
    title: str
    duration_sec: int
    code_sources: list[str] = field(default_factory=list)

    def absolute_sources(self) -> list[Path]:
        return [PROJECT / s for s in self.code_sources]


# Add entries here. Examples (commented):
#
# VIDEOS: list[Video] = [
#     # A coding lecture WITH canonical-code splicing
#     Video(
#         video_id="VMj-3S1tku0",
#         title="The spelled-out intro to neural networks and backpropagation: building micrograd",
#         duration_sec=8752,  # 2h25m52s
#         code_sources=[
#             "nn-zero-to-hero/lectures/micrograd/micrograd_lecture_first_half_roughly.ipynb",
#             "repos/micrograd/README.md",
#             "repos/micrograd/micrograd/engine.py",
#         ],
#     ),
#     # A conference talk WITHOUT code splicing
#     Video(
#         video_id="bZQun8Y4L2A",
#         title="State of GPT — keynote",
#         duration_sec=2560,  # 0h42m40s
#     ),
# ]

VIDEOS: list[Video] = []


def by_id(video_id: str) -> Video:
    for v in VIDEOS:
        if v.video_id == video_id:
            return v
    raise KeyError(video_id)


def all_total_seconds() -> int:
    return sum(v.duration_sec for v in VIDEOS)


if __name__ == "__main__":
    total = all_total_seconds()
    print(f"{COLLECTION_TITLE!r}")
    print(f"{len(VIDEOS)} video(s), total {total} s = {total/3600:.2f} h")
    for v in VIDEOS:
        h, m = divmod(v.duration_sec // 60, 60)
        n_sources = len(v.code_sources)
        print(f"  {v.video_id}  {h}h{m:02d}m  {n_sources} code source(s)  {v.title[:60]}")
