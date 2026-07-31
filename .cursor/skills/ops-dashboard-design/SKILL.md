---
name: ops-dashboard-design
description: Design or review monitoring/ops dashboards (Grafana, Datadog, custom) so every panel answers a named question with visible good/bad semantics. Use when creating dashboards, choosing panels/thresholds for metrics, or when a dashboard shows "random numbers" nobody can act on. Complements mark/palette-level dataviz guidance — this skill is about semantics.
---

# Ops dashboard design

A dashboard is a set of answers, not a set of charts. A number without a target is not informative: "40 fallbacks" means nothing until the panel says whether 40 is good, bad, or someone's to-do list.

## Procedure

1. **Write the questions first.** Each panel answers exactly one named question ("Is the new mechanism healthy?", "Which services haven't migrated?", "Is the system alive at all?"). If you can't phrase the question, cut the panel.
2. **Split metrics with opposite desired directions.** Never blend "expected to decay" (progress/adoption) with "should stay near zero" (health) into one series or panel — their good and bad point opposite ways, so any shared color or threshold lies about one of them.
3. **Encode good/bad visually, not in the reader's head.** Stat tiles color by threshold; time charts get a filled threshold zone so "bad" is a visible region. Reserve red strictly for "act now" — a decaying legacy metric gets no red at any value.
4. **Normalize the value to fit fixed thresholds; never freeze the panel's time window to fit them.** Thresholds calibrated per-day + a range-following value = show avg/day over the selected range. Pinning a panel to "last 24h" keeps thresholds honest but silently breaks zoom — the wrong trade.
5. **Match form to the question.**
   - Discrete events at regular intervals → bars (per day/hour), not lines.
   - Headline current state → stat tile with sparkline.
   - "Who's left / who's the biggest offender" → sorted horizontal bar gauge or table, NOT a stacked time series with a dozen colors — the question is *who*, not *when*.
   - Continuous rates/latencies → lines.
6. **Default range = the story's cadence.** A multi-week migration gets 14–30d; an incident dashboard gets hours. Don't default to a range where the interesting change is a few pixels tall.
7. **Titles state the question or the expectation** ("Legacy DNS — should reach 0"); the description is one sentence: what this means + when to act. No prose paragraphs.
8. **Distinguish "No data" from zero.** Set an explicit no-value display where absence means zero; but when a series has never existed, decide whether "No data" is a truthful message or a bug in the reader's eyes.
9. **Chart what the instrumentation cannot say.** If failures emit no metric (the process dies before incrementing), silence looks like health — add a volume/liveness panel where a collapse is the alarm, and say so in its description.

## Review checklist

For each panel: What question does it answer? Can a stranger tell good from bad in 3 seconds without context? Does zooming the dashboard range keep it truthful? Is red only where action is required? Would this panel change what anyone does — and if not, why is it here?
