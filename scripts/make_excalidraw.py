"""Generate an Excalidraw diagram of the architecture.

Open the output at excalidraw.com (File -> Open) and talk over it. Everything is
plain shapes and text, so you can drag pieces around while you rehearse.

    python scripts/make_excalidraw.py
"""
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs/architecture.excalidraw"
random.seed(7)

INK = "#1e1e1e"
BLUE, GREEN, ORANGE, PURPLE, GREY = "#1971c2", "#2f9e44", "#e8590c", "#9c36b5", "#868e96"
FILL_BLUE, FILL_GREEN, FILL_ORANGE, FILL_PURPLE = "#d0ebff", "#d3f9d8", "#ffe8cc", "#f3d9fa"

elements = []


def _base(kind, x, y, w, h, **kw):
    el = {
        "id": f"{kind}-{len(elements)}-{random.randint(1000, 9999)}",
        "type": kind, "x": x, "y": y, "width": w, "height": h, "angle": 0,
        "strokeColor": INK, "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 2, "strokeStyle": "solid", "roughness": 1, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": {"type": 3},
        "seed": random.randint(1, 10**9), "version": 1,
        "versionNonce": random.randint(1, 10**9), "isDeleted": False,
        "boundElements": [], "updated": 1, "link": None, "locked": False,
    }
    el.update(kw)
    return el


def text(label, x, y, size=16, color=INK, width=None, align="left"):
    lines = label.split("\n")
    w = width or max(len(l) for l in lines) * size * 0.58
    el = _base("text", x, y, w, len(lines) * size * 1.25,
               strokeColor=color, roundness=None, text=label, originalText=label,
               fontSize=size, fontFamily=2, textAlign=align, verticalAlign="top",
               containerId=None, lineHeight=1.25, baseline=int(size * 0.8))
    elements.append(el)
    return el


def box(title, body, x, y, w=230, h=100, stroke=INK, fill="transparent", size=15):
    elements.append(_base("rectangle", x, y, w, h, strokeColor=stroke, backgroundColor=fill))
    text(title, x + 14, y + 12, size=size + 1, color=stroke)
    if body:
        text(body, x + 14, y + 12 + (size + 10), size=size - 2, color=INK)


def arrow(x1, y1, x2, y2, label=None, color=INK):
    elements.append(_base("arrow", x1, y1, x2 - x1, y2 - y1, strokeColor=color,
                          roundness={"type": 2}, points=[[0, 0], [x2 - x1, y2 - y1]],
                          startBinding=None, endBinding=None,
                          startArrowhead=None, endArrowhead="arrow",
                          backgroundColor="transparent"))
    if label:
        text(label, (x1 + x2) / 2 - 30, (y1 + y2) / 2 - 24, size=12, color=color)


# ---------------------------------------------------------------- title
text("Agentic GraphRAG on TigerGraph", 40, 20, size=28)
text("One corpus · 100 questions · one model (gemini-3.1-flash-lite) · exact match 67% → 99%",
     40, 60, size=15, color=GREY)

# ---------------------------------------------------------------- ingestion
text("1 · INGEST  (one time)", 40, 110, size=16, color=GREY)
box("Corpus", "2,951 Wikipedia\narticles (JSONL)", 40, 140, 190, 95, stroke=GREY)

box("Chunk + embed", "BGE, runs locally\nno API, no quota", 290, 110, 215, 85, stroke=BLUE, fill=FILL_BLUE)
box("LLM extraction", "entities + relations\n1 call per document", 290, 210, 215, 85, stroke=ORANGE, fill=FILL_ORANGE)
box("Infobox parser", "deterministic\nZERO LLM calls", 290, 310, 215, 85, stroke=GREEN, fill=FILL_GREEN)

arrow(232, 170, 288, 150)
arrow(232, 190, 288, 245)
arrow(232, 210, 288, 345)

# ---------------------------------------------------------------- graph
text("2 · STORE  (TigerGraph Savanna 4.2.5)", 570, 110, size=16, color=GREY)
elements.append(_base("rectangle", 560, 135, 300, 275, strokeColor=GREY,
                      backgroundColor="transparent", strokeStyle="dashed"))
box("Document → Chunk", "+ native vector index\n768-dim, cosine", 575, 150, 270, 75, stroke=BLUE)
box("Entity → RELATED_TO", "12k entities\nfree-text relations", 575, 235, 270, 70, stroke=ORANGE)
box("OlympicEvent → Games\nSport · Venue · PREV_GAMES", "2,210 events, each field\nqueryable: competitors,\nnations, venue, date, gold",
    575, 315, 270, 85, stroke=GREEN)

arrow(507, 150, 573, 180)
arrow(507, 250, 573, 262)
arrow(507, 350, 573, 350)

# ---------------------------------------------------------------- agent
text("3 · ANSWER  (per question)", 920, 110, size=16, color=GREY)
box("ORCHESTRATOR AGENT", "plans the next step ·\nchecks its own evidence\nin the SAME call ·\nstops when satisfied",
    910, 140, 265, 120, stroke=PURPLE, fill=FILL_PURPLE, size=16)

box("5 tools it chooses from",
    "query_events  (GSQL: count, max)\nquery_facts   (as-of a date)\nlink_entities (vector)\ngraph_traverse (1 hop)\nsearch_chunks (vector)",
    910, 280, 265, 130, stroke=PURPLE)

arrow(1042, 262, 1042, 278)
arrow(862, 200, 908, 200, "reads")
arrow(908, 345, 862, 360, "queries", color=PURPLE)

box("Answer + evidence", "every item carries:\ndoc id · source URL ·\nthe query that produced it",
    910, 440, 265, 95, stroke=INK)
arrow(1042, 412, 1042, 438)

# ---------------------------------------------------------------- results lane
text("WHAT THE MEASUREMENT SHOWED", 40, 470, size=16, color=GREY)
box("RAG", "vector search only\n67%   ·   aggregation 1/21", 40, 500, 245, 75, stroke=BLUE)
box("GraphRAG", "entity graph, fixed route\n67%   ·   aggregation 0/21", 310, 500, 245, 75, stroke=ORANGE)
box("Agent, text/entity tools only", "the ABLATION\n70%   ·   aggregation 3/21", 580, 500, 275, 75, stroke=GREY)
box("Agent + structured graph tools", "THE SUBMISSION\n99%   ·   aggregation 21/21", 40, 600, 295, 75, stroke=PURPLE, fill=FILL_PURPLE)
box("Selection planner (no LLM gen)", "same 99% · 1.7s/question\nZERO generation calls", 360, 600, 295, 75, stroke=GREEN, fill=FILL_GREEN)

text("The agent alone buys +3 points.  The agent WITH the right graph tools buys +32.",
     690, 610, size=15, color=PURPLE)
text("Counting needs every matching document (up to 43).\nRetrieval hands you 5. That is why RAG cannot do it.",
     690, 640, size=13, color=GREY)

doc = {
    "type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
    "files": {},
}
OUT.write_text(json.dumps(doc, indent=1))
print(f"wrote {OUT.relative_to(Path.cwd())} · {len(elements)} elements")
