# Glossary

Agent
:   An AI model run in a loop that chooses its own next action (which tool to use, with what settings), looks at the result, and decides whether to answer or keep going. Contrast with a *fixed recipe*, where the programmer decides the steps in advance.

Agentic GraphRAG
:   The submitted approach: an agent whose tools include exact graph queries as well as search. Called `investigator` in the code.

Chunk
:   A passage of an article, a few hundred words long. Search works on chunks rather than whole articles.

Embedding (meaning fingerprint)
:   A list of numbers (768 here) that captures what a piece of text means. Texts with similar meanings get similar numbers, which is what makes similarity search possible.

Entity
:   A person, place, team, event or organisation mentioned in an article. Here Gemini extracted them by reading every article.

Exact match
:   The headline score. The answer is compared with the official answer by fixed rules, with no AI involved.

Exact query
:   A database query with precise conditions ("sport = Biathlon and competitors > 73"). It checks every matching record and returns the same answer every time.

Fact box (infobox)
:   The standard summary table at the top of a Wikipedia article. For Olympic events it lists Games, sport, venue, date, competitors, nations and medallists.

Fixed recipe (pipeline)
:   An approach whose steps are written by the programmer and run the same way every time.

GraphRAG
:   Retrieval-augmented generation over a graph of entities and relationships, rather than over plain text alone.

GSQL
:   TigerGraph's query language. Queries are *installed* on the graph and called by name.

Hidden set
:   The 50 judging questions, released without answers.

LLM (large language model)
:   An AI text model, here Google's Gemini 3.1 Flash-Lite.

LLM judge
:   A second AI model that grades answers 1–5. Useful as a rough signal, not as ground truth.

Oracle (fact-box checker)
:   The team's script that computes each answer directly from the fact boxes, with no AI and no database, used to check the hidden set.

RAG (retrieval-augmented generation)
:   Find relevant text first, then have the AI answer from it.

Re-ranking
:   A second, more careful scoring pass over search results, so the best passages reach the AI first.

Savanna
:   TigerGraph's managed cloud service.

Similarity search (vector search)
:   Finding the chunks whose embeddings are closest to the question's. It returns the top few, never "all matches". TigerGraph does this natively.

Token
:   The unit AI models read and write, roughly three-quarters of a word. Cost scales with tokens.

Vertex / edge
:   A node and a connection in a graph. For example, an `OlympicEvent` vertex connected by a `HELD_AT` edge to a `Venue` vertex.
