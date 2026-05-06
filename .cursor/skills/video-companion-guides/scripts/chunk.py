"""Chunk the transcript into rewrite-sized pieces, aligned to scene boundaries.

A chunk is a contiguous span of sentences:
  - covering one or more whole scenes,
  - up to ~target_sec long,
  - never splitting a sentence.

We also pre-pick which scene-frames belong to each chunk and which notebook
cells (if any) overlap the chunk by index range.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


_FENCE_RE = re.compile(r"^```(\w*)\n(.*?)^```", re.MULTILINE | re.DOTALL)
# .py files this big are split into N pseudo-cells of ~split lines each so the
# positional heuristic can route different parts of a long source file to
# different chunks.
PY_SPLIT_LINES = 60


def _load_ipynb(path: Path) -> list[dict]:
    nb = json.loads(path.read_text())
    out = []
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"]) if isinstance(c["source"], list) else c["source"]
        src = src.strip()
        if not src:
            continue
        out.append({"notebook": path.name, "cell_idx": i, "source": src})
    return out


def _load_md(path: Path) -> list[dict]:
    text = path.read_text()
    out = []
    for i, m in enumerate(_FENCE_RE.finditer(text)):
        lang = m.group(1).strip().lower()
        if lang and lang not in ("python", "py", "ipython", "pycon"):
            continue
        src = m.group(2).rstrip()
        if not src.strip():
            continue
        out.append({"notebook": path.name, "cell_idx": i, "source": src})
    return out


def _load_py(path: Path) -> list[dict]:
    lines = path.read_text().splitlines()
    out = []
    n_chunks = max(1, (len(lines) + PY_SPLIT_LINES - 1) // PY_SPLIT_LINES)
    for i in range(n_chunks):
        block = "\n".join(lines[i * PY_SPLIT_LINES:(i + 1) * PY_SPLIT_LINES]).strip()
        if not block:
            continue
        out.append({"notebook": f"{path.name}#{i+1}", "cell_idx": i, "source": block})
    return out


def load_code_cells(paths: list[Path]) -> list[list[dict]]:
    """Returns one list of cells per source file. The chunker treats each source
    as spanning the full audio independently, so a README is not pushed to the
    end of the lecture just because it was listed after the notebook."""
    sources: list[list[dict]] = []
    for p in paths:
        if p.suffix == ".ipynb":
            cells = _load_ipynb(p)
        elif p.suffix == ".md":
            cells = _load_md(p)
        elif p.suffix == ".py":
            cells = _load_py(p)
        else:
            print(f"WARN: unknown code-source extension: {p}", flush=True)
            continue
        if cells:
            sources.append(cells)
    return sources


def chunk_sentences(sentences: list[dict], scene_starts: list[float],
                    target_sec: float, max_sec: float) -> list[dict]:
    """Greedy: walk sentences in order, start new chunk when:
       (a) we cross a scene boundary AND current chunk >= target_sec * 0.6, or
       (b) current chunk would exceed max_sec.
    """
    if not sentences:
        return []
    chunks = []
    cur = {"start": sentences[0]["start"], "end": sentences[0]["end"], "sentences": [sentences[0]]}
    next_scene_idx = 1  # scene_starts[0] == 0 typically
    for s in sentences[1:]:
        cur_dur = cur["end"] - cur["start"]
        # Did we cross a scene start?
        crossed = (next_scene_idx < len(scene_starts)
                   and s["start"] >= scene_starts[next_scene_idx])
        will_exceed = (s["end"] - cur["start"]) > max_sec
        if (crossed and cur_dur >= target_sec * 0.6) or will_exceed:
            chunks.append(cur)
            cur = {"start": s["start"], "end": s["end"], "sentences": [s]}
            while next_scene_idx < len(scene_starts) and s["start"] >= scene_starts[next_scene_idx]:
                next_scene_idx += 1
        else:
            cur["sentences"].append(s)
            cur["end"] = s["end"]
            while next_scene_idx < len(scene_starts) and s["start"] >= scene_starts[next_scene_idx]:
                next_scene_idx += 1
    chunks.append(cur)
    return chunks


def attach_scenes_and_code(chunks: list[dict], scenes: list[dict],
                           sources: list[list[dict]],
                           total_audio_sec: float) -> list[dict]:
    """Annotate each chunk with overlapping scenes and a heuristic slice of
    canonical-code cells. Each source is assumed to span the full lecture, so
    its cells are mapped independently — a README's 2 blocks land near the
    start of the lecture even if it was listed after a notebook in argv.
    """
    # Assign each scene to exactly one chunk: the one whose [start,end) contains
    # the scene's midpoint. Edge case: a scene's mid past the last chunk falls
    # back to the last chunk.
    scene_owner: dict[int, list[dict]] = {i: [] for i in range(len(chunks))}
    for sc in scenes:
        mid = sc["mid"]
        owner = len(chunks) - 1
        for i, c in enumerate(chunks):
            if c["start"] <= mid < c["end"]:
                owner = i
                break
        scene_owner[owner].append(sc)

    for i, c in enumerate(chunks):
        c["scene_frames"] = scene_owner[i]
        cells_here: list[dict] = []
        if total_audio_sec > 0:
            f0 = c["start"] / total_audio_sec
            f1 = c["end"] / total_audio_sec
            for src_cells in sources:
                n = len(src_cells)
                if n == 0:
                    continue
                # widen the slice by 1 cell on each side so a chunk that sits on
                # a cell boundary still sees the relevant code
                i0 = max(0, int(f0 * n) - 1)
                i1 = min(n, int(f1 * n) + 2)
                cells_here.extend(src_cells[i0:i1])
        c["candidate_cells"] = cells_here
    return chunks


def main():
    p = argparse.ArgumentParser()
    p.add_argument("work_dir")
    p.add_argument("--code-sources", nargs="*", default=[],
                   help=".ipynb / .py / .md files to use as canonical code references")
    p.add_argument("--target-sec", type=float, default=180.0,
                   help="target chunk length")
    p.add_argument("--max-sec", type=float, default=300.0,
                   help="hard cap on chunk length")
    p.add_argument("--full-audio-sec", type=float, default=None,
                   help=("total length of the FULL video in seconds; used to map "
                         "notebook cells to chunks. Defaults to the snippet's own "
                         "duration, which is correct only for full-video runs."))
    args = p.parse_args()

    work = Path(args.work_dir)
    transcript = json.loads((work / "transcript.json").read_text())
    scenes_doc = json.loads((work / "scenes.json").read_text())
    sentences = transcript["sentences"]
    scenes = scenes_doc["scenes"]
    scene_starts = [s["start"] for s in scenes]

    sources = load_code_cells([Path(p) for p in args.code_sources])

    chunks = chunk_sentences(sentences, scene_starts,
                             target_sec=args.target_sec, max_sec=args.max_sec)
    audio_dur = sentences[-1]["end"] if sentences else 0.0
    full_audio = args.full_audio_sec if args.full_audio_sec else audio_dur
    chunks = attach_scenes_and_code(chunks, scenes, sources, full_audio)

    # number them and emit
    for i, c in enumerate(chunks, 1):
        c["index"] = i
        c["text"] = " ".join(s["text"] for s in c["sentences"])
        c["duration"] = round(c["end"] - c["start"], 2)
        c["start"] = round(c["start"], 2)
        c["end"] = round(c["end"], 2)

    n_total_cells = sum(len(s) for s in sources)
    out = {
        "n_chunks": len(chunks),
        "audio_duration_sec": round(audio_dur, 2),
        "target_sec": args.target_sec,
        "max_sec": args.max_sec,
        "n_code_sources": len(sources),
        "n_total_cells": n_total_cells,
        "chunks": chunks,
    }
    (work / "chunks.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print(f"chunks: {len(chunks)}, total audio {audio_dur:.1f}s, "
          f"code sources: {len(sources)} ({n_total_cells} total cells)")
    for c in chunks:
        print(f"  #{c['index']:02d} {c['start']:6.1f}s -> {c['end']:6.1f}s "
              f"({c['duration']:5.1f}s)  scenes={len(c['scene_frames'])} "
              f"cells={len(c['candidate_cells'])}")


if __name__ == "__main__":
    main()
