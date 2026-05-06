# video-companion-guides

A Claude Code skill that turns any long-form video — YouTube lecture, conference talk, keynote, podcast, interview, panel — into a book-chapter-style markdown companion guide, fully local on Apple Silicon, $0 cloud spend.

## What it does

Given a single video URL, a YouTube playlist, or a custom list of videos, it:

1. Downloads audio + a low-bitrate video stream (`yt-dlp` + `static-ffmpeg`, both `uv`-isolated).
2. Transcribes with NVIDIA Parakeet-TDT-0.6b-v3 via [`parakeet-mlx`](https://github.com/senstella/parakeet-mlx) — ~50× real-time on M-series.
3. Scene-detects with PySceneDetect and pulls one keyframe per scene (mostly useful when the source has slides; talk-only videos can pass `--no-frames`).
4. Optionally splices canonical code from the speaker's published repos (`.ipynb` / `.py` / `.md`) so identifiers and code blocks aren't reconstructed from speech. Most non-lecture videos won't use this.
5. Chunks the transcript at scene boundaries and rewrites each chunk into long-form prose with `qwen3:30b-a3b-instruct-2507-q4_K_M` via ollama.
6. Stitches into `guides/<slug>.md` per video with a TOC, frame embeds, deduped headings, and YouTube timestamp citations.

## Validated on

Karpathy's *Neural Networks: Zero to Hero* (19 h 21 m of coding lectures → 10 guides in 3.07 h on an Apple M3 Pro, 36 GB). The pipeline is content-agnostic: conference talks, keynotes, and podcasts work too — code-source splicing is opt-in via `videos.py` and stays empty for non-coding content.

## Installing

Drop this folder into your skills collection and Claude Code will pick it up:

```bash
cp -r video-companion-guides ~/.claude/skills/
# or commit it into your skills repo:
git -C ~/code/skills add video-companion-guides
git -C ~/code/skills commit -m "add video-companion-guides"
```

Then invoke from Claude Code with anything like:

> Make a companion guide for `https://www.youtube.com/watch?v=...`.

> Transcribe and rewrite this conference talk into a long-form article.

> Convert this YouTube playlist into companion notes; splice code from `karpathy/micrograd`.

## Hardware

- Apple Silicon M-series (the MLX path is M-series-specific; on Linux/CUDA, swap `parakeet-mlx` for [`nvidia-nemo`](https://github.com/NVIDIA/NeMo)'s Parakeet checkpoint).
- ≥ 32 GB unified memory (Qwen3-30B-A3B Q4_K_M is ~18 GB resident).
- ~22 GB free disk for models + deps; ~3.5 MB per minute of audio for output.

## Layout

- [`SKILL.md`](SKILL.md) — the skill instructions Claude follows when invoked.
- [`scripts/`](scripts/) — the pipeline (download → transcribe → scenes → chunk → rewrite → render → index → QA).
- [`templates/`](templates/) — `pyproject.toml` and `.gitignore` to drop into a new project.
