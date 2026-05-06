"""Stitch per-chunk rewrites into a final companion guide markdown.

Inputs:
    work/<id>/{download.json, transcript.json, scenes.json, chunks.json,
              rewrite.json, rewrites/chunk_*.md}

Output:
    guides/<slug>.md  with:
      - title + a small subtitle line (NOT a blockquote — some viewers don't
        render links inside blockquotes),
      - "← back to course index" anchor at the top,
      - a TOC of H2 sections (skipped if there are < 5),
      - per-chunk markdown with duplicate H2s suffixed " (cont.)",
      - inline scene-keyframes embedded at scene boundaries within each chunk,
      - YouTube-timestamped "watch from m:ss" link at the end of each chunk,
      - footer "About this guide" linking to the source video.

Frame embeds are on by default. Pass `--no-frames` to skip frame extraction
and produce a text-only guide (smaller, but loses the visual context).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from pathlib import Path


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80]


def github_anchor(heading: str) -> str:
    """Approximate GitHub's heading-to-anchor rule:
    lowercase, drop punctuation (keep letters/digits/space/hyphen), spaces -> hyphen."""
    s = heading.strip().lower()
    s = re.sub(r"[^\w\- ]+", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def fmt_mmss(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def dedupe_h2_headings(md: str, seen_counter: Counter) -> str:
    """Suffix duplicate H2 headings with " (cont.)" / " (II)", etc.

    `seen_counter` is updated in place across chunks within a single guide.
    The first occurrence of a heading text is kept verbatim; subsequent ones
    get a roman-style suffix so anchors remain unique.
    """
    def repl(m: re.Match) -> str:
        heading = m.group(1).strip()
        seen_counter[heading] += 1
        n = seen_counter[heading]
        if n == 1:
            return f"## {heading}"
        # n=2 -> " (cont.)", n=3 -> " (cont. II)", n=4 -> " (cont. III)", ...
        if n == 2:
            tag = "cont."
        else:
            tag = f"cont. {to_roman(n - 1)}"
        return f"## {heading} ({tag})"
    return _H2_RE.sub(repl, md)


def to_roman(n: int) -> str:
    table = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for v, sym in table:
        while n >= v:
            out += sym
            n -= v
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("work_dir")
    p.add_argument("--guides-dir", default="guides")
    p.add_argument("--suffix", default="",
                   help="optional slug suffix (e.g. '5min')")
    p.add_argument("--toc-min-sections", type=int, default=5,
                   help="emit a TOC only if the guide has at least this many H2s")
    p.add_argument("--no-frames", action="store_true",
                   help="skip scene-keyframe extraction and image embeds "
                        "(produces a text-only guide; default is to embed)")
    args = p.parse_args()
    args.with_frames = not args.no_frames

    work = Path(args.work_dir)
    download = json.loads((work / "download.json").read_text())
    chunks_doc = json.loads((work / "chunks.json").read_text())
    chunks = chunks_doc["chunks"]

    video_id = download["video_id"]
    title = download["title"]
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"

    slug = slugify(title)
    if args.suffix:
        slug = f"{slug}--{args.suffix}"

    guides_dir = Path(args.guides_dir)
    guides_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = guides_dir / "assets" / slug
    if args.with_frames:
        assets_dir.mkdir(parents=True, exist_ok=True)

    section = download.get("section") or [0, int(download.get("duration_full_sec", 0))]
    duration_full = download.get("duration_full_sec", 0)
    is_full = section[0] == 0 and section[1] == duration_full

    # ----------------- assemble the body (chunks + frames + citations) -----
    body: list[str] = []
    seen_headings: Counter = Counter()
    for c in chunks:
        rewrite_path = work / "rewrites" / f"chunk_{c['index']:02d}.md"
        if not rewrite_path.exists():
            continue
        md = rewrite_path.read_text().strip()
        md = dedupe_h2_headings(md, seen_headings)
        body.append(md)
        body.append("")

        if args.with_frames:
            for sc in c.get("scene_frames", []):
                frame_rel = sc.get("frame_path")
                if not frame_rel:
                    continue
                src = work / frame_rel
                if not src.exists():
                    continue
                dst_name = f"chunk{c['index']:02d}-scene{sc['index']:03d}.png"
                dst = assets_dir / dst_name
                shutil.copy2(src, dst)
                rel = dst.relative_to(guides_dir)
                cap = f"_Frame at {fmt_mmss(sc['mid'])} (scene #{sc['index']}, {sc['duration']:.0f}s)._"
                alt_title = title.replace("|", "│")
                body.append(f"![{alt_title} frame at {fmt_mmss(sc['mid'])}](./{rel.as_posix()})")
                body.append("")
                body.append(cap)
                body.append("")

        cite_t = int(c["start"])
        body.append(f"↪ [watch from {fmt_mmss(c['start'])}]({youtube_url}&t={cite_t}s)")
        body.append("")
        body.append("---")
        body.append("")

    body_md = "\n".join(body)

    # collect H2 headings AFTER dedupe so the TOC matches what's in the doc
    toc_entries: list[tuple[str, str]] = []
    seen_anchors: Counter = Counter()
    for m in _H2_RE.finditer(body_md):
        h = m.group(1).strip()
        a = github_anchor(h)
        seen_anchors[a] += 1
        # GitHub disambiguates duplicate anchors by appending -1, -2, ...; we
        # already deduped headings, so this should usually be n==1, but keep
        # the safety net in case someone hand-edits the markdown.
        anchor = a if seen_anchors[a] == 1 else f"{a}-{seen_anchors[a] - 1}"
        toc_entries.append((h, anchor))

    # ----------------- assemble the head (title + nav + subtitle + TOC) ----
    head: list[str] = []
    head.append("[← back to course index](README.md)")
    head.append("")
    head.append(f"# {title}")
    head.append("")
    # subtitle as plain text (not blockquote) so links render in every viewer
    if is_full:
        coverage = f"**{fmt_mmss(duration_full)}** of source video"
    else:
        coverage = (f"**{fmt_mmss(section[0])}–{fmt_mmss(section[1])}** "
                    f"of {fmt_mmss(duration_full)} total")
    head.append(
        f"_Source: [`youtu.be/{video_id}`]({youtube_url})_  ·  "
        f"_{coverage}_  ·  "
        f"_{len(chunks)} sections from {chunks_doc.get('audio_duration_sec', 0):.0f}s of audio_"
    )
    head.append("")

    if len(toc_entries) >= args.toc_min_sections:
        head.append("## Contents")
        head.append("")
        for h, a in toc_entries:
            head.append(f"- [{h}](#{a})")
        head.append("")
        head.append("---")
        head.append("")

    # ----------------- footer ---------------------------------------------
    footer = [
        "## About this guide",
        "",
        (f"Auto-generated companion to "
         f"[*{title}*]({youtube_url}) by an offline pipeline:"),
        "",
        "- Transcribed with NVIDIA Parakeet-TDT-0.6b-v3 via [parakeet-mlx](https://github.com/senstella/parakeet-mlx).",
        "- Rewritten by Qwen3-30B-A3B-Instruct-2507 (Q4_K_M) running locally via ollama.",
        "- Frame timing detected with PySceneDetect.",
        ("- Code blocks (when emitted) are spliced verbatim from the speaker's "
         "published source files, configured in `videos.py`."),
        "",
        "[← back to course index](README.md)",
        "",
    ]

    out = head + ["---", "", body_md.rstrip(), ""] + footer
    guide_path = guides_dir / f"{slug}.md"
    guide_path.write_text("\n".join(out))
    print(f"wrote {guide_path}  ({sum(v for v in seen_headings.values()) - len(seen_headings)} dup H2(s) renamed)")


if __name__ == "__main__":
    main()
