---
hide:
  - navigation
---

<div class="rv-hero" markdown>
<div class="rv-eyebrow">Hackathon review · TigerGraph Savanna + Gemini</div>

# Agentic GraphRAG, explained

An entry that answers questions about 2,951 Wikipedia articles by **putting the facts into TigerGraph** and letting an **AI agent decide how to query them**. We rebuilt it from scratch on our own Savanna workspace. Its results hold up.
</div>

<div class="rv-stats">
  <div class="rv-stat"><div class="num">67%</div><div class="lbl"><span class="sw rag"></span>Plain search (RAG), the baseline</div></div>
  <div class="rv-stat accent"><div class="num">99%</div><div class="lbl"><span class="sw agent"></span>Agentic GraphRAG, as submitted</div></div>
  <div class="rv-stat"><div class="num">98%</div><div class="lbl">Agentic GraphRAG, our independent rerun</div></div>
  <div class="rv-stat"><div class="num">49 / 50</div><div class="lbl">Hidden-set answers identical to the submission</div></div>
</div>

## The one-minute version

- **The task.** Answer 100 questions, plus 50 hidden ones, about Olympic events, venues and medal winners, using only a fixed set of 2,951 Wikipedia articles.
- **The comparison.** Six approaches answer the same questions with the same AI model (Gemini 3.1 Flash-Lite). Only *how they find information* differs.
- **Search-based approaches stall at 67–70%.** Plain search, following links in an AI-built graph, and an AI agent with search tools all plateau, because many questions need *every* matching record, such as "how many events had more than 73 competitors?", and search only ever looks at the top few.
- **The jump to 99% comes from one design choice.** The fact box at the top of each Olympic article (Games, sport, venue, date, competitors, winner) was loaded into TigerGraph as **structured data**. Counting and "which was biggest" questions become exact database queries instead of guesses.
- **The submitted "Agentic GraphRAG"** is an agent that has that exact query as one of its tools. It picks it when it fits, checks its own evidence, and switches to text search when it doesn't.
- **It reproduces.** We rebuilt the graph and reran everything. Every approach landed within one question of the reported score.

!!! tip "The takeaway for TigerGraph"
    This is a clean demonstration of the graph + agent story: **put whatever facts you can into the graph as structured data, and let the agent choose between exact graph queries and fuzzy search.** The agent alone added 3 points; the structured graph added 29.

!!! warning "Keep in mind"
    Every question in this eval is one of five fixed shapes, and all five ask about fields in those article fact boxes, which is exactly what the structured layer was built for. The 99% shows how well that design fits this eval more than how capable the agent is in general. See [Results → What to keep in mind](results.md#what-to-keep-in-mind).

## Read in this order

<div class="grid cards" markdown>

-   :material-help-circle-outline:{ .lg } **[The problem and the data](problem.md)**

    ---
    What the 2,951 articles and 150 questions look like, and why counting questions are hard for search.

-   :material-sitemap-outline:{ .lg } **[How it works](architecture.md)**

    ---
    The moving parts (TigerGraph, Gemini, embeddings) and what happens when you ask a question.

-   :material-graph-outline:{ .lg } **[The knowledge graph](graph.md)**

    ---
    The three layers inside TigerGraph, how each was built, and the queries that run on them.

-   :material-compare-horizontal:{ .lg } **[The six approaches](approaches/index.md)**

    ---
    Each approach in plain words with a worked example, from plain search to the agent.

-   :material-chart-box-outline:{ .lg } **[Results](results.md)**

    ---
    Scores by approach and question type, cost and speed, the hidden set, and the caveats.

-   :material-check-decagram-outline:{ .lg } **[How we reproduced it](reproduction.md)**

    ---
    What we rebuilt, what matched, and what we found along the way.

</div>

## About this review

| | |
|---|---|
| **Submission** | "GraphRAG vs. RAG vs. Agentic GraphRAG" by Anant Kumar (team *graphrag*), repo `antcybersec/graph_rag` |
| **Reproduced by** | Devanshu Saxena, 4–5 November 2026 |
| **Our setup** | Fresh TigerGraph Savanna 4.2.5 workspace, graph `test`; Gemini 3.1 Flash-Lite on a paid key; local BGE embeddings |
| **What we added** | A redesigned console (`src/dashboard/app_v2.py`), a terminal tool for live questions (`scripts/ask.py`), and this site |
| **Not reproduced** | The *Jev planner* approach, which needs a TypeSafe API key we don't have |
