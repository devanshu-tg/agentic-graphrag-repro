# How we reproduced it

<p class="lead">We cloned the repo, built the whole graph from scratch on a fresh TigerGraph Savanna workspace with our own Gemini key, and reran every approach that doesn't need a TypeSafe key. The results match.</p>

## Setup

| | |
|---|---|
| **Graph database** | A fresh TigerGraph Savanna 4.2.5 workspace, the same version the team used, with an empty graph named `test` |
| **AI model** | Gemini 3.1 Flash-Lite on a paid key; the judge is Gemini 3.1 Flash-Lite Preview, as in the team's setup |
| **Local models** | BGE-base embeddings and the BGE reranker, run on a MacBook (Apple Silicon) |
| **Code** | The submitted repo at commit `2e6f925`, unmodified. Our additions are separate files. |
| **Dates** | 4–5 November 2026 |

## What we ran

<ol class="rv-steps">
<li><b>Built the graph</b> with all eight steps in order (<a href="architecture.md#how-the-graph-is-built">listed here</a>), including the two the README leaves out.</li>
<li><b>Ran the public benchmark</b> for five approaches × 100 questions (500 scored answers), with the AI judge on the same 20% sample.</li>
<li><b>Ran the hidden set</b> through Agentic GraphRAG and the event graph, and checked both with the team's fact-box checker.</li>
<li><b>Reran the reworded-question test</b> (10 questions) and the regression tests (6).</li>
<li><b>Asked live questions</b> through every approach, and ran the installed GSQL queries directly against the graph.</li>
</ol>

## What we built

| | Count |
|---|---:|
| Articles loaded | 2,951 of 2,951 |
| Text chunks, each with its embedding | 14,332 |
| Articles with entities extracted by Gemini | 2,937 of 2,951 |
| Entities after merging duplicates | 19,032 |
| Entity relationships | 17,723 |
| Structured Olympic events | 2,210 |
| Dated facts | 2,316 |
| Gemini calls for the one-time extraction | about 1,600 (about 11 million tokens) |

## Do the numbers match?

| Approach | Submitted | Ours |
|---|---:|---:|
| RAG | 67 | 67 |
| GraphRAG | 67 | 67 |
| Agent without graph tools | 70 | 70 |
| Event graph | 99 | 99 |
| Agentic GraphRAG | 99 | 98 |
| Hidden set: same answers as the submission | — | 49 / 50 |
| Reworded questions | 10 / 10 | 10 / 10 |

**Yes.** The one-point difference on Agentic GraphRAG is a single question where our run of the agent second-guessed a data error in the source article ([details](approaches/agentic-graphrag.md#how-agentic-is-it-in-practice)). That is model variation, not a difference in the system.

## What we found along the way

These matter for anyone rebuilding it. None of them changes the results.

!!! warning "1 · The README is missing two required build steps"
    `fix_related_to_discriminator` must run right after `create_schema`; without it, two entities can hold only one relationship. `build_temporal_facts` must run at the end; without it, the agent's dated-fact tool has no data and no queries. Both scripts exist in the repo. Only the README omits them.

!!! note "2 · The graph name is fixed"
    Every build script targets a graph named `test`, which must exist before the first connection.

!!! note "3 · Benchmark results need their own file"
    By default, the benchmark writes into the team's committed results file and **skips any question already in it**. A fresh run against the repo as shipped would silently do almost nothing. Pass `--output` with a new file name.

!!! note "4 · Gemini refuses 14 articles"
    Entity extraction failed on the same 14 articles every time. All are films with mature themes (for example *Irréversible* and *Hostel*), blocked by Gemini's safety filter. None of the questions involve them, and their text is still searchable.

!!! note "5 · The AI-built layer differs run to run"
    Gemini's extraction isn't deterministic, so our entity graph is similar to the team's, not identical. Only the weaker approaches rely on it, and their scores still matched. The two 99% approaches use layers built without AI, which come out the same every time.

!!! note "6 · Built-in pacing assumes the free tier"
    The code waits 6.5 seconds between Gemini calls to stay under free-tier limits. On a paid key we shortened that for the one-time extraction only, and kept the default for benchmark runs so latency numbers stay comparable.

## Not reproduced

| Item | Why |
|---|---|
| Jev planner | Needs a TypeSafe API key |
| `scripts/demo.py` | Runs the Jev planner |
| Evidence verification (`verify_evidence.py`) | Uses TypeSafe |

## Where everything is

| | Location in the repo |
|---|---|
| Our public benchmark results | `data/results/repro_public.jsonl` |
| Our hidden-set answers | `data/results/repro_hidden_investigator.jsonl`, `data/results/repro_hidden_event_graph.jsonl` |
| Our Gemini entity extraction (reusable, skips about 1,600 calls) | `data/results/extractions.jsonl` |
| The 14 refused articles | `data/results/extraction_failures.jsonl` |
| The team's original results, unchanged | `data/results/benchmark_results.jsonl`, `benchmark_v4_investigator.jsonl`, `hidden_50_results.json` |
