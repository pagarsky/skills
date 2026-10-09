---
name: video-companion-guides
description: Use this skill to turn any long-form video (YouTube lecture, conference talk, keynote, podcast, interview, panel) into a book-chapter-style markdown companion guide — fully local on Apple Silicon, $0 cloud spend. Pipeline transcribes audio with Parakeet-TDT-0.6b-v3 (MLX), scene-detects frames, optionally splices canonical code from the speaker's published repos (lectures only), and rewrites into long-form prose with Qwen3-30B-A3B-Instruct via ollama. Triggers — "make a companion guide for [video URL]", "transcribe this talk as markdown", "convert a conference recording into a long-form article", "summarise this YouTube lecture as a book chapter", "auto-generate notes for [video / playlist]", "Karpathy-style guide for X".
---

# video-companion-guides

Generate book-chapter-style markdown companion guides for long-form videos — fully local, no cloud spend.

Built and validated on Karpathy's *Neural Networks: Zero to Hero* (a 19h21m coding-lecture series), but the pipeline is content-agnostic. Works on:

- **Coding lectures** — transcript + scene frames + spliced code from the speaker's repo. The richest output mode.
- **Conference talks / keynotes** — transcript + scene frames (slide changes). No code splicing needed; leave `code_sources=[]`.
- **Podcasts / interviews** — transcript only (set `--no-frames` if the video has no visual content beyond a static thumbnail).
- **Panels / Q&A** — same as podcasts. Speaker diarisation is NOT done; the rewrite reads each chunk as a single voice.

## Pipeline at a glance

```
yt-dlp ─→ audio.wav  ─→ Parakeet-TDT-0.6b-v3 (MLX) ─→ transcript.json
        ╲                                                         ╲
         video.mp4 ─→ PySceneDetect ────→ scenes.json + frames     ╲
                                                                    ╲
                       (optional) speaker's repo: README + .py + .ipynb
                                                                       ↓
                                  per-source positional cell mapping ─→ chunks.json
                                                                       ↓
                                                       Qwen3-30B-A3B-Instruct-2507 (Q4, ollama)
                                                                       ↓
                                                                rewrites/chunk_NN.md
                                                                       ↓
                                                                guides/<slug>.md
```

## Hardware assumptions

- **Apple Silicon (M-series)** — `parakeet-mlx` is MLX-only. On Linux/CUDA, swap for [`nvidia-nemo`](https://github.com/NVIDIA/NeMo)'s Parakeet checkpoint and call out the change to the user.
- **≥ 32 GB unified memory** — Qwen3-30B-A3B in Q4_K_M is ~18 GB resident.
- **`uv`** ([install](https://github.com/astral-sh/uv)) and **`ollama`** ([install](https://ollama.com)) on PATH.

## Workflow when invoked

### 1 — Confirm scope with the user

The skill supports four typical input shapes:

| User says | Mode | Notes |
|---|---|---|
| "Make a guide for [single YouTube URL]" | **single video** | Quickest path. Run `pipeline.py <video_id>`. |
| "Process this YouTube playlist" or pastes a `playlist?list=...` URL | **playlist** | Use `yt-dlp` to fetch the video list, populate `videos.py` with `Video(...)` entries, then `run_all.py`. |
| "Run on [list of videos]" | **custom list** | User edits `videos.py` directly with explicit `Video(...)` entries. |
| "[Lecture series] with code splicing from [repo]" | **lecture mode** | Same as above, but `code_sources=[...]` populated. Clone any referenced repos into `repos/<name>/`. |

If unclear, pick the most likely interpretation and confirm in one sentence — don't ask multiple questions in series.

**For a single ad-hoc video without code splicing, you don't need to touch `videos.py` at all.** `pipeline.py <video_id>` handles unregistered IDs gracefully; the rewrite still works.

### 2 — Bootstrap the project (idempotent)

If the current directory does NOT already have a working pipeline, set one up:

```bash
uv init --no-readme --bare --python 3.11
mkdir -p work guides docs scripts
```

Copy this skill's `scripts/` into the project's `scripts/`, and `templates/pyproject.toml` into the project root (merging into existing `pyproject.toml` if one exists). Then:

```bash
uv add yt-dlp parakeet-mlx scenedetect static-ffmpeg \
       opencv-python-headless pillow ollama tqdm
```

Pull the rewrite model (only once per machine):

```bash
ollama pull qwen3:30b-a3b-instruct-2507-q4_K_M
```

For lecture-mode runs, also clone the speaker's repos into `repos/`:

```bash
mkdir -p repos
git clone --depth 1 https://github.com/<speaker>/<repo>.git repos/<repo>
```

### 3 — Configure `scripts/videos.py` (only for batch or lecture mode)

For ad-hoc single-video runs, skip this step entirely.

For multi-video / lecture runs, edit:

- `COLLECTION_TITLE`, `COLLECTION_DESCRIPTION`, `PLAYLIST_URL` — used by `build_index.py`.
- `VIDEOS = [...]` — one `Video(video_id=..., title=..., duration_sec=..., code_sources=[...])` per video.

To get `duration_sec` for a single video:

```bash
uv run python -c "from static_ffmpeg import add_paths; add_paths(); import yt_dlp; \
  print(yt_dlp.YoutubeDL({'quiet': True}).extract_info('https://youtu.be/<id>', download=False)['duration'])"
```

For a whole playlist (bulk):

```bash
uv run python -c "
from static_ffmpeg import add_paths; add_paths()
import yt_dlp
opts = {'extract_flat': True, 'quiet': True}
with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info('https://www.youtube.com/playlist?list=...', download=False)
for e in info['entries']:
    print(f\"{e['id']}\\t{e.get('duration')}\\t{e.get('title','')}\")"
```

### 4 — Run

Single video, quick test (~5 min wall):

```bash
uv run python scripts/pipeline.py <video_id> --end 300 --suffix 5min
```

Single video, full:

```bash
uv run python scripts/pipeline.py <video_id>
```

Talk-only / no slides — fewer frames:

```bash
uv run python scripts/pipeline.py <video_id> --scene-threshold 50
```

(For audio-only podcast-style content, post-render with `--no-frames` to skip embeds entirely.)

Whole `videos.py` list:

```bash
uv run python scripts/run_all.py
```

### 5 — Index, QA, report

```bash
uv run python scripts/build_index.py   # generate guides/README.md (multi-video runs only)
uv run python scripts/qa.py            # sanity-check all guides
```

For a single ad-hoc video there's no need for the index — just open `guides/<slug>.md`. `qa.py` prints a hint in that case.

## Pipeline stages (each is a separate script)

`pipeline.py` orchestrates these; you can also run them individually:

1. **`download.py`** — `yt-dlp` whole-video by default (much faster than section-fetch). `static-ffmpeg` provides ffmpeg+ffprobe in-venv. Snippet mode: `--end <sec>`.
2. **`transcribe.py`** — `mlx-community/parakeet-tdt-0.6b-v3` via `parakeet-mlx`. ~50× real-time on M-series. Outputs `transcript.json` (sentences + words) and `transcript.srt`.
3. **`scenes.py`** — PySceneDetect `ContentDetector`. Default threshold 12 (slide-heavy videos); raise to ~50 for talking-head content where you want fewer frames.
4. **`chunk.py`** — Splits the transcript at scene boundaries, target 180 s / max 300 s per chunk. Maps each code source independently across the audio: a README's blocks span the full video rather than getting clustered at the end if the file was listed late in `code_sources`.
5. **`rewrite.py`** — Per-chunk LLM call with strict prompt: faithful, no invented identifiers, prefer the speaker's own terms, splice candidate code verbatim or omit. Retries once at higher temperature on suspiciously short / heading-less output. Default model: `qwen3:30b-a3b-instruct-2507-q4_K_M` (override with `--model`).
6. **`render.py`** — Stitches per-chunk markdown, dedupes duplicate H2s with " (cont.)" / " (cont. II)" suffixes, generates a TOC if there are ≥ 5 sections, embeds frames inline (default; `--no-frames` opts out), adds YouTube timestamp citations and a back-link to the index.
7. **`pipeline.py`** — Drives all of the above for a single video. Writes `work/<id>/pipeline.json` with per-stage timings.
8. **`run_all.py`** — Runs `pipeline.py` for every entry in `VIDEOS`, writes `docs/batch_run.json`.
9. **`build_index.py`** — Generates `guides/README.md` (the multi-video index).
10. **`qa.py`** — Sanity-checks guides for empty chunks, missing headings, etc.

## Bugs that took time the first time around (don't repeat them)

- **`yt-dlp` needs both `ffmpeg` *and* `ffprobe`.** `imageio-ffmpeg` only ships ffmpeg → `static-ffmpeg` is the right call (bundles both, `static_ffmpeg.add_paths()` exposes them on PATH).
- **Don't pass `extractor_args = player_client=...` to yt-dlp** — breaks format selection on some videos (results in "Requested format is not available").
- **Re-rendering after re-chunking requires wiping `rewrites/`** — chunk boundaries shift, but per-chunk markdown is keyed by index. `pipeline.py` does this automatically; if calling steps individually, do it yourself.
- **Snippet runs need `--full-audio-sec <full_video_length>`** so cell positional matching is honest. `pipeline.py` does this when `--end` is set AND the video is registered in `videos.py`.
- **Section-fetch (`yt-dlp --download-ranges`) is ~30× slower per second** than whole-video. Use it only for quick snippet tests; full runs should pull the whole video.
- **Frames must be assigned to exactly one chunk** (the one containing the scene's midpoint), otherwise long static scenes embed multiple times.

## Disk / time budget (M3 Pro reference numbers)

- **Compute:** ~0.13 s per second of audio (1.7 min of compute per hour of audio).
- **Whole-video download:** ~30 s for any length (bandwidth-bound).
- **Per-video disk (post-cleanup):** ~3.5 MB / minute of audio. Delete `video.mp4` after `scenes` runs (the pipeline does this by default; pass `--keep-video` to retain).
- **One-off:** ~22 GB on disk for models + deps (Qwen3 ~18 GB, Parakeet ~1.2 GB, deps ~3 GB).

## Quality polish items (for guides that look rough)

These were observed on the validation run and aren't auto-fixed:

1. **Some lectures emit zero fenced ```python blocks** even though candidate code was provided. The model prefers inline `` `code` `` notation. If the user complains, tighten the rewrite prompt with an explicit "emit ≥ 1 fenced block when CANDIDATE_CODE is non-empty" rule.
2. **Heading repetition** — already auto-suffixed " (cont.)" by `render.py`, but the underlying duplicate sections come from the LLM re-introducing topics. A "running outline summary" instead of a flat heading list in the rewrite prompt would help.
3. **Long static scenes** yield only one frame each — for talk-heavy videos (no slide changes) this can be visually monotonous. Workarounds: raise `--scene-threshold` so fewer scenes are detected, or pass `--no-frames` to skip embeds entirely.

## Files in this skill

- `SKILL.md` — this file.
- `README.md` — short human-readable overview for browsers of the skills repo.
- `scripts/*.py` — the full pipeline. Copy verbatim into the target project's `scripts/`.
- `templates/pyproject.toml` — base deps; `uv sync` after copying.
- `templates/.gitignore` — sensible ignores for projects using this skill (`.venv/`, `work/`, `repos/`, etc.).

## Output shape

```
<project>/
├── pyproject.toml
├── scripts/                    (copied from this skill)
├── work/<video_id>/            (intermediate artefacts; gitignored)
│   ├── audio.wav
│   ├── transcript.{json,srt}
│   ├── scenes.json
│   ├── frames/scene_*.png
│   ├── chunks.json
│   ├── rewrites/chunk_NN.md
│   └── pipeline.json           (per-stage timings)
├── repos/                      (cloned canonical-code repos for lecture mode; gitignored)
└── guides/
    ├── README.md               (index — only relevant for multi-video runs)
    ├── <slug>.md               (per-video guide)
    └── assets/<slug>/*.png     (scene keyframes used by the guide)
```

## Don't

- Don't run the rewrite step against stale chunks — `pipeline.py` handles cache invalidation, but if you call `rewrite.py` directly without re-chunking first, you'll mix old rewrites with new boundaries.
- Don't redistribute the source audio or video. The pipeline doesn't, by design — only excerpts (a transcript and scene-keyframes) end up in the output guide.
- For talks / podcasts where the speaker hasn't published the material under a permissive license, prefer `--no-frames` (transcript-only) and add an explicit attribution line.
