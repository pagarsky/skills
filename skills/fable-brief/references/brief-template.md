# <task title>

## Goal

<One or two sentences: the end state, in terms someone could check.>

## Context

<What exists today, with file paths and links. Why this task is being done. Prior decisions and their reasons. Only what the worker needs to act on.>

## Done when

- <observable outcome>
- verify with: `<exact command(s)>`

## Stance

<!-- keep exactly one -->
You are the owner and long-term maintainer of this codebase, and its design is up to you.
<!-- or -->
Keep the change minimal: touch only what the goal needs, and list anything else worth fixing in your report instead of fixing it.

## Approvals

Ask before:
- <specific action, e.g. pushing a branch, opening a PR, deploying, writing to Jira/Slack, deleting files>

No approval needed for:
- <routine steps, e.g. reading anything, running tests/linters, editing files in <dir>, creating local branches>

## Out of scope

- <thing it will be tempted to do> — <why not>

## Finishing work

Do not stop while you still owe work this brief asks for. When you hit an ordinary obstacle (an error, a timeout, a failing test, an empty result), diagnose it and work through it. Leave deliberate blockers alone (<list, e.g. a guardrail, a file marked do-not-touch>), finish everything that doesn't depend on them, and report them. If an action needs approval and nobody answers, do the rest and list it as pending.

## Delegation

<"Work solo." | "Subagents are fine for <kind of work>; use <model>.">

## Report

Write the final report for an intelligent but low-context reader who has not seen your tool calls or files. Put the outcome and anything they must act on in the first few sentences. Use plain words, no invented terms or abbreviations, short active sentences. Use bullets only for separate items. Include: what changed (paths, branch/PR), how you verified it, and what you left open. List every change nobody asked for, and any change to existing behaviour.
