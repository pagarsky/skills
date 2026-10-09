---
name: tldr
description: Summarize arbitrary context into terse one-sentence bullets
argument-hint: [text, file, URL, PR, or topic]
---

Summarize the provided material, referenced artifact, or current conversation context as a terse
TLDR.

Use this when the user asks for `/tldr`, a TLDR, a short team-share summary, or a concise
explanation of arbitrary work, docs, PRs, skills, plans, notes, or decisions.

## Input

Use `$ARGUMENTS` first. If `$ARGUMENTS` is empty, summarize the most recent relevant conversation
context. Ask a short follow-up only when there is no usable source.

## Style

- Output only a bullet list unless the user asks for a different format.
- Use one sentence per bullet.
- Keep each bullet short and direct.
- Prefer one bullet per named item, such as each skill, command, PR, doc, ticket, service, or
  component.
- Start bullets with the item name in backticks when there is a clear name.
- Avoid intros, outros, caveats, headings, nested bullets, and implementation detail.
- Use plain language a teammate can paste into Slack.

## Defaults

- For a list of skills or commands: one bullet per skill or command explaining what it does.
- For a PR or work batch: 2-4 bullets summarizing the user-visible outcomes.
- For a single concept: 1-3 bullets explaining the idea and why it matters.
- For messy notes: group by outcome, not by chronology.

## Example

Input: "Summarize the release-notes and standup-digest PR."

Output:

- `release-notes`: Turns merged PRs since the last tag into a draft changelog grouped by component.
- `standup-digest`: Drafts a short standup update from yesterday's commits, reviews, and tickets.
