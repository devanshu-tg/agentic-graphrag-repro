# 3 · Agent without graph tools

<div class="rv-tldr" style="--rv-accent: var(--c-agentic)" markdown>
<div class="t">In one sentence</div>
<div class="b">Let Gemini run a loop (search, look, decide what to search next) until it thinks it has enough, using only the text and entity tools.</div>
<div class="m">The control experiment · 70% · about 6,000 tokens and 20 seconds per question</div>
</div>

**Analogy:** a research assistant who can rephrase searches and follow references, but has never seen the spreadsheet of events.

## Why this approach exists

This is the **ablation**: the same agent design as the submitted approach, *minus* the exact-query tools. It answers one question: *is the improvement coming from the agent, or from the structured graph?* It is the most informative row in the results table.

## How it works

Each round is one Gemini call that returns a decision:

| Tool it can choose | What it does |
|---|---|
| `link_entities` | find entities near a phrase (vector index) |
| `graph_traverse` | follow those entities' links one step |
| `search_chunks` | vector search over passages, re-ranked to the best 4 |
| `answer` | stop and answer from the evidence so far |

It repeats for at most 5 rounds.

## Example

> **"In the 2018 Winter Games, how many biathlon events drew a field larger than 73 athletes?"** Correct answer: 5. *(Our live run.)*

It searched repeatedly with different wordings and found more events than plain search, then answered **4** <span class="no">✕</span>. It used 9 model calls and about 27,000 tokens, roughly 7× what Agentic GraphRAG spent getting it right.

## What it tells us

| | Score |
|---|---:|
| Plain search (RAG) | 67% |
| **+ agent loop** | **70%** (+3 points) |
| + agent loop **+ exact graph queries** (Agentic GraphRAG) | **99%** (+29 more) |

**The agent on its own buys about 3 points. The structured data in TigerGraph buys the rest.** Searching more cleverly cannot fix a search that only returns the top few results.

## Numbers

| | Submitted | Our rerun |
|---|---:|---:|
| Exact match | 70 / 100 | 70 / 100 |
| Model calls per question | 4.1 | 4.1 |
| Tokens per question | 6,065 | 6,367 |
| Seconds per question | 20.2 | 17.8 |

Code: `src/pipelines/agentic/pipeline.py`. In the team's dashboard it is labelled "Agentic GraphRAG (ablation, no graph tools)".
