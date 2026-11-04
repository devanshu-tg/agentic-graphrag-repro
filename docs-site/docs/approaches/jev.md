# 6 · Jev planner: no Gemini at all

<div class="rv-tldr" style="--rv-accent: var(--c-jev)" markdown>
<div class="t">In one sentence</div>
<div class="b">Same exact queries as the event graph, but the "fill in the form" step picks from lists of valid options with a classifier service (TypeSafe), instead of having Gemini write the form.</div>
<div class="m">An efficiency result, reported separately · 99% · 1.7 seconds per question, zero Gemini calls · <b>not reproduced</b> (needs a TypeSafe key)</div>
</div>

**Analogy:** the spreadsheet filter again, but instead of typing the filter, you choose from drop-down menus filled from the spreadsheet itself, so you can't ask for something that isn't there.

## How it works

<ol class="rv-steps">
<li><b>Build the menus from the graph.</b> Read every sport (47), Games, venue (316) and event name from TigerGraph once.</li>
<li><b>Pick from the menus.</b> Two TypeSafe "System One" requests choose the operation, sport, Games, and then the specific event or venue, each with a confidence score.</li>
<li><b>Read numbers and dates</b> straight from the question with simple text rules.</li>
<li><b>Run the same GSQL and template</b> as the <a href="event-graph.md">event graph</a>.</li>
<li><b>Low confidence?</b> If any choice scores below 0.6, hand the question to <a href="agentic-graphrag.md">Agentic GraphRAG</a> instead of guessing.</li>
</ol>

## Why the team built it

- **Free-tier limits.** Gemini's free tier allowed about 500 calls a day, so one full benchmark run could exhaust it. Taking Gemini off the critical path removes that failure mode for a live demo.
- **Choosing beats writing.** Everything the plan needs already exists as a record in the graph, so the plan is a *selection*, not generation, and a selection can't invent a sport or venue that isn't there.

## Numbers (as submitted)

| | |
|---|---:|
| Exact match | 99 / 100 |
| Seconds per question | 1.7 |
| Gemini calls | 0 (about 1.4 TypeSafe requests) |
| Hidden set: agrees with the fact-box check | 49 / 49 |

!!! note "Why we didn't rerun it"
    It calls TypeSafe's paid API. Everything it depends on in TigerGraph (the event layer and its queries) is the same as the event graph's, which we did reproduce at 99%.

Code: `src/pipelines/jev_planner/pipeline.py`
