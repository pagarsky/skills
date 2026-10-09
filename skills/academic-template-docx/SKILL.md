---
name: academic-template-docx
description: Generate theses, conference papers, and similar academic documents that match an existing template or formatting instructions. Use when the user provides a template in .doc/.docx/.pdf/text form, asks to reproduce formatting, convert markdown to styled DOCX, transfer styles, fit page limits, or preserve academic layout details such as columns, headings, formulas, figures, footers, and author blocks.
---

# Academic Template DOCX

## When to use

Use this skill when the user wants a thesis, conference abstract, paper, or report to match an existing academic template.

Typical triggers:
- "format this like the template"
- "convert markdown/text to docx"
- "match this conference thesis style"
- "follow instructions embedded in the doc/pdf"
- "reverse-engineer the formatting"
- "make it fit exactly 2 pages"

## Core rule

Always prefer explicit instructions embedded in the template text.

If some formatting cannot be inferred from text alone, recover what you can from the template file itself. If style metadata is lost or incomplete, reconstruct the layout from the written rules and visible evidence.

## Workflow

### 1. Gather the three input types

Collect, when available:
- source content to be formatted
- formatting instructions or template files
- one or more finished examples that show the intended style

If there are multiple instruction artifacts, inspect them in parallel. If the set is large or mixed (`.doc`, `.docx`, `.pdf`, sample papers), use parallel explore subagents or parallel reads to extract constraints quickly.

### 2. Extract formatting constraints

Build a formatting spec before editing anything. Capture:
- paper size and margins
- column count and column gap
- body font, heading font, sizes, and line spacing
- title, author, affiliation, and abstract formatting
- paragraph indent and spacing
- heading numbering rules
- formula placement and numbering
- figure/table placement and caption rules
- citation/reference conventions
- header/footer content and size
- author affiliation markers, including superscripts if used
- page-count constraints

### 3. Choose the best transfer strategy

Use this order:

1. **Best case:** direct `reference.docx` or native template styling is available and preserves the needed layout.
2. **Medium case:** extract recoverable layout/style data from `.docx` or rendered output and reuse it.
3. **Fallback:** convert content to an intermediate `.docx`, then rebuild formatting explicitly with `python-docx` and OOXML edits.

Do not assume a `.doc -> .docx` conversion preserves real styles. Treat legacy `.doc` conversions skeptically.

### 4. Convert content safely

Preferred default:
- generate an intermediate `.docx` from markdown using `pandoc`
- if `pandoc` is not installed, use `uv run --with pypandoc-binary`
- rebuild or refine the output with `python-docx`

For images/figures:
- keep process flow in the figure
- keep interpretation in the paragraph or caption unless the template clearly expects a callout
- insert figures at single-column width unless the template allows two-column figures
- keep captions under the figure

### 5. Fit the target length

If the document must hit a page limit:
- first adjust figures and spacing within the template rules
- then expand or compress body text in scientifically natural ways
- avoid padding with repetition
- rebalance content across sections rather than only changing the conclusion

### 6. Verify the generated DOCX

Verify both visually and structurally:
- inspect generated paragraphs, section settings, footer/header text, and run formatting
- check column settings, spacing, author superscripts, formula numbering, and figure insertion
- confirm that footer/header text, dates, and conference names match the latest requested version
- mention any remaining approximations clearly

## Defaults that worked well

- Read instruction text first.
- Use sample finished documents as secondary evidence.
- For legacy `.doc`, extract text instructions before trusting converted styles.
- Reconstruct exact numeric rules when style transfer is unreliable.
- Keep a validation loop: extract -> spec -> generate -> inspect -> adjust -> regenerate.

## Recommended tool pattern

- Use file reads and parallel exploration first.
- Use `textutil` to extract text from legacy `.doc` files.
- Use `uv` with `pypandoc-binary`, `python-docx`, and `pillow` when needed.
- Use OOXML edits for columns, borders, footer lines, and similar layout details that `python-docx` does not expose directly.

## Deliverables

When done, provide:
- the final styled document
- any generated figure assets
- the source markdown or text changes
- a short note on what was inferred from text vs reconstructed from file inspection

## Additional reference

For commands, fallback tiers, and a reusable extraction checklist, see [reference.md](reference.md)
