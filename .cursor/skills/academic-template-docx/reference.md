# Reference

## Extraction checklist

Before generating a styled academic document, extract these fields:

- source content path
- template path(s)
- sample finished document path(s)
- page size
- margins
- column count
- column gap
- body font and size
- heading font and size
- title size and spacing
- author line size and spacing
- affiliation size and spacing
- abstract and keyword formatting
- paragraph indent
- heading alignment and spacing
- formula alignment and numbering
- figure width rules
- caption placement and size
- bibliography style clues
- footer/header text
- page-count target

## Practical fallback tiers

### Tier 1: Native style reuse

Use when the user provides a clean `.docx` template with usable styles.

Approach:
- inspect section/page settings
- inspect paragraph styles
- use `pandoc --reference-doc=...` if it preserves the needed structure

### Tier 2: Partial style recovery

Use when some styles survive but not all.

Approach:
- inspect generated `.docx` paragraphs and sections with `python-docx`
- inspect OOXML for columns, sections, borders, footers, and math blocks
- reuse what is real; reconstruct the rest from text instructions

### Tier 3: Full reconstruction

Use when the template is legacy `.doc`, heavily flattened, or otherwise unreliable.

Approach:
- read the text instructions from the template
- use sample output as visual evidence
- generate an intermediate `.docx`
- rebuild layout explicitly with `python-docx`
- patch OOXML for unsupported details

## Useful commands

### Extract text from legacy `.doc`

```bash
textutil -convert txt -stdout "template.doc"
```

### Convert markdown to intermediate DOCX with `uv`

```bash
uv run --no-project --with pypandoc-binary python -c "
import pypandoc
pypandoc.convert_file(
    'input.md',
    'docx',
    format='markdown+tex_math_single_backslash',
    outputfile='intermediate.docx',
    extra_args=['--standalone'],
)
"
```

### Inspect a DOCX with `python-docx`

```bash
uv run --no-project --with python-docx python -c "
from docx import Document
doc = Document('file.docx')
print(len(doc.sections))
for i, p in enumerate(doc.paragraphs[:20]):
    print(i, repr(p.text[:120]), p.style.name if p.style else None)
"
```

### Generate simple figures with `uv`

```bash
uv run --no-project --with pillow python scripts_or_inline_figure_generator.py
```

## Multi-artifact extraction strategy

If the template exists in several forms:

1. Read the instruction-bearing text source first.
2. Read one or more finished examples.
3. Compare against the template file itself for missing details.
4. If the artifact set is large, use parallel explore subagents or parallel reads.

Use subagents especially when:
- there are multiple PDFs plus a template file
- the instructions are split across examples and appendices
- you need one pass for textual rules and another for visual cues

## Common details that are easy to miss

- author affiliation markers are superscript
- title/author spacing is explicitly specified
- headings may be centered even if body text is justified
- footer text and dates may need manual updates
- figure captions belong below the figure
- interpretation text should often stay outside the figure
- formula numbering may need to be added explicitly
- page-fit work is iterative, not one-shot

## Verification loop

After generation:

1. inspect the author/title block
2. inspect heading alignment and spacing
3. inspect footer/header text, line, and font size
4. inspect section columns and margins
5. inspect formula numbering
6. inspect figure embed count and caption placement
7. adjust and regenerate

## What worked best in this project

- extracting `.doc` instructions with `textutil`
- treating `.doc -> .docx` style transfer as unreliable
- reconstructing page geometry from text rules
- using `pypandoc-binary` through `uv` instead of relying on system `pandoc`
- using `python-docx` plus OOXML edits for footers, columns, superscripts, and borders
- moving interpretive figure text into caption/body instead of inside the figure
