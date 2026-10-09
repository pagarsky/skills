---
name: writing-glanceable
description: Use when writing or editing prose another person will skim — a ticket, a status update, a design doc, a report, a summary, a handoff note. Not for code or code comments.
---

write for someone who reads about a quarter of the words, in order, and stops as soon as they have what they need.

**cap it.** ~300 visible words for a ticket or a report. past that the reader bails. anything an implementer might want but a skimmer won't — raw tables, queries, full evidence, repro steps — goes in a collapsed block or an appendix at the end, never in the main flow.

**front-load every line.** people read the first few words of a bullet and skip the rest. put the subject there, not the setup.

**lead with the number when there is one.** "1,284 failed runs against a 40 baseline" beats "failures were much higher than usual".

but when the claim is a comparison or something qualitative, don't force a number, and never invent one to satisfy the pattern:

- bad: `0 change in the control job` — false, it had dropped by a quarter
- good: `control job runs fell, 8,900 to 6,400`

one fake number in a doc full of real ones gets someone to check, find the lie, and stop trusting the rest.

**one idea per sentence.** short words. if a sentence needs a comma to survive, split it.

**no literary phrasing.** "the change threads the needle between safety and velocity" is not how people talk. "the change is slower, but it cannot lose data" is. a metaphor can decorate something already said plainly — it can't do the explaining.

**bullets over paragraphs**, but a bullet is one sentence, not a paragraph wearing a dash.

**write for a cold reader.** no "as discussed", no references to an earlier session, no notes on how the work got done. they weren't there and don't care.

**link every claim that has a source.** if it can't be linked, say where it came from or cut it.

**cut the recap.** don't restate the request, don't summarise what you just said, don't announce what you're about to do next.
