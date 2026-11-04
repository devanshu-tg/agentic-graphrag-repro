# Review and reproduction of this submission

This is a private copy of [antcybersec/graph_rag](https://github.com/antcybersec/graph_rag) (Anant Kumar's
"Agentic GraphRAG" hackathon entry), rebuilt and rerun end to end on our own TigerGraph Savanna 4.2.5 workspace.

**Start here: open [`docs-site/site/index.html`](docs-site/site/index.html) in a browser** (download or clone the
repo, then double-click it). It explains every approach, the graph and the results in plain language, and
records what we found reproducing it.

## Branches

| Branch | Contents |
|---|---|
| `main` | The submission exactly as published (commit `2e6f925`) |
| `reproduction` (default) | `main` plus everything below |

## What the `reproduction` branch adds

| Path | What it is |
|---|---|
| `docs-site/` | The explainer site: Markdown source in `docs/`, ready-to-open build in `site/` |
| `src/dashboard/app_v2.py` | Redesigned console: live Q&A, benchmark browser (submitted vs. reproduced), graph schema and GSQL query runner. The original `app.py` is unchanged. |
| `scripts/ask.py` | Ask the live graph from the terminal; `--compare` runs all five Gemini-based approaches |
| `data/results/repro_*.jsonl` | Our benchmark results: public set (5 approaches × 100) and hidden set |
| `data/results/extractions.jsonl` | Our Gemini entity extraction. Reusing it skips about 1,600 Gemini calls. |
| `data/results/extraction_failures.jsonl` | The 14 articles Gemini's safety filter refused |

## Result in one line

Every approach reproduced within one question of the submitted score (Agentic GraphRAG: 99% submitted, 98% rerun;
hidden set 49/50 answers identical). Details: `docs-site/site/reproduction.html`.

No credentials are stored in this repo. Copy `.env.example` to `.env` and add your own.
