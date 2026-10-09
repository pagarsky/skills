"""Rewrite each chunk into long-form prose using a local LLM via ollama.

Inputs: work/<id>/chunks.json
Outputs: work/<id>/rewrites/chunk_NN.md  + rewrite.json (timings)

Each chunk gets a system+user prompt with:
  - a per-chunk contract (output style, faithfulness, code-splice rules),
  - the running outline of headings emitted so far (for de-duplication),
  - a small slice of candidate code cells (when configured for this video),
  - the transcript text for that chunk with [t=mm:ss] markers preserved.

The LLM is told: prefer the speaker's terms; never invent identifiers; if you
cite code, splice from the candidate cells verbatim.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import ollama


SYSTEM = """You are an expert editor turning a video transcript into a long-form article (book-chapter style — readable as standalone prose).

Rules — read carefully and follow strictly:
1. The reader has NOT seen the video. Write self-contained prose, not stage directions like "as you can see in the slide".
2. Stay faithful to the speaker's claims. Do NOT invent facts, code, library names, function names, numbers, or quotes.
3. Preserve the speaker's terms of art and idioms. Do not rename concepts.
4. If a code block is needed, copy it VERBATIM from the CANDIDATE_CODE section when a passage clearly matches one; otherwise omit code (do not reconstruct from speech). For non-coding videos CANDIDATE_CODE will be empty — that's fine, just produce prose.
5. Drop verbal fillers ("um", "okay", "so basically"), false starts, and asides that don't carry information. Keep the substantive content dense.
6. Use Markdown with H2 (`## ...`) for the main section heading and H3 for sub-sections. NEVER use H1 (`# ...`) — the page title is reserved.
7. Use inline math with `$...$` and display math with `$$...$$` when the speaker is doing arithmetic or showing equations. Use fenced ```python code blocks for code.
8. Do NOT repeat headings already used in EXISTING_OUTLINE.
9. Drop the bracketed `[t=mm:ss]` anchors entirely from your output — they are reference markers for you, not for the reader.
10. Output ONLY the markdown for THIS chunk. No preamble, no meta-commentary, no "Here is your chunk".
"""


USER_TEMPLATE = """EXISTING_OUTLINE (headings used in earlier chunks; do not reuse them):
{outline}

CANDIDATE_CODE (code excerpts from the speaker's published source files that *might* belong in this chunk; use ONLY if a passage clearly refers to one of these and copy verbatim — including comments and prints. May be "(no candidate cells)" for non-coding videos — in that case, produce prose only):
{code_block}

CHUNK_TIME_RANGE: {time_range}

TRANSCRIPT (the verbatim spoken text for this chunk; the bracketed `[t=...]` markers are reference anchors for you only — they MUST NOT appear in your output):
{transcript}

Now write the markdown for this chunk. Remember: long-form article prose, never copy the raw transcript, drop the `[t=...]` markers, never use `# ` H1 headings."""


def fmt_mmss(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def build_transcript_text(chunk: dict) -> str:
    """Reassemble the chunk transcript with [t=mm:ss] anchors per sentence."""
    lines = []
    for s in chunk["sentences"]:
        ts = fmt_mmss(s["start"])
        lines.append(f"[t={ts}] {s['text']}")
    return "\n".join(lines)


def build_code_block(chunk: dict) -> str:
    cells = chunk.get("candidate_cells") or []
    if not cells:
        return "(no candidate cells)"
    parts = []
    for c in cells:
        parts.append(f"--- {c['notebook']} cell {c['cell_idx']} ---\n{c['source']}")
    return "\n\n".join(parts)


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def extract_headings(md: str) -> list[str]:
    return [m.group(2).strip() for m in HEADING_RE.finditer(md)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("work_dir")
    p.add_argument("--model", default="qwen3:30b-a3b-instruct-2507-q4_K_M")
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--num-ctx", type=int, default=16384,
                   help="ollama context window")
    p.add_argument("--max-tokens", type=int, default=4096)
    args = p.parse_args()

    work = Path(args.work_dir)
    chunks_doc = json.loads((work / "chunks.json").read_text())
    chunks = chunks_doc["chunks"]
    out_dir = work / "rewrites"
    out_dir.mkdir(parents=True, exist_ok=True)

    outline: list[str] = []
    timings = []
    t_overall = time.time()
    for c in chunks:
        out_path = out_dir / f"chunk_{c['index']:02d}.md"
        if out_path.exists() and out_path.stat().st_size > 0:
            print(f"[skip] {out_path} already exists", flush=True)
            outline.extend(extract_headings(out_path.read_text()))
            continue

        transcript_text = build_transcript_text(c)
        user_msg = USER_TEMPLATE.format(
            outline="\n".join(f"- {h}" for h in outline) or "(none yet — this is the first chunk)",
            code_block=build_code_block(c),
            time_range=f"{fmt_mmss(c['start'])} -> {fmt_mmss(c['end'])} (chunk #{c['index']})",
            transcript=transcript_text,
        )

        t0 = time.time()
        md = ""
        attempt = 0
        # The model occasionally returns a near-empty / junk chunk; retry once
        # at slightly higher temperature before giving up.
        while attempt < 2:
            resp = ollama.chat(
                model=args.model,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                options={
                    "temperature": args.temperature + (0.15 * attempt),
                    "num_ctx": args.num_ctx,
                    "num_predict": args.max_tokens,
                },
            )
            md = resp["message"]["content"].strip()
            ok = (len(md) >= 200) and bool(extract_headings(md))
            if ok:
                break
            attempt += 1
            print(f"  [retry] chunk {c['index']} returned {len(md)} chars / "
                  f"{len(extract_headings(md))} headings; retrying", flush=True)
        dt = time.time() - t0
        out_path.write_text(md)

        new_headings = extract_headings(md)
        outline.extend(new_headings)

        usage = {
            "chunk": c["index"],
            "audio_sec": c["duration"],
            "rewrite_sec": round(dt, 2),
            "input_chars": len(user_msg),
            "output_chars": len(md),
            "n_new_headings": len(new_headings),
            "prompt_eval_count": resp.get("prompt_eval_count"),
            "eval_count": resp.get("eval_count"),
        }
        timings.append(usage)
        print(json.dumps(usage), flush=True)

    total = time.time() - t_overall
    summary = {
        "model": args.model,
        "total_rewrite_sec": round(total, 2),
        "n_chunks": len(chunks),
        "per_chunk": timings,
        "final_outline": outline,
    }
    (work / "rewrite.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nDone. {len(chunks)} chunks rewritten in {total:.1f}s.")


if __name__ == "__main__":
    main()
