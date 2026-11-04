# The six approaches

<p class="lead">Every approach uses the same AI model on the same questions. The only thing that changes is how it finds information before answering.</p>

## At a glance

| Approach | In one line | Score | Tokens / question | Seconds |
|---|---|---:|---:|---:|
| <span class="sw rag"></span>[1 · RAG](rag.md) | Search the text, read the top few passages, answer | 67% | 3,586 | 6.8 |
| <span class="sw graphrag"></span>[2 · GraphRAG](graphrag.md) | Find the entities in the question, follow their links, answer | 67% | 3,952 | 10.2 |
| <span class="sw agentic"></span>[3 · Agent without graph tools](agent-no-graph.md) | An AI loop that keeps searching until satisfied | 70% | 6,065 | 20.2 |
| <span class="sw event"></span>[4 · Event graph](event-graph.md) | Turn the question into an exact database query | 99% | 619 | 8.9 |
| <span class="sw agent"></span>[**5 · Agentic GraphRAG**](agentic-graphrag.md) | An AI loop that **chooses** between exact queries and search | **99%** | 3,412 | 13.2 |
| <span class="sw jev"></span>[6 · Jev planner](jev.md) | Like 4, but picks from lists instead of generating text, with no Gemini at all | 99% | 2,267 | 1.7 |

<small>Scores are exact match on the 100 public questions as submitted by the team. Our rerun matched within one question on every approach; see [Results](../results.md).</small>

## Two ideas explain the whole table

### 1. Searching vs. querying

=== "Searching (approaches 1–3)"

    Like **searching a library and reading only the first few pages that come up**. The question and every passage are turned into "meaning fingerprints"; the closest few passages go to Gemini, which reads them and answers.

    Fast and flexible, but it only ever sees the top few results. If the answer needs 11 articles and the search returns 5, Gemini counts 5 articles' worth and sounds just as confident.

=== "Querying (approaches 4–6)"

    Like **using a spreadsheet filter**. The fact boxes are stored as records, so Gemini's only job is to translate the question:

    > "how many biathlon events at the 2018 Winter Games had more than 73 competitors?"
    > → `count events where sport = Biathlon, games = 2018 Winter, competitors > 73`

    TigerGraph checks **every** matching record and returns the exact answer, the same every time.

### 2. Fixed recipe vs. agent

=== "Fixed recipe (approaches 1, 2, 4, 6)"

    The programmer wrote the steps in advance: *step 1, then step 2, then answer*, no matter what happens. Predictable and cheap, but if step 1 goes wrong the recipe carries on regardless.

=== "Agent (approaches 3 and 5)"

    The AI **decides its own next step**, in a loop:

    1. *Think:* which tool fits?
    2. *Use it* and look at the result.
    3. *Ask itself:* do I have enough to answer?
       - yes → answer
       - no → try a different tool or different words (at most 5 rounds)

    Flexible and able to recover from a bad first try, but each round costs another model call.

**Agentic GraphRAG (approach 5) combines both ideas: an agent whose best tool is an exact query.**

## One question through all five

We sent the same question through the five approaches that run on Gemini, live against our graph:

> *"In the 2018 Winter Games, how many biathlon events drew a field larger than 73 athletes?"*, worded differently from the eval on purpose. The correct answer is **5**.

| Approach | Answer | Model calls | Tokens | Why |
|---|---|---:|---:|---|
| <span class="sw rag"></span>RAG | 2 <span class="no">✕</span> | 2 | 3,732 | saw only some of the 11 event articles |
| <span class="sw graphrag"></span>GraphRAG | 2 <span class="no">✕</span> | 2 | 4,229 | same: links led to a few passages, not all 11 |
| <span class="sw agentic"></span>Agent without graph tools | 4 <span class="no">✕</span> | 9 | 27,197 | kept searching and found more, but not all, at 7× the cost |
| <span class="sw event"></span>Event graph | **5** <span class="ok">✓</span> | 1 | 586 | one exact query over all 11 events |
| <span class="sw agent"></span>Agentic GraphRAG | **5** <span class="ok">✓</span> | 2 | 3,960 | chose the exact query, checked it, answered |

<small>"Model calls" counts every call through the shared client: Gemini calls plus the free local embedding call that the search-based approaches make.</small>
