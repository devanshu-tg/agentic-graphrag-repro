# The problem and the data

<p class="lead">A fixed library of articles, a set of questions about it, and one rule: the answer must come from the library, not from what the AI model already knows.</p>

## The library: 2,951 Wikipedia articles

| | |
|---|---|
| **Size** | 2,951 English Wikipedia articles, about 5.5 million tokens (roughly 4 million words) |
| **Subject** | Mostly individual Olympic events, plus some politicians and office holders, and some films. Coverage spans 1987–2023. |
| **Rule** | The library is the only source of truth. If Wikipedia today says something different, the library wins. |

Almost every Olympic article starts with a small, regular **fact box** (Wikipedia calls it an *infobox*). It is the key to this whole project:

```text
[Infobox Olympic event]
  event:        Men's canoe sprint K-2 1,000 metres
  games:        2012 Summer
  venue:        Eton Dorney
  date:         6 to 8 August
  competitors:  24
  nations:      12
  gold:         Rudolf Dombi, Roland Kökény
```

The rest of the article is ordinary prose: background, race reports, results tables.

## The questions: 100 public, 50 hidden

The organisers supplied **100 questions with answers** for development and **50 hidden questions without answers** for judging. Every question falls into one of five types:

| Type | Public | Hidden | Real example | Answer |
|---|---:|---:|---|---|
| **Lookup**: read one fact | 19 | 7 | How many nations competed in Judo at the 2016 Summer Olympics – Women's 57 kg? | 23 |
| **Multi-hop**: find the event first, then the fact | 28 | 10 | Who won the gold medal in the event held at Richmond Olympic Oval on 14 February 2010? | Martina Sáblíková |
| **Temporal**: work out *which* Games first | 22 | 8 | Who won the men's 20 km walk at the Summer Olympics held immediately before 2016? | Chen Ding |
| **Superlative**: compare every event | 10 | 10 | Which sailing event at the 2000 Summer Olympics had the highest number of competitors? | Soling |
| **Aggregation**: count across every event | 21 | 15 | How many biathlon events at the 2018 Winter Olympics had more than 73 competitors? | 5 |

!!! note "Every question is about the fact box"
    All five types ask about fields in those fact boxes: competitors, nations, venue, date, gold medallist, and which Games came before which. That matters later.

## Why some of these are hard

The first three types need one or two articles. A search that finds the right article is enough.

**Aggregation and superlative questions need every matching article at once.** Take the biathlon question:

- There are **11** biathlon events at the 2018 Winter Games in the library, each in its own article.
- To answer "how many had more than 73 competitors?", you have to look at **all 11** and count.
- A search engine returns the *top few* most relevant pieces of text, typically 5 to 20 chunks out of 14,332. If only some of the 11 articles make it into that set, the count comes out wrong, and nothing tells you it is wrong.

That single weakness explains most of the gap between the approaches. See [Results](results.md#by-question-type): plain search scores **1 out of 21** on aggregation questions.

## How answers are scored

| Metric | How it works | Trust it for |
|---|---|---|
| **Exact match** (headline) | Compares the answer to the official answer with fixed rules, no AI involved. A list of several candidate answers counts as wrong. | The real score |
| **AI judge** (secondary) | A *different* Gemini model grades 1–5 for accuracy, completeness and groundedness, on a 20% sample (21 questions) | A rough second opinion only. On the team's first run it gave 4–5 to 14 answers that were actually wrong. |
| **Document precision / recall** | Did the approach retrieve the articles the official answer comes from? | Whether failures come from finding or from reasoning |
| **Tokens, model calls, seconds** | Cost and speed per question | Trade-offs |
