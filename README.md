# Skills

Reusable Cursor skills and related guidance.

Current contents:
- `skills/academic-template-docx/`: a skill for producing academic theses, conference papers, and similar documents from templates or embedded formatting instructions.
- `skills/video-companion-guides/`: a skill for turning long-form videos (YouTube lectures, conference talks, keynotes, podcasts, interviews) into book-chapter-style markdown companion guides — fully local on Apple Silicon, $0 cloud spend.
- `skills/credentials/`: a macOS-only skill for obtaining secrets (passwords, API tokens, sudo, basic-auth) via osascript prompts + Keychain so they never appear in chat transcripts.
- `skills/ops-dashboard-design/`: a skill for designing monitoring/ops dashboards where every panel answers a named question — opposite-direction metrics separated, thresholds encode good/bad visually, values normalized instead of time windows frozen.
- `skills/eli5-engineer/`: a skill for explaining unfamiliar systems and decisions to a competent engineer without the local context — background-first ordering, follow-the-wire concreteness, single extended analogy, cited claims.
- `skills/writing-pr/`: a skill for writing pull request titles and bodies — concise, diagram- and code-sample-first, no test-run narration, no intermediate-PR trivia.

The skills live under `skills/` so the repo root is installable as a Claude Code plugin; `.cursor/skills` and `.claude/skills` are symlinks to it.

This repository is intended to stay generic and public. Project-specific working files remain local and are ignored by git.
