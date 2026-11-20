---
name: fable-brief
description: Prepare a task brief for a Claude Fable worker and flush ambiguity before it starts — settle decisions with the user, write one brief file, lint it against Fable anti-patterns, then dry-run it on Fable at low effort until it has no blocking questions. Use when the user wants to hand a task to Fable, prep work for a worker or background session, or says "brief fable" / "prep this for fable".
---

You are preparing work for a Fable worker that starts cold: it sees the brief and the repo, nothing from this conversation. The output is one brief file. How the worker gets launched is not your job.

## 1. Settle decisions

Explore the code first; ask the user only what the code cannot answer. One question at a time, each with your recommended answer. You are done when every section of [the template](references/brief-template.md) has a real answer:

- **goal + done-criteria** — the observable end state and the exact commands that prove it.
- **stance** — *owner* or *minimal change*. Always ask; never default. Owner makes Fable consolidate and fix nearby things (much bigger diffs, unrequested tests/docs, sometimes behaviour changes). Minimal keeps the diff tight. A "no drive-by refactors" rule does not cancel owner — pick one.
- **approvals** — name the specific actions that need a yes (e.g. push, open PR, prod deploy, Jira/Slack writes, deleting files) and the routine ones that don't. Broad wording ("anything external") makes it hold back half its legitimate work.
- **blockers vs obstacles** — what it must stop and report on (guardrails, files not to touch) vs push through (errors, flaky tests, empty results).
- **effort** — `high` by default; `xhigh` only for long unattended work where it's known to help; `low`/`medium` for well-specified mechanical tasks.
- **delegation** — whether subagents are wanted, and on which model.
- **out of scope** — things it will be tempted to do and shouldn't.

## 2. Write the brief

Fill [references/brief-template.md](references/brief-template.md) and save it as a file. Inline everything the worker needs: file paths, commands, links, the decisions above with their reasons. Nothing like "as discussed" or "the approach above".

## 3. Lint

Fix any of these before the dry run:

- "think less", "answer directly without deliberating" → delete; lower effort instead.
- token budgets shown to the worker → delete; they raise cost without helping.
- "show / write out your reasoning" → delete; it can trigger a refusal.
- unscoped `never` / `always` → give it a scope and a reason, or turn it into an approval rule. Fable treats "never" as absolute.
- standing "always delegate X" → keep only if this task needs it.
- lines telling it not to re-examine its own earlier work → delete; they stop Fable catching its own mistakes. Settled user decisions stay.
- hard style caps (words per sentence, etc.) → delete; prose turns choppy.
- owner stance plus "keep the diff minimal" → contradiction, pick one.
- if the worker will load project memory or instruction files, say which notes apply to this task; the rest is background.

## 4. Dry-run on Fable

Spawn a read-only Fable agent at **low** effort (Agent tool: `model: fable`, `effort: low`, an Explore/read-only type) with:

> Read `<brief path>` and the code it points to. Do not do the task and do not edit anything. List every question, ambiguity, missing permission or contradiction you'd hit doing this work. Mark each **blocking** (you'd have to guess or stop) or **minor**. If there are none, say so.

Answer what the code answers by editing the brief; take the decisions to the user, one at a time. Rerun until a run has no blocking questions.

## 5. Hand off

Reply with the brief path, the effort level, and any minor questions you chose to leave open. Then stop: whoever launches the worker takes it from there.
