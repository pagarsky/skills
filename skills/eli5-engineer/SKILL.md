---
name: eli5-engineer
description: Explain an unfamiliar system, concept, or decision to a competent engineer who lacks the local context ("ELI5 but for an engineer"). Use when the user asks to explain something they're not familiar with, says ELI5, asks "what did X mean by this comment", or needs background before making a decision they don't fully understand yet.
---

# ELI5 for an engineer

The audience is a strong engineer with zero local context — not a beginner. Never simplify by dumbing down; simplify by ordering: background before conclusions. Keep every technical term, hostname, port, and failure mode — precision is respect.

## Structure

1. **Lead with the one missing concept.** Find the single piece of background that makes everything else obvious and teach it first, in 2–4 sentences. ("Consul is a client-server system, and we run both halves.") If you can't name that one concept, you don't understand the topic well enough yet — go investigate before explaining.
2. **Follow the wire.** Trace the actual end-to-end path of the thing being explained — who calls whom, what process answers, where it physically runs. Don't describe architecture in the abstract; narrate one concrete request through it ("when the agent doesn't answer, we do a DNS query — but who answers *that*?").
3. **Name the absurdity.** If the current design contains an accidental redundancy or a historical wart, say so plainly — that unstated oddity is usually the exact thing the reader senses but can't articulate.
4. **Now explain the actual question** — the proposal, the review comment, the decision. If steps 1–3 did their job, this part is only a few sentences.
5. **Honest trade-offs**, each with its mitigation. Never present a one-sided case; "strictly nicer" claims must survive you actively looking for the downside.
6. **End with "where this belongs"** — scope, sequencing, what happens next — not a recap.

## Analogy rules

- At most ONE analogy, chosen so it can be extended through the whole explanation (librarian → phone line to the central library → mailing a postcard to the same librarian). A pile of one-off metaphors is worse than none.
- The analogy carries the *relationships*; it never carries the facts. Every factual claim also appears in literal terms right next to it.

## Grounding rules

- Every load-bearing claim gets a verifiable artifact inline: a file path, a config line, a metric, a command output. If you can't cite it, verify it first or label it explicitly as an assumption.
- Prefer numbers to adjectives ("~60/day, 0.04% of lookups" — not "rarely").
- If the explanation claims "nobody does X", show the search that proves it.

## Register

- Headers that say things ("What our DNS fallback actually is"), not categories ("Background", "Details").
- Prose for the narrative; bullets only for genuine enumerations (trade-offs, options).
- Light humor is fine where the *system* is funny; never at the reader's expense.
