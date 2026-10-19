# Presentation prep — 5 min talk + 5 min Q&A

Read Part 1 once to get the vocabulary straight. Part 3 is what you say.
Part 4 is what you'll be asked.

---

# Part 1 · The foundations, from the bottom

Each term here appears somewhere in your project. If a judge uses one of these
words, this is what they mean.

**Python** — the language the whole project is written in. A `.py` file is a
*script* or *module*; `python -m src.eval.run_benchmark` means "run that module".
Nothing in your project is magic: it's files that read data, call services, and
write results.

**API** — a service you send a request to over the internet and get a reply.
You used two: Google's Gemini (a language model) and TypeSafe (a judgment model).
An **API key** is the password that identifies you. A **rate limit / quota** is
the cap on how many requests you may send — Gemini's free tier is 500 a day,
which is the single biggest constraint you hit all week.

**LLM (large language model)** — a model that takes text and produces text. You
used `gemini-3.1-flash-lite`, deliberately a cheap small one.

**Token** — roughly a word-piece. Models charge and limit by tokens. "3,412
tokens per question" means that's how much text went in and out per answer.
**Context** is the text you put in the prompt for the model to read.

**Embedding** — a list of numbers (yours are 768 long) representing the meaning
of a piece of text. Two texts about the same thing end up with similar numbers.
**Cosine similarity** is the measure of "how close are these two lists". A
**vector index** is a database structure that finds the closest vectors fast.
Yours is TigerGraph's own, with embeddings generated locally by `BAAI/bge-base-en-v1.5`
— no API, so no quota.

**RAG (retrieval-augmented generation)** — the baseline: embed the question,
find the most similar chunks of text, paste them into the prompt, let the model
answer. It can only answer from what retrieval happened to fetch. That single
sentence explains your aggregation failure.

**Chunk** — documents are long, so they're split into pieces (~550 tokens) and
each piece is embedded separately.

**Reranker / cross-encoder** — a smaller model that reads the question and a
candidate passage *together* and scores how relevant it really is. Vector search
is fast but rough; the reranker reorders the top candidates. Yours is
`BAAI/bge-reranker-base`, also local.

**Graph database** — stores data as **vertices** (things) and **edges**
(relationships), instead of tables. TigerGraph is one. **GSQL** is its query
language. A **traversal** means walking from one vertex along edges to others —
"from this Games, hop to the Games before it".

**GraphRAG** — RAG plus graph structure: instead of only matching text, you
link entities and walk relationships to gather evidence.

**Agent** — a program where the *model decides what to do next* instead of
following a fixed sequence. The **orchestrator** is the loop that asks the model
"given what you know, which tool now?". A **tool** is a thing it can call
(a query, a search). **Stopping criteria** is how it decides it has enough.
**Trace** is the recorded list of what it did — that's your audit trail.

**Exact match** — compare the answer to the gold answer directly, no model
involved. **LLM-as-judge** — ask a model to score an answer 1–5. You use exact
match as the headline *because* your judge turned out unreliable.

**Ablation** — running the same system with one piece removed, to prove that
piece is what mattered. Your 70% pipeline is an ablation.

---

# Part 2 · Your system in those words

**Ingestion, done once.** The 2,951 articles are processed three ways:
1. split into chunks and embedded locally → the vector index;
2. sent to the LLM once per document to pull out entities and relationships →
   the entity graph (12k entities);
3. parsed for the **infobox** at the top of each article — event, games, venue,
   date, competitors, nations, gold — with **no LLM at all** → the event graph
   (2,210 events) and 2,316 time-stamped facts.

Step 3 is the one that won. The infobox is already structured data; extracting it
with a language model would only add errors and cost.

**Answering, per question.** The orchestrator looks at the question and picks
one of five tools: a structured graph query (counts, maximums, field lookups),
a time-scoped fact query, entity linking, a one-hop traversal, or vector search
over chunks. It writes down what the evidence does and doesn't establish *in the
same call* as the decision — so self-checking is free — then either answers with
citations or tries a different tool.

**Why that beats RAG.** "How many cycling events had more than 30 competitors"
needs *every* matching event — sometimes 43 documents. RAG retrieves five. The
graph can count all of them in one query, so aggregation goes 1/21 → 21/21.

---

# Part 3 · The 5-minute talk

Have the Excalidraw diagram on screen. Timings are a guide, not a script to rush.

### 0:00–0:40 · What I built and why

> "I built an agentic GraphRAG system on TigerGraph over a corpus of about
> three thousand Wikipedia articles. Rather than just build one pipeline, I built
> six and benchmarked them against the same hundred questions with the same
> model, because the question I actually wanted to answer was the one in the
> brief: when does an agent earn its cost, and when is it overkill?
>
> The headline: exact match went from sixty-seven percent with plain RAG to
> ninety-nine percent with the agentic pipeline. But the more useful finding is
> *where* those thirty-two points came from."

### 0:40–1:40 · The failure that shaped the design *(point at the results lane)*

> "Plain RAG scored sixty-seven. GraphRAG — entity linking plus one-hop
> traversal — also scored sixty-seven. Identical. So I broke the results down by
> question type, and one type explained almost everything.
>
> Aggregation questions: 'how many cycling events had more than thirty
> competitors'. RAG got one out of twenty-one. GraphRAG got zero.
>
> That's structural, not a tuning problem. Answering it needs every matching
> document — for one question, forty-three of them. Retrieval fetches the top
> five and the model counts those, then reports a confident wrong number. My
> LLM-extracted entity graph didn't help either: it had twelve thousand entities
> with free-text relations, but 'competitors: 43' was never a field you could
> filter or count on. I had modelled the prose instead of the facts."

### 1:40–2:40 · The architecture *(walk the diagram left to right)*

> "So ingestion does three things. It chunks and embeds documents locally with
> BGE into TigerGraph's native vector index. It runs one LLM call per document
> to extract entities. And — this is the part that mattered — it parses the
> infobox at the top of each article into a proper event graph: every Olympic
> event linked to its Games, its sport, its venue, and to the Games before it.
> That parser makes zero LLM calls, because the infobox is already structured.
>
> At query time the orchestrator picks between five tools: the structured graph
> query, a time-scoped fact query, entity linking, graph traversal, and vector
> search. It states what the evidence establishes in the same structured call as
> its routing decision, so evaluating its own evidence costs nothing extra. Then
> it answers with citations, or changes strategy."

### 2:40–3:40 · The result that I think matters *(point at the bottom two boxes)*

> "Here's the comparison I'd want you to look at. An agent given only text and
> entity tools scores seventy percent — three points over RAG. The *same*
> orchestrator, same model, with structured graph tools, scores ninety-nine —
> thirty-two points. I kept the weaker one as an ablation precisely to isolate
> that.
>
> So the agentic architecture alone bought three points. The agent with the right
> retrieval surface bought thirty-two. Agency isn't what pays; agency over the
> right thing is."

### 3:40–4:30 · Efficiency and the surprise

> "Two numbers on cost. The agent reaches ninety-nine percent on three thousand
> four hundred tokens a question — fewer than plain RAG's three thousand five
> hundred. It averages two steps, and all hundred investigations stopped because
> the agent judged the evidence sufficient, never because it ran out of budget.
>
> And then a result I didn't expect. If the agent picks the structured query on
> every question, does it need to generate a plan at all? Everything it decides
> already exists as a row in the graph — the sports, the Games, the venues. So I
> replaced the generative planner with typed selection: same ninety-nine percent,
> one point seven seconds instead of thirteen, and zero generation-model calls.
> That path can't hit a rate limit, which matters when the free tier is five
> hundred calls a day and every one of my benchmark runs died on it."

### 4:30–5:00 · Close

> "So my answer to the brief: agents earn their cost on open-ended questions, and
> they're overkill where a typed query settles it — and I can show you exactly
> which questions fall on each side. Fifty out of fifty hidden questions
> answered, every number reproducible from the repo, and the one thing I'd flag
> myself is that my LLM judge scored fourteen wrong answers as correct, which is
> why exact match is my headline metric. Happy to take questions."

---

# Part 4 · Q&A drill

## They will probably ask these

**"Why is your Agentic number 99 but the dashboard shows a 70?"**
> Two different agent designs. The seventy is the ablation — same orchestrator,
> same model, without the structured graph tools. I kept it in deliberately,
> because it's what proves the thirty-two points come from the retrieval surface
> and not from the agentic loop itself.

**"Isn't 99% just hardcoding the eval set?"**
> Fair challenge, and I tested it. I rewrote ten questions to avoid the eval's
> wording entirely — using host cities like "Sydney 2000", which never appear in
> the dataset — and it got ten out of ten. Mapping "Sydney 2000" to the 2000
> Summer Games is the planner's inference; no regex in my code contains it.

**"Your event-graph pipeline also hits 99% without an agent. So why the agent?"**
> That's exactly the finding, and I report it rather than hide it. For these
> templated factual questions the agent is unnecessary. It earns its place on
> anything the graph doesn't model — ask it who directed a film and it switches
> to vector search on its own. You ship the agent because you don't know which
> kind of question arrives next.

**"Did you use the same model everywhere?"**
> Yes. `gemini-3.1-flash-lite` for every pipeline in the comparison, through one
> shared client with no per-pipeline override. Embeddings are local BGE for all
> of them. The judge deliberately uses a *different* model to reduce
> self-preference, and it only scores a twenty percent sample.

**"You used TypeSafe for one pipeline — isn't that an unfair model swap?"**
> Which is why I report it separately and never inside the three-way comparison.
> It's an efficiency result, not an accuracy claim: same ninety-nine percent with
> zero generation calls. The accuracy comparison is strictly same-model.

**"How do you know the hidden answers are right? There's no gold."**
> I wrote a deterministic checker that computes each answer straight from the
> corpus infoboxes, with no model involved, and validated it where gold does
> exist — it agrees with the published answers on ninety-nine of a hundred public
> questions. Against that, my hidden answers are forty-nine out of forty-nine on
> every question it can check.

**"What's your token efficiency story?"**
> The agent is cheaper than the baseline it beats: three thousand four hundred
> tokens versus RAG's three thousand five hundred, for thirty-two more points.
> The selection planner is two thousand two hundred. Aggregation is the reason —
> counting happens inside the database instead of by stuffing forty-three
> documents into a prompt.

**"How does the agent decide to stop?"**
> It states an evidence check in the same call as its routing decision, and only
> chooses to answer when that check passes. There's a hard cap of five
> iterations as a backstop, but across all hundred questions it never hit it —
> every single one stopped on "answer found".

**"What's in the trace?"**
> Per question: the steps, which tools were called with what arguments, the
> agent's own evidence check at each step, how many new evidence items the tool
> returned, per-step timing, why it stopped, and whether it changed strategy.
> Every evidence item carries its source document, URL, and the exact query that
> produced it. It's all in `hidden_50_results.json`.

## The hard ones

**"What's the weakest part of this?"**
> Three things. First, the event layer is built for this corpus's infobox
> structure — a different corpus needs a different parser, though the agent and
> the vector path carry over unchanged. Second, GraphRAG's global search over
> community summaries isn't implemented; the `Community` vertex exists unused.
> Third, my LLM judge was unreliable and I'd rebuild evaluation differently from
> the start.

**"What would you do with more time?"**
> Round 2's problem: reasoning over conflicting facts. I've built the temporal
> half — two thousand three hundred interval-stamped facts with provenance, and
> an as-of-date tool — but this corpus has essentially no genuine contradictions,
> so authority-based conflict resolution would need a corpus that actually
> disagrees with itself.

**"Did anything break?"**
> Plenty, and it's in the write-up. One change of mine dropped accuracy from
> ninety-nine to eighty-two: the agent couldn't see what its tools had computed,
> so it recounted a truncated evidence list and answered "twelve" — the size of
> the cap — to seven counting questions. And my hidden answers were once
> generated two minutes before a bug fix, with five wrong counts; I caught it by
> answering them again with a second pipeline and scoring both against the
> oracle. Every one of those is now a regression test.

**"Why should we trust your numbers?"**
> Because none of the headline ones need a model to verify. Exact match is string
> comparison, the oracle computes answers from the corpus, and both run with no
> API key. `python -m tests.test_regressions` and `python -m src.eval.oracle`
> work on a fresh clone.

## If you don't know the answer

Say so, then give the nearest thing you do know:
> "I haven't measured that. What I can tell you is [closest measured fact]. I'd
> test it by [concrete method]."

Never invent a number. Judges remember a confident wrong figure far longer than
an honest "I didn't measure that".

---

# Part 5 · Numbers to have cold

| | RAG | GraphRAG | Agent (ablation) | Agent (full) | Selection planner |
|---|---|---|---|---|---|
| Exact match | 67% | 67% | 70% | **99%** | 99% |
| Aggregation | 1/21 | 0/21 | 3/21 | **21/21** | 21/21 |
| Tokens/q | 3,586 | 3,952 | 6,065 | 3,412 | 2,267 |
| Seconds | 6.8 | 10.2 | 20.2 | 13.2 | **1.7** |

- Corpus 2,951 docs · 100 public questions · 50 hidden
- Agent: 2.04 steps, 2.08 LLM calls, 4.2 citations per question
- Tools invoked: structured query 100, vector search 4 · stopped on "answer found" 100/100 · changed strategy 4
- Judge scored 14 wrong answers as 4–5; verification catches 14/14
- Paraphrase robustness 10/10 · hidden set 49/49 oracle-checkable
- Model `gemini-3.1-flash-lite` · embeddings `BAAI/bge-base-en-v1.5` · TigerGraph Savanna 4.2.5, 768-dim cosine vector index
