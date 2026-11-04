"""Agentic GraphRAG console: live graph Q&A, the benchmark, and the TigerGraph graph itself.

    streamlit run src/dashboard/app_v2.py

Added locally during the reproduction. The original submission dashboard is app.py and is
left untouched; this file reuses its data layer (data.py) and its pipeline color slots.

Design rules carried over from app.py and the dataviz method:
  * color means "which pipeline" and nothing else; chrome stays neutral;
  * categorical slots in fixed order, validated on this dark surface (adjacent pairs pass);
  * scatters cannot rely on six hues (all-pairs fails), so they gray every pipeline but the
    highlighted one and label each point by name;
  * hero numbers are proportional Inter; tabular figures only where numbers align.
"""
from __future__ import annotations

import html
import importlib
import os
import re
import sys
import textwrap
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.dashboard import data as bench  # noqa: E402

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except Exception:
    pass

st.set_page_config(
    page_title="Agentic GraphRAG",
    page_icon=":material/hub:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------------------------------------------------------------------------- tokens

INK = {
    "page": "#0b0d10",
    "surface": "#111318",
    "raised": "#161a20",
    "primary": "#f0efec",
    "secondary": "#c3c2b7",
    "muted": "#898781",
    "grid": "#2c2c2a",
    "axis": "#383835",
    "node_line": "#3a404a",
}
GOOD, CRITICAL = "#0ca30c", "#d03b3b"
# Sequential (dark mode): low values recede toward the surface, high values brighten.
SEQ = ["#0d366b", "#1c5cab", "#2a78d6", "#3987e5", "#86b6ef", "#cde2fb"]

# Categorical slots 1-6 in the validated order -- one per pipeline, constant everywhere.
PIPES = {
    "rag": {"short": "RAG", "color": "#3987e5",
            "blurb": "Vector search over document chunks, then one Gemini call to answer."},
    "graphrag": {"short": "GraphRAG", "color": "#d95926",
                 "blurb": "Entity linking, a 1-hop graph traversal, then one Gemini call."},
    "agentic": {"short": "Agent · no graph tools", "color": "#199e70",
                "blurb": "An agent loop over text and entity tools only (the ablation)."},
    "event_graph": {"short": "Event graph · fixed", "color": "#c98500",
                    "blurb": "One Gemini call plans a typed query; GSQL answers it from the event layer."},
    "investigator": {"short": "Agentic GraphRAG", "color": "#d55181",
                     "blurb": "The submitted agent: picks among five graph and text tools and checks its own evidence."},
    "jev_planner": {"short": "Jev planner", "color": "#008300",
                    "blurb": "Selection planner on TypeSafe System One; no generation model."},
}
for _k, _v in PIPES.items():
    _v["label"] = bench.PIPELINE_LABELS[_k]
COLOR_BY_SHORT = {v["short"]: v["color"] for v in PIPES.values()}
AGENT = "investigator"
LIVE_PIPES = ["investigator", "event_graph", "graphrag", "rag", "agentic"]
COMPARE_ORDER = ["rag", "graphrag", "agentic", "event_graph", "investigator"]

EXAMPLES = [
    "Who won gold at Richmond Olympic Oval on 14 February 2010?",
    "In the 2018 Winter Games, how many biathlon events drew a field larger than 73 athletes?",
    "Which sailing event at Sydney 2000 had the biggest field?",
    "Who was the President of Russia on 1 January 2013?",
    "How many nations entered the women's 57 kg judo at the 2016 Rio Olympics?",
    "Who won the women's 200 m freestyle swimming gold at the Games immediately preceding Rio 2016?",
]

TOOLS = {
    "query_events": ("Event graph query", "GSQL over OlympicEvent, Games, Sport and Venue"),
    "query_facts": ("Temporal fact query", "GSQL over TemporalFact validity intervals"),
    "search_chunks": ("Vector search", "TigerGraph vector index on Chunk.embedding, then rerank"),
    "link_entities": ("Entity linking", "TigerGraph vector index on Entity.embedding"),
    "graph_traverse": ("Graph traversal", "1-hop RELATED_TO and MENTIONS from linked entities"),
    "answer": ("Answer", "the agent judged its evidence sufficient and answered"),
}
EVENT_OP_QUERY = {
    "count_events_over": "events_by_games_sport",
    "top_event_by_competitors": "events_by_games_sport",
    "event_field": "events_by_games_sport",
    "gold_at_venue_date": "events_at_venue",
    "gold_previous_games": "events_in_previous_games",
}

# --------------------------------------------------------------------------- css

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root{--page:#0b0d10;--surface:#111318;--raised:#161a20;--ink:#f0efec;--ink-2:#c3c2b7;--muted:#898781;
--line:rgba(255,255,255,0.08);--line-2:rgba(255,255,255,0.15);--good:#0ca30c;--critical:#d03b3b;}
html,body,.stApp,[class*="css"]{font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;}
.stApp{background:var(--page);}
[data-testid="stMainBlockContainer"]{max-width:1240px;padding-top:4.6rem;padding-bottom:5rem;}
button[data-variant="segmented_control"]{background:transparent;}
button[data-variant="segmented_control"] p{color:var(--ink-2);}
button[data-variant="segmented_control"][data-selected="true"]{background:var(--ink) !important;border-color:var(--ink) !important;}
button[data-variant="segmented_control"][data-selected="true"] p{color:#0b0d10 !important;font-weight:600;}
button[data-variant="pills"]{background:var(--surface);border-color:var(--line-2);}
button[data-variant="pills"] p{color:var(--ink-2);}
button[data-variant="pills"]:hover p{color:var(--ink);}
button[data-variant="pills"][data-selected="true"]{background:rgba(240,239,236,0.14) !important;border-color:var(--ink-2) !important;}
button[data-variant="pills"][data-selected="true"] p{color:var(--ink) !important;font-weight:600;}
[data-testid="stAppDeployButton"]{display:none;}
[data-testid="stHeader"]{background:var(--page);border-bottom:1px solid var(--line);}
[data-testid="stSidebarCollapsedControl"]{display:none;}
code,.mono{font-family:'JetBrains Mono',ui-monospace,'SF Mono',Menlo,monospace;}
a{color:var(--ink);}

/* top bar */
.ag-top{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;margin:0 0 1.6rem;}
.ag-brand{display:flex;align-items:center;gap:10px;color:var(--ink);font-weight:650;font-size:1.02rem;letter-spacing:-0.01em;}
.ag-brand small{color:var(--muted);font-weight:500;font-size:.82rem;}
.ag-pill{display:inline-flex;align-items:center;gap:8px;font-size:.78rem;color:var(--ink-2);border:1px solid var(--line);
border-radius:999px;padding:6px 12px;background:var(--surface);}
.ag-pill b{color:var(--ink);font-weight:600;}
.ag-dot{width:8px;height:8px;border-radius:50%;background:var(--good);flex:none;}
.ag-dot.off{background:var(--critical);}

/* hero */
.ag-eyebrow{font-size:.74rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:.55rem;}
.ag-hero h1{font-size:2.15rem;font-weight:700;margin:0 0 .45rem;color:var(--ink);line-height:1.15;letter-spacing:-0.025em;padding:0;}
.ag-hero p{color:var(--ink-2);font-size:1rem;max-width:780px;margin:0 0 1.3rem;line-height:1.6;}

/* section headings */
.ag-h2{font-size:1.05rem;font-weight:650;color:var(--ink);margin:1.7rem 0 .2rem;letter-spacing:-0.01em;}
.ag-sub{color:var(--muted);font-size:.84rem;margin:0 0 .85rem;line-height:1.5;}

/* streamlit widgets */
[data-testid="stForm"]{border:1px solid var(--line);border-radius:16px;background:var(--surface);padding:18px 18px 6px;}
[data-testid="stTextInput"] [data-baseweb="input"]{border-radius:12px;background:var(--raised);border:1px solid var(--line-2);}
[data-testid="stTextInput"] input{font-size:1.06rem;padding:15px 16px;color:var(--ink);}
[data-testid="stBaseButton-primaryFormSubmit"],[data-testid="stBaseButton-primary"]{background:var(--ink);color:#0b0d10;border:none;
font-weight:600;border-radius:10px;min-height:2.75rem;}
[data-testid="stBaseButton-primaryFormSubmit"]:hover,[data-testid="stBaseButton-primary"]:hover{background:#ffffff;color:#0b0d10;}
[data-testid="stBaseButton-primaryFormSubmit"] p,[data-testid="stBaseButton-primary"] p{color:#0b0d10;font-weight:600;}
[data-baseweb="tab-list"]{gap:4px;border-bottom:1px solid var(--line);}
button[data-baseweb="tab"]{padding:10px 14px;}
button[data-baseweb="tab"] p{font-weight:500;color:var(--muted);font-size:.92rem;}
button[data-baseweb="tab"][aria-selected="true"] p{color:var(--ink);}
[data-baseweb="tab-highlight"]{background:var(--ink) !important;}
[data-testid="stExpander"] details{border:1px solid var(--line);border-radius:12px;background:var(--surface);}
[data-testid="stDataFrame"]{font-variant-numeric:tabular-nums;}
[data-testid="stGraphVizChart"]{display:flex;justify-content:center;}
[data-testid="stGraphVizChart"] svg{max-width:100%;height:auto;}
[data-testid="stWidgetLabel"] p{color:var(--muted);font-size:.8rem;}

/* cards */
.ag-card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:18px 20px;}

/* KPI tiles */
.ag-kpi{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px 18px 15px;margin-bottom:12px;}
.ag-kpi .name{display:flex;align-items:center;gap:8px;font-size:.86rem;font-weight:600;color:var(--ink);}
.ag-sw{width:10px;height:10px;border-radius:3px;flex:none;display:inline-block;}
.ag-kpi .desc{font-size:.76rem;color:var(--muted);margin-top:3px;min-height:2.9em;line-height:1.45;}
.ag-kpi .val{font-size:2.35rem;font-weight:700;color:var(--ink);margin:.35rem 0 0;letter-spacing:-0.03em;line-height:1.1;}
.ag-kpi .val small{font-size:.8rem;color:var(--muted);font-weight:500;margin-left:6px;letter-spacing:0;}
.ag-meter{height:4px;background:rgba(255,255,255,0.07);border-radius:4px;overflow:hidden;margin:.6rem 0 .7rem;}
.ag-meter>span{display:block;height:100%;border-radius:4px;}
.ag-kpi .sub{font-size:.78rem;color:var(--ink-2);line-height:1.55;}
.ag-kpi .sub b{color:var(--ink);font-weight:600;}

/* headline band */
.ag-band{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));background:var(--surface);border:1px solid var(--line);
border-radius:16px;margin:.3rem 0 1.2rem;}
.ag-band>div{padding:18px 22px;border-left:1px solid var(--line);}
.ag-band>div:first-child{border-left:none;}
.ag-band .lbl{font-size:.8rem;color:var(--muted);display:flex;gap:8px;align-items:center;}
.ag-band .num{font-size:2.7rem;font-weight:700;color:var(--ink);letter-spacing:-0.035em;line-height:1.1;margin-top:.3rem;}
.ag-band .cap{font-size:.8rem;color:var(--ink-2);margin-top:.3rem;}
.ag-up{color:var(--good);}
@media (max-width:760px){.ag-band{grid-template-columns:1fr;}.ag-band>div{border-left:none;border-top:1px solid var(--line);}
.ag-band>div:first-child{border-top:none;}}

/* answer */
.ag-answer{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:20px 24px 20px 26px;position:relative;overflow:hidden;}
.ag-answer:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--accent);}
.ag-answer .meta{display:flex;align-items:center;gap:8px;font-size:.8rem;color:var(--muted);margin-bottom:.7rem;flex-wrap:wrap;}
.ag-answer .meta b{color:var(--ink);font-weight:600;}
.ag-answer .q{font-size:.9rem;color:var(--ink-2);margin-bottom:.4rem;}
.ag-answer .headline{font-size:1.65rem;font-weight:700;color:var(--ink);line-height:1.25;letter-spacing:-0.02em;margin-bottom:.6rem;}
.ag-answer .body{font-size:.97rem;color:var(--ink-2);line-height:1.7;}
.ag-cite{display:inline-flex;align-items:center;font-family:'JetBrains Mono',monospace;font-size:.7rem;padding:1px 7px;margin:0 2px;
border-radius:6px;border:1px solid var(--line-2);color:var(--ink) !important;background:var(--raised);text-decoration:none !important;
vertical-align:1px;white-space:nowrap;}
a.ag-cite:hover{border-color:var(--ink-2);}

/* stat strip */
.ag-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0 6px;}
.ag-stat{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:11px 15px;}
.ag-stat .l{font-size:.74rem;color:var(--muted);}
.ag-stat .v{font-size:1.3rem;font-weight:650;color:var(--ink);margin-top:2px;letter-spacing:-0.01em;}
@media (max-width:760px){.ag-stats{grid-template-columns:repeat(2,minmax(0,1fr));}}

/* timeline */
.ag-steps{position:relative;padding-left:28px;margin-top:6px;}
.ag-steps:before{content:"";position:absolute;left:8px;top:8px;bottom:14px;width:2px;background:var(--line-2);}
.ag-step{position:relative;margin-bottom:18px;}
.ag-step:before{content:"";position:absolute;left:-25px;top:4px;width:12px;height:12px;border-radius:50%;background:var(--page);
border:2px solid var(--ink-2);}
.ag-step.final:before{background:var(--accent);border-color:var(--accent);}
.ag-step .t{font-weight:600;color:var(--ink);font-size:.93rem;display:flex;gap:9px;align-items:baseline;}
.ag-step .t .n{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--muted);font-weight:500;}
.ag-step .m{color:var(--muted);font-size:.77rem;margin-top:3px;line-height:1.5;}
.ag-step .r{color:var(--ink);font-size:.84rem;margin-top:6px;line-height:1.5;padding:7px 10px;background:var(--raised);
border:1px solid var(--line);border-radius:8px;}
.ag-step .d{color:var(--ink-2);font-size:.82rem;line-height:1.55;margin-top:6px;font-style:italic;}
.ag-chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px;}
.ag-chip{font-family:'JetBrains Mono',monospace;font-size:.7rem;padding:2px 7px;border-radius:6px;background:var(--raised);
border:1px solid var(--line);color:var(--ink-2);}
.ag-tag{font-size:.68rem;font-weight:600;letter-spacing:.05em;text-transform:uppercase;padding:2px 8px;border-radius:999px;
border:1px solid var(--line-2);color:var(--ink-2);white-space:nowrap;}

/* evidence */
.ag-ev{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 15px;margin-bottom:10px;}
.ag-ev.cited{border-color:var(--accent);}
.ag-ev .h{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;}
.ag-ev .title{font-weight:600;font-size:.88rem;color:var(--ink);line-height:1.4;}
.ag-ev .title a{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--line-2);}
.ag-ev .txt{color:var(--ink-2);font-size:.8rem;line-height:1.55;margin-top:6px;}
.ag-ev .prov{color:var(--muted);font-size:.74rem;margin-top:7px;}

/* explorer */
.ag-res{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:15px 17px;margin-bottom:8px;}
.ag-res .hd{display:flex;justify-content:space-between;align-items:center;gap:8px;}
.ag-res .nm{display:flex;align-items:center;gap:8px;font-weight:600;font-size:.86rem;color:var(--ink);}
.ag-res .sa{font-size:1.02rem;font-weight:650;color:var(--ink);margin:.55rem 0 .3rem;line-height:1.35;}
.ag-res .an{font-size:.84rem;color:var(--ink-2);line-height:1.6;}
.ag-res .mt{font-size:.74rem;color:var(--muted);margin-top:.6rem;}
.ag-ok{color:var(--good);font-weight:600;font-size:.76rem;white-space:nowrap;}
.ag-bad{color:#e66767;font-weight:600;font-size:.76rem;white-space:nowrap;}
.ag-na{color:var(--muted);font-weight:500;font-size:.76rem;white-space:nowrap;}
.ag-qcard{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:18px 22px;margin:.4rem 0 1rem;}
.ag-qcard .qt{font-size:1.15rem;font-weight:650;color:var(--ink);line-height:1.45;margin:.5rem 0 .7rem;}
.ag-qcard .ref{font-size:.88rem;color:var(--ink-2);}
.ag-qcard .ref b{color:var(--ink);}
</style>
"""

LOGO = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
    '<circle cx="5" cy="6" r="2.6" stroke="#f0efec" stroke-width="1.6"/>'
    '<circle cx="19" cy="6" r="2.6" stroke="#f0efec" stroke-width="1.6"/>'
    '<circle cx="12" cy="18" r="2.6" fill="#d55181" stroke="#d55181" stroke-width="1.6"/>'
    '<path d="M7.4 7.2 10.6 15.8M16.6 7.2 13.4 15.8M7.6 6h8.8" stroke="#898781" stroke-width="1.4" stroke-linecap="round"/>'
    "</svg>"
)


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def md(html_text: str) -> None:
    """Render raw HTML through st.markdown. Blank lines would end the HTML block, so strip them."""
    st.markdown(re.sub(r"\n\s*\n", "\n", html_text), unsafe_allow_html=True)


def heading(title: str, sub: str | None = None) -> None:
    md(f'<div class="ag-h2">{esc(title)}</div>' + (f'<div class="ag-sub">{esc(sub)}</div>' if sub else ""))


def swatch(key: str) -> str:
    return f'<span class="ag-sw" style="background:{PIPES[key]["color"]}"></span>'


def fmt_int(n) -> str:
    try:
        return f"{int(round(float(n))):,}"
    except (TypeError, ValueError):
        return "–"


# --------------------------------------------------------------------------- tigergraph

@st.cache_resource(show_spinner=False)
def tg_conn():
    from src.common.tg_conn import get_connection

    return get_connection()


@st.cache_data(ttl=900, show_spinner=False)
def graph_stats() -> dict:
    try:
        conn = tg_conn()
        edges = {e: conn.getEdgeCount(e) for e in conn.getEdgeTypes()}
        queries = sorted({q.rstrip("/").split("/")[-1] for q in conn.getInstalledQueries()})
        return {"ok": True, "graph": conn.graphname, "vertices": conn.getVertexCount("*"), "edges": edges, "queries": queries}
    except Exception as exc:  # the console still renders without a graph
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


@st.cache_data(ttl=3600, show_spinner=False)
def doc_meta(ids: tuple) -> dict:
    if not ids:
        return {}
    try:
        rows = tg_conn().getVerticesById("Document", list(ids))
        return {r["v_id"]: r["attributes"] for r in rows}
    except Exception:
        return {}


def run_pipeline(key: str, question: str) -> dict:
    from src.common.token_tracker import TokenTracker

    module = importlib.import_module(f"src.pipelines.{key}.pipeline")
    tracker = TokenTracker()
    started = time.time()
    try:
        result, error = module.answer_question(tg_conn(), question, tracker=tracker, question_id="live"), None
    except Exception as exc:
        result, error = {}, f"{type(exc).__name__}: {exc}"
    elapsed = time.time() - started
    totals = tracker.totals_for("live")
    records = tracker.all_records()
    return {
        "key": key,
        "question": question,
        "result": result or {},
        "error": error,
        "elapsed": elapsed,
        "tokens": totals.get("total_tokens", 0),
        "gemini_calls": sum(1 for r in records if r.get("call_type") != "embedding"),
    }


# --------------------------------------------------------------------------- answer rendering

CITE_RE = re.compile(r"\[([A-Za-z0-9_\-]{2,90}(?:\s*[,;]\s*[A-Za-z0-9_\-]{2,90})*)\]")


def cited_ids(text: str) -> set:
    out = set()
    for m in CITE_RE.finditer(text or ""):
        out.update(p.strip() for p in re.split(r"[,;]", m.group(1)))
    return out


def answer_html(text: str, urls: dict) -> str:
    """Escape the answer, then turn [citation] markers into linked chips."""
    out = esc(text)

    def chip(match):
        chips = []
        for cid in (p.strip() for p in re.split(r"[,;]", match.group(1))):
            url = urls.get(cid) or urls.get(cid.split("_c")[0])
            label = cid if len(cid) <= 22 else cid[:20] + "…"
            if url:
                chips.append(f'<a class="ag-cite" href="{esc(url)}" target="_blank" title="{esc(cid)}">{esc(label)}</a>')
            else:
                chips.append(f'<span class="ag-cite" title="{esc(cid)}">{esc(label)}</span>')
        return "".join(chips)

    out = CITE_RE.sub(chip, out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = out.replace("**", "")  # an unpaired marker left by truncation
    out = re.sub(r"(?m)^\s*[\*\-]\s+", "• ", out)
    return out.replace("\n", "<br>")


def evidence_urls(res: dict) -> dict:
    urls = {}
    for e in res.get("evidence") or []:
        if not isinstance(e, dict):
            continue
        cid = e.get("citation_id") or e.get("event_id")
        if cid and e.get("source_url"):
            urls[cid] = e["source_url"]
    docs = doc_meta(tuple(res.get("retrieved_doc_ids") or []))
    for doc_id, attrs in docs.items():
        urls.setdefault(doc_id, attrs.get("url"))
    return urls


def param_chips(step: dict) -> list:
    chips = []
    for field in ("event_query", "fact_query"):
        spec = step.get(field)
        if isinstance(spec, dict):
            chips += [f"{k}={v}" for k, v in spec.items() if v not in (None, "", [])]
    if step.get("query"):
        chips.append(f'"{step["query"]}"')
    if step.get("entity_ids"):
        chips += [str(e) for e in step["entity_ids"][:6]]
    return chips


def steps_for(key: str, res: dict) -> list:
    """A uniform list of steps for any pipeline, so every answer shows how it was reached."""
    trace = res.get("trace") or []
    steps = []
    if key in ("investigator", "agentic") and trace:
        for s in trace:
            act = s.get("action") or "?"
            name, sub = TOOLS.get(act, (act, ""))
            meta = []
            if s.get("new_evidence") is not None:
                meta.append(f"+{s['new_evidence']} evidence")
            if s.get("tool_latency_sec") is not None:
                meta.append(f"{s['tool_latency_sec']:.2f}s in TigerGraph")
            steps.append({
                "title": name, "sub": sub, "chips": param_chips(s), "result": s.get("tool_result"),
                "detail": s.get("evidence_check") or s.get("reasoning"), "meta": meta, "final": act == "answer",
            })
    elif key == "event_graph":
        plan = res.get("plan") or {}
        chips = [f"{k}={v}" for k, v in plan.items() if v not in (None, "", [], False) and k != "reasoning"]
        steps.append({"title": "Plan the query", "sub": "one Gemini call turns the question into a typed plan", "chips": chips})
        if res.get("route") == "fallback_rag":
            steps.append({"title": "Graph could not answer", "sub": "fell back to the RAG pipeline"})
        else:
            n = len(res.get("evidence") or [])
            steps.append({"title": "GSQL on the event layer",
                          "sub": f"installed query {EVENT_OP_QUERY.get(plan.get('operation'), 'events_*')}",
                          "meta": [f"{n} matching event vertices"]})
        steps.append({"title": "Answer", "sub": "templated from the matched vertices, no second model call", "final": True})
    elif key == "rag":
        steps += [
            {"title": "Embed the question", "sub": "local BGE model, 768 dimensions"},
            {"title": "Vector search", "sub": "installed query vector_search_chunks over Chunk.embedding, then rerank"},
            {"title": "Answer", "sub": "one Gemini call over the top chunks", "final": True},
        ]
    elif key == "graphrag":
        steps += [
            {"title": "Entity linking", "sub": "installed query vector_search_entities"},
            {"title": "Graph traversal", "sub": "installed query entity_neighbors_1hop (RELATED_TO, MENTIONS)"},
            {"title": "Answer", "sub": "one Gemini call over the facts and chunks found", "final": True},
        ]
    return steps


def steps_html(steps: list, accent: str) -> str:
    parts = [f'<div class="ag-steps" style="--accent:{accent}">']
    for i, s in enumerate(steps, 1):
        parts.append(f'<div class="ag-step{" final" if s.get("final") else ""}">')
        parts.append(f'<div class="t"><span class="n">{i:02d}</span>{esc(s["title"])}</div>')
        if s.get("sub"):
            parts.append(f'<div class="m">{esc(s["sub"])}</div>')
        if s.get("chips"):
            parts.append('<div class="ag-chips">' + "".join(f'<span class="ag-chip">{esc(c)}</span>' for c in s["chips"]) + "</div>")
        if s.get("result"):
            parts.append(f'<div class="r">{esc(str(s["result"])[:280])}</div>')
        if s.get("detail"):
            parts.append(f'<div class="d">{esc(str(s["detail"])[:320])}</div>')
        if s.get("meta"):
            parts.append(f'<div class="m">{" · ".join(esc(m) for m in s["meta"])}</div>')
        parts.append("</div>")
    parts.append("</div>")
    return "".join(parts)


def evidence_items(key: str, res: dict) -> list:
    """Normalize every pipeline's evidence to {id, kind, title, url, text, prov}."""
    out = []
    raw = res.get("evidence") or []
    if key == "event_graph":
        docs = doc_meta(tuple(e.get("event_id") for e in raw if isinstance(e, dict)))
        for e in raw:
            bits = [e.get("venue"), e.get("date_text"),
                    f"{e['competitors']} competitors" if (e.get("competitors") or -1) >= 0 else None,
                    f"{e['nations']} nations" if (e.get("nations") or -1) >= 0 else None,
                    f"gold: {e['gold']}" if e.get("gold") else None]
            out.append({"id": e.get("event_id"), "kind": "OlympicEvent vertex", "title": e.get("title"),
                        "url": (docs.get(e.get("event_id")) or {}).get("url"),
                        "text": " · ".join(b for b in bits if b), "prov": "events_* GSQL query"})
        return out
    if raw:
        kinds = {"event": "OlympicEvent vertex", "chunk": "Chunk · vector match", "fact": "TemporalFact vertex"}
        for e in raw:
            if not isinstance(e, dict):
                continue
            prov = e.get("provenance") or {}
            params = prov.get("params") or {}
            prov_txt = " · ".join(str(x) for x in (prov.get("tool"), prov.get("operation") or prov.get("query")) if x)
            if params.get("text"):
                prov_txt += f' · "{params["text"]}"'
            out.append({"id": e.get("citation_id"), "kind": kinds.get(e.get("source"), e.get("source") or "evidence"),
                        "title": e.get("doc_title") or e.get("doc_id"), "url": e.get("source_url"),
                        "text": str(e.get("text") or "")[:320], "prov": prov_txt, "tool": prov.get("tool")})
        return out
    docs = doc_meta(tuple(res.get("retrieved_doc_ids") or []))
    for doc_id in res.get("retrieved_doc_ids") or []:
        attrs = docs.get(doc_id) or {}
        out.append({"id": doc_id, "kind": "Document", "title": attrs.get("title") or doc_id, "url": attrs.get("url"),
                    "text": "", "prov": "retrieved by vector search"})
    return out


def evidence_cards_html(items: list, cited: set, accent: str) -> str:
    parts = []
    for it in items:
        is_cited = it["id"] in cited or (it["id"] or "").split("_c")[0] in cited
        title = esc(it["title"])
        if it.get("url"):
            title = f'<a href="{esc(it["url"])}" target="_blank">{title}</a>'
        parts.append(
            f'<div class="ag-ev{" cited" if is_cited else ""}" style="--accent:{accent}"><div class="h">'
            f'<div class="title">{title}</div><span class="ag-tag">{esc(it["kind"])}</span></div>'
            + (f'<div class="txt">{esc(it["text"])}</div>' if it.get("text") else "")
            + f'<div class="prov"><span class="mono">{esc(it["id"])}</span>'
            + (f' · {esc(it["prov"])}' if it.get("prov") else "")
            + (" · <b style='color:var(--ink)'>cited in the answer</b>" if is_cited else "")
            + "</div></div>"
        )
    return "".join(parts)


def _wrap(text: str, width: int = 26, lines: int = 3) -> str:
    chunks = textwrap.wrap(str(text or ""), width) or [""]
    if len(chunks) > lines:
        chunks = chunks[:lines]
        chunks[-1] = chunks[-1][: width - 1] + "…"
    return "<br/>".join(html.escape(c) for c in chunks)


def evidence_dot(key: str, res: dict, steps: list, items: list, cited: set) -> str:
    accent = PIPES[key]["color"]
    answer_ink = "#0b0b0b" if key == "event_graph" else "#ffffff"
    lines = [
        "digraph G {",
        'graph [bgcolor="transparent", rankdir=LR, pad="0.2", nodesep="0.22", ranksep="0.65", fontname="Inter"];',
        f'node [shape=box, style="rounded,filled", fillcolor="{INK["raised"]}", color="{INK["node_line"]}", '
        f'fontcolor="{INK["primary"]}", fontname="Inter", fontsize=12, penwidth=1, margin="0.18,0.09"];',
        f'edge [color="{INK["node_line"]}", arrowsize=0.55, penwidth=1];',
    ]
    q = res.get("_question") or "Question"
    lines.append(f'q [label=<<font color="{INK["muted"]}" point-size="8">QUESTION</font><br/>{_wrap(q, 30)}>, fillcolor="#1d2128"];')
    answer = res.get("short_answer") or "Answer"
    lines.append(f'ans [label=<<font point-size="8">ANSWER</font><br/><b>{_wrap(answer, 24)}</b>>, fillcolor="{accent}", '
                 f'color="{accent}", fontcolor="{answer_ink}"];')

    tool_steps = [s for s in steps if not s.get("final")]
    prev = "q"
    tool_ids = {}
    for i, s in enumerate(tool_steps):
        sid = f"s{i}"
        sub = s["chips"][0] if s.get("chips") else ""
        label = f"<b>{html.escape(s['title'])}</b>" + (f'<br/><font color="{INK["muted"]}" point-size="8">{_wrap(sub, 28, 1)}</font>' if sub else "")
        lines.append(f"{sid} [label=<{label}>];")
        lines.append(f"{prev} -> {sid};")
        prev = sid
        tool_ids.setdefault(s["title"], sid)

    def anchor_for(item):
        tool = item.get("tool")
        if tool and TOOLS.get(tool, (None,))[0] in tool_ids:
            return tool_ids[TOOLS[tool][0]]
        return prev

    shown = items[:9]
    any_cited = False
    for j, it in enumerate(shown):
        eid = f"e{j}"
        is_cited = it["id"] in cited or (it["id"] or "").split("_c")[0] in cited or key == "event_graph"
        any_cited |= is_cited
        style = f'color="{accent}", penwidth=1.6' if is_cited else f'fontcolor="{INK["secondary"]}", fillcolor="{INK["surface"]}"'
        kind = it["kind"].split(" ")[0]
        lines.append(f'{eid} [label=<<font color="{INK["muted"]}" point-size="8">{html.escape(kind.upper())}</font><br/>'
                     f'{_wrap(it["title"], 26, 2)}>, {style}];')
        lines.append(f"{anchor_for(it)} -> {eid};")
        if is_cited:
            lines.append(f'{eid} -> ans [color="{accent}", penwidth=1.3];')
    if len(items) > len(shown):
        lines.append(f'more [label="+{len(items) - len(shown)} more", fontcolor="{INK["muted"]}", fillcolor="{INK["surface"]}", style="rounded,dashed"];')
        lines.append(f"{prev} -> more;")
    if not any_cited:
        lines.append(f'{prev} -> ans [color="{accent}"];')
    lines.append("}")
    return "\n".join(lines)


def stats_html(stats: list) -> str:
    return '<div class="ag-stats">' + "".join(
        f'<div class="ag-stat"><div class="l">{esc(label)}</div><div class="v">{esc(value)}</div></div>' for label, value in stats
    ) + "</div>"


def graph_query_count(key: str, res: dict) -> int:
    trace = res.get("trace") or []
    if key in ("investigator", "agentic"):
        return sum(1 for s in trace if s.get("action") and s["action"] != "answer")
    return {"rag": 1, "graphrag": 2, "event_graph": 1}.get(key, 0)


def render_run(run: dict, full: bool = True) -> None:
    key, res = run["key"], dict(run["result"])
    res["_question"] = run["question"]
    pipe = PIPES[key]
    if run["error"]:
        st.error(f"{pipe['short']} failed: {run['error']}")
        return
    accent = pipe["color"]
    urls = evidence_urls(res)
    cited = cited_ids(res.get("answer", ""))
    headline = res.get("short_answer")
    md(
        f'<div class="ag-answer" style="--accent:{accent}">'
        f'<div class="meta">{swatch(key)}<b>{esc(pipe["short"])}</b><span>·</span><span>{esc(pipe["blurb"])}</span></div>'
        f'<div class="q">{esc(run["question"])}</div>'
        + (f'<div class="headline">{esc(headline)}</div>' if headline else "")
        + f'<div class="body">{answer_html(res.get("answer", ""), urls)}</div></div>'
    )
    steps = steps_for(key, res)
    md(stats_html([
        ("Time", f"{run['elapsed']:.1f} s"),
        ("Gemini calls", str(run["gemini_calls"])),
        ("Tokens", fmt_int(run["tokens"])),
        ("Graph / vector queries", str(graph_query_count(key, res))),
    ]))
    if not full:
        return
    items = evidence_items(key, res)
    heading("Evidence path", "From the question, through the TigerGraph queries, to the vertices the answer cites.")
    with st.container(border=True):
        st.graphviz_chart(evidence_dot(key, res, steps, items, cited), width="content")
    left, right = st.columns([1, 1.1], gap="large")
    with left:
        heading("How it was answered", "Each step the pipeline took, with the parameters it chose.")
        md(steps_html(steps, accent))
    with right:
        if items:
            heading(f"Evidence ({len(items)})", "Outlined cards are cited in the answer; titles link to the source article.")
            ordered = sorted(items, key=lambda it: not (it["id"] in cited or (it["id"] or "").split("_c")[0] in cited))
            md(evidence_cards_html(ordered[:6], cited, accent))
            if len(ordered) > 6:
                with st.expander(f"{len(ordered) - 6} more evidence items"):
                    md(evidence_cards_html(ordered[6:], cited, accent))


def render_compare(runs: dict) -> None:
    heading("Side by side", "The same question through every pipeline that runs on Gemini.")
    keys = [k for k in COMPARE_ORDER if k in runs]
    cols = st.columns(3, gap="medium")
    for i, key in enumerate(keys):
        run, pipe = runs[key], PIPES[key]
        res = run["result"]
        with cols[i % 3]:
            if run["error"]:
                st.error(f"{pipe['short']}: {run['error']}")
                continue
            body = res.get("answer", "")
            short = res.get("short_answer")
            md(
                f'<div class="ag-res"><div class="hd"><div class="nm">{swatch(key)}{esc(pipe["short"])}</div>'
                f'<span class="ag-na">{run["elapsed"]:.1f} s</span></div>'
                + (f'<div class="sa">{esc(short)}</div>' if short else "")
                + f'<div class="an">{answer_html(body[:420] + ("…" if len(body) > 420 else ""), evidence_urls(res))}</div>'
                + f'<div class="mt">{run["gemini_calls"]} Gemini calls · {fmt_int(run["tokens"])} tokens · '
                + f'{graph_query_count(key, res)} graph/vector queries</div></div>'
            )
            with st.expander("Steps and evidence"):
                render_run(run, full=True)
    table = pd.DataFrame([{
        "Pipeline": PIPES[k]["short"],
        "Answer": runs[k]["result"].get("short_answer") or (runs[k]["result"].get("answer") or "")[:120],
        "Seconds": round(runs[k]["elapsed"], 1),
        "Gemini calls": runs[k]["gemini_calls"],
        "Tokens": runs[k]["tokens"],
    } for k in keys if not runs[k]["error"]])
    if not table.empty:
        heading("Cost of each answer")
        st.dataframe(table, hide_index=True, width="stretch", column_config={
            "Tokens": st.column_config.ProgressColumn("Tokens", format="%d", min_value=0, max_value=int(table["Tokens"].max() or 1)),
            "Seconds": st.column_config.NumberColumn(format="%.1f s"),
        })


# --------------------------------------------------------------------------- pages


def topbar() -> None:
    stats = graph_stats()
    if stats.get("ok"):
        v = stats["vertices"]
        status = (f'<span class="ag-dot"></span>TigerGraph Savanna · graph <b>{esc(stats["graph"])}</b> · '
                  f'{fmt_int(v.get("Document", 0))} docs · {fmt_int(v.get("Entity", 0))} entities · '
                  f'{fmt_int(v.get("OlympicEvent", 0))} events')
    else:
        status = '<span class="ag-dot off"></span>TigerGraph unreachable · check TG_HOST / TG_SECRET in .env'
    md(f'<div class="ag-top"><div class="ag-brand">{LOGO}Agentic GraphRAG <small>console</small></div>'
       f'<div class="ag-pill">{status}</div></div>')


def page_ask() -> None:
    md('<div class="ag-hero"><div class="ag-eyebrow">Live · TigerGraph + Gemini 3.1 Flash-Lite</div>'
       "<h1>Ask the knowledge graph</h1>"
       "<p>Every question runs live. Gemini plans the lookup, TigerGraph answers it, and each answer links back "
       "to the graph vertex and Wikipedia article it came from. The corpus covers Olympic events, venues and "
       "medalists, plus office holders and some films.</p></div>")

    st.session_state.setdefault("history", [])

    def use_example():
        picked = st.session_state.get("ex_pick")
        if picked:
            st.session_state["ask_q"] = picked
            st.session_state["ask_pending"] = True
            st.session_state["ex_pick"] = None

    with st.form("ask_form"):
        st.text_input("Question", key="ask_q", label_visibility="collapsed",
                      placeholder="e.g. Who won gold at Richmond Olympic Oval on 14 February 2010?")
        c1, c2 = st.columns([5, 1.25], vertical_alignment="center")
        with c1:
            st.segmented_control(
                "Pipeline", options=[*LIVE_PIPES, "compare"], default="investigator", required=True, key="ask_mode",
                format_func=lambda k: "Compare all five" if k == "compare" else PIPES[k]["short"],
                label_visibility="collapsed",
            )
        with c2:
            submitted = st.form_submit_button("Ask the graph", type="primary", icon=":material/arrow_forward:", width="stretch")
    st.pills("Try an example", EXAMPLES, key="ex_pick", on_change=use_example)

    pending = st.session_state.pop("ask_pending", False)
    question = (st.session_state.get("ask_q") or "").strip()
    if (submitted or pending) and question:
        if not graph_stats().get("ok"):
            st.error("TigerGraph is unreachable, so live questions cannot run. Check TG_HOST and TG_SECRET in .env.")
            return
        mode = st.session_state.get("ask_mode") or "investigator"
        runs = {}
        if mode == "compare":
            with st.status("Running all five pipelines…", expanded=True) as status:
                for key in COMPARE_ORDER:
                    status.update(label=f"Running {PIPES[key]['short']}…")
                    runs[key] = run_pipeline(key, question)
                    st.write(f"{PIPES[key]['short']}: {runs[key]['elapsed']:.1f} s")
                status.update(label="All five pipelines answered", state="complete", expanded=False)
        else:
            with st.spinner(f"{PIPES[mode]['short']} is querying TigerGraph…"):
                runs[mode] = run_pipeline(mode, question)
        st.session_state["history"].insert(0, {"question": question, "mode": mode, "runs": runs, "at": time.strftime("%H:%M")})

    history = st.session_state["history"]
    if not history:
        md('<div class="ag-sub" style="margin-top:1rem">Pick an example above or type your own question. '
           "Use <b>Compare all five</b> to see why the graph-backed pipelines get counting questions right.</div>")
        return
    latest = history[0]
    st.write("")
    if latest["mode"] == "compare":
        render_compare(latest["runs"])
    else:
        render_run(next(iter(latest["runs"].values())))
    if len(history) > 1:
        heading("Earlier in this session")
        for item in history[1:8]:
            label = "Compare all five" if item["mode"] == "compare" else PIPES[item["mode"]]["short"]
            with st.expander(f"{item['at']} · {label} · {item['question']}"):
                if item["mode"] == "compare":
                    render_compare(item["runs"])
                else:
                    render_run(next(iter(item["runs"].values())), full=False)


# ----------------------------------------------------------------- benchmark helpers

SOURCES = {
    "submitted": ("Submitted by the team", bench.results_path()),
    "repro": ("Our reproduction", _ROOT / "data" / "results" / "repro_public.jsonl"),
}


@st.cache_data(show_spinner="Loading benchmark results…")
def load_bench(path_str: str, _mtime: float):
    frame, stats = bench.load_results(Path(path_str))
    if not frame.empty:
        present = [k for k in bench.PIPELINES if k in set(frame["pipeline"])]
        frame["pipe"] = pd.Categorical(frame["pipeline"].map(lambda k: PIPES.get(k, {}).get("short", k)),
                                       categories=[PIPES[k]["short"] for k in present], ordered=True)
    return frame, stats


def chart_layout(fig: go.Figure, *, height: int = 340, legend: bool = False, title: str = "") -> go.Figure:
    fig.update_layout(
        template="none", height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", size=12, color=INK["secondary"]),
        margin=dict(l=8, r=20, t=44 if title else 12, b=8), showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text="", font=dict(color=INK["secondary"], size=11)),
        hoverlabel=dict(bgcolor="#1d2128", bordercolor="#3a404a", font=dict(family="Inter", size=12, color=INK["primary"])),
        bargap=0.4, bargroupgap=0.08,
    )
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=14, color=INK["primary"]), x=0, xanchor="left", y=0.98))
    fig.update_xaxes(showgrid=False, linecolor=INK["axis"], ticks="outside", tickcolor=INK["axis"], color=INK["muted"],
                     zeroline=False, automargin=True)
    fig.update_yaxes(showgrid=True, gridcolor=INK["grid"], zeroline=False, showline=False, color=INK["muted"], automargin=True)
    fig.update_traces(marker_cornerradius=4, selector=dict(type="bar"))
    return fig


def show(fig: go.Figure, key: str) -> None:
    st.plotly_chart(fig, key=key, theme=None, config={"displayModeBar": False})


def present_keys(view: pd.DataFrame) -> list:
    return [k for k in bench.PIPELINES if k in set(view["pipeline"])]


def exact_match_bars(view: pd.DataFrame) -> go.Figure:
    s = view.groupby("pipeline")["exact_match"].agg(["mean", "sum", "count"]).reset_index().sort_values("mean")
    names = [PIPES[k]["short"] for k in s["pipeline"]]
    fig = go.Figure(go.Bar(
        x=s["mean"] * 100, y=names, orientation="h", width=0.56,
        marker=dict(color=[PIPES[k]["color"] for k in s["pipeline"]], line=dict(width=0)),
        text=[f"{m:.0%}" for m in s["mean"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=INK["primary"], size=12),
        customdata=s[["sum", "count"]].to_numpy(),
        hovertemplate="<b>%{y}</b><br>%{x:.0f}% exact match (%{customdata[0]:.0f} of %{customdata[1]:.0f})<extra></extra>",
    ))
    chart_layout(fig, height=300, title="Exact match against the gold answer")
    fig.update_xaxes(range=[0, 112], ticksuffix="%", dtick=25, showgrid=True, gridcolor=INK["grid"], ticks="", showline=False)
    fig.update_yaxes(showgrid=False, ticks="", color=INK["secondary"])
    return fig


def emphasis_scatter(view: pd.DataFrame, x_field: str, y_field: str, *, x_title: str, y_title: str, title: str,
                     y_pct: bool = True, x_fmt: str = ",.0f") -> go.Figure:
    """Six hues cannot all be told apart on a scatter, so gray all but the agent and label every point."""
    s = view.groupby("pipeline").agg(x=(x_field, "mean"), y=(y_field, "mean")).reset_index().dropna()
    s["name"] = s["pipeline"].map(lambda k: PIPES[k]["short"])
    yv = s["y"] * (100 if y_pct else 1)
    xr = (s["x"].max() - s["x"].min()) or 1
    yr = (yv.max() - yv.min()) or 1
    # Label placement: a name is ~25% of the plot wide, so neighbors closer than that alternate above/below,
    # and points near either edge anchor their label inward so it is never clipped.
    xmin, xmax = s["x"].min(), s["x"].max()
    positions, placed = [], []
    order = sorted(range(len(s)), key=lambda i: s["x"].iloc[i])
    pos_by_index = {}
    for i in order:
        xi, yi = s["x"].iloc[i], yv.iloc[i]
        crowded = [p for (px, py, p) in placed if abs(xi - px) / xr < 0.32 and abs(yi - py) / yr < 0.15]
        vertical = "bottom" if crowded and crowded[-1].startswith("top") else "top"
        frac = (xi - xmin) / xr
        horizontal = "left" if frac > 0.82 else ("right" if frac < 0.12 else "center")
        pos = f"{vertical} {horizontal}"
        pos_by_index[i] = pos
        placed.append((xi, yi, pos))
    positions = [pos_by_index[i] for i in range(len(s))]
    colors = [PIPES[k]["color"] if k == AGENT else "#5d6068" for k in s["pipeline"]]
    fig = go.Figure(go.Scatter(
        x=s["x"], y=yv, mode="markers+text", text=s["name"], textposition=positions, cliponaxis=False,
        marker=dict(size=15, color=colors, line=dict(width=2, color=INK["page"])),
        textfont=dict(color=INK["secondary"], size=11),
        hovertemplate="<b>%{text}</b><br>" + x_title + ": %{x:" + x_fmt + "}<br>" + y_title + ": %{y:.1f}"
                      + ("%" if y_pct else "") + "<extra></extra>",
    ))
    chart_layout(fig, height=330, title=title)
    fig.update_xaxes(title=dict(text=x_title, font=dict(size=11, color=INK["muted"])), rangemode="tozero", showgrid=True,
                     gridcolor=INK["grid"])
    pad = max(6, yr * 0.25) if y_pct else max(0.05, yr * 0.25)
    fig.update_yaxes(title=dict(text=y_title, font=dict(size=11, color=INK["muted"])),
                     range=[max(0, yv.min() - pad), (yv.max() + pad) if not y_pct else min(108, yv.max() + pad)],
                     ticksuffix="%" if y_pct else "")
    return fig


def qtype_heatmap(view: pd.DataFrame, qtypes: list) -> go.Figure:
    keys = present_keys(view)
    g = view.groupby(["pipeline", "qtype"], observed=True)["exact_match"].agg(["mean", "sum", "count"])
    z, labels = [], []
    for k in keys:
        row_z, row_t = [], []
        for qt in qtypes:
            if (k, qt) in g.index:
                m, s_, n = g.loc[(k, qt)]
                row_z.append(m * 100)
                row_t.append((m * 100, f"{m:.0%}", f"{s_:.0f}/{n:.0f}"))
            else:
                row_z.append(None)
                row_t.append(None)
        z.append(row_z)
        labels.append(row_t)
    xs = [bench.qtype_label(q) for q in qtypes]
    ys = [PIPES[k]["short"] for k in keys]
    fig = go.Figure(go.Heatmap(
        z=z, x=xs, y=ys, zmin=0, zmax=100, xgap=3, ygap=3,
        colorscale=[[i / (len(SEQ) - 1), c] for i, c in enumerate(SEQ)],
        colorbar=dict(title=dict(text="Exact match", font=dict(size=11, color=INK["muted"])), ticksuffix="%", thickness=10,
                      len=0.85, outlinewidth=0, tickfont=dict(color=INK["muted"], size=10)),
        hovertemplate="<b>%{y}</b> · %{x}<br>%{z:.0f}% exact match<extra></extra>",
    ))
    for yi, row in enumerate(labels):
        for xi, cell in enumerate(row):
            if cell is None:
                continue
            value, pct, frac = cell
            ink = "#0b0b0b" if value >= 72 else "#ffffff"
            fig.add_annotation(x=xs[xi], y=ys[yi], showarrow=False,
                               text=f"<b>{pct}</b><br><span style='font-size:10px'>{frac}</span>",
                               font=dict(color=ink, size=13, family="Inter"))
    chart_layout(fig, height=60 + 52 * len(keys), title="Exact match by question type")
    fig.update_xaxes(showgrid=False, ticks="", showline=False, side="top", color=INK["secondary"])
    fig.update_yaxes(showgrid=False, autorange="reversed", color=INK["secondary"])
    fig.update_layout(margin=dict(l=8, r=8, t=70, b=8))
    return fig


def grouped_bars(frame: pd.DataFrame, x: str, y: str, *, title: str, y_title: str, y_range=None, value_fmt=None) -> go.Figure:
    fig = go.Figure()
    for k in [k for k in bench.PIPELINES if k in set(frame["pipeline"])]:
        rows = frame[frame["pipeline"] == k]
        fig.add_trace(go.Bar(
            x=rows[x], y=rows[y], name=PIPES[k]["short"], marker=dict(color=PIPES[k]["color"], line=dict(width=0)),
            hovertemplate="<b>" + PIPES[k]["short"] + "</b><br>%{x}: %{y:" + (value_fmt or ".2f") + "}<extra></extra>",
        ))
    chart_layout(fig, height=360, legend=True, title=title)
    fig.update_layout(barmode="group", margin=dict(l=8, r=20, t=80, b=8), legend=dict(y=1.06))
    fig.update_yaxes(title=dict(text=y_title, font=dict(size=11, color=INK["muted"])), range=y_range)
    return fig


def box_chart(view: pd.DataFrame, field: str, *, title: str, y_title: str) -> go.Figure:
    """Horizontal boxes, so the pipeline names read level instead of at 45 degrees."""
    fig = go.Figure()
    for k in present_keys(view):
        rows = view[view["pipeline"] == k]
        fig.add_trace(go.Box(x=rows[field], name=PIPES[k]["short"], orientation="h", boxpoints=False, width=0.5,
                             line=dict(width=2, color=PIPES[k]["color"]), fillcolor="rgba(0,0,0,0)",
                             marker=dict(color=PIPES[k]["color"])))
    chart_layout(fig, height=330, title=title)
    fig.update_xaxes(title=dict(text=y_title, font=dict(size=11, color=INK["muted"])), rangemode="tozero", showgrid=True,
                     gridcolor=INK["grid"], ticks="", showline=False)
    fig.update_yaxes(showgrid=False, autorange="reversed", color=INK["secondary"])
    return fig


def kpi_tile(key: str, rows: pd.DataFrame, latency_field: str) -> str:
    em = rows["exact_match"].dropna()
    judged = rows["judge_mean"].dropna()
    pct = em.mean() if len(em) else None
    color = PIPES[key]["color"]
    val = f"{pct:.0%}" if pct is not None else "n/a"
    judge = f"judge <b>{judged.mean():.2f}</b> (n={len(judged)})" if len(judged) else "not judged"
    return (
        f'<div class="ag-kpi"><div class="name">{swatch(key)}{esc(PIPES[key]["short"])}</div>'
        f'<div class="desc">{esc(PIPES[key]["blurb"])}</div>'
        f'<div class="val">{val}<small>exact match · n={len(em)}</small></div>'
        f'<div class="ag-meter"><span style="width:{(pct or 0) * 100:.1f}%;background:{color}"></span></div>'
        f'<div class="sub"><b>{fmt_int(rows["total_tokens"].mean())}</b> tokens · <b>{rows[latency_field].mean():.1f} s</b> · '
        f'<b>{rows["num_llm_calls"].mean():.1f}</b> calls per question<br>{judge}</div></div>'
    )


def answer_card(key: str, row: pd.Series) -> str:
    em = row.get("exact_match")
    if em == 1:
        badge = '<span class="ag-ok">✓ Correct</span>'
    elif em == 0:
        badge = '<span class="ag-bad">✕ Incorrect</span>'
    else:
        badge = '<span class="ag-na">– not scored</span>'
    short = row.get("short_answer")
    short = short if isinstance(short, str) and short else ""
    body = str(row.get("answer") or "")
    urls = {}
    for e in row.get("evidence") or []:
        if isinstance(e, dict) and e.get("citation_id") and e.get("source_url"):
            urls[e["citation_id"]] = e["source_url"]
    meta = (f'P {row["doc_precision"]:.2f} · R {row["doc_recall"]:.2f} · {row["latency_sec"]:.1f} s · '
            f'{fmt_int(row["total_tokens"])} tokens · {row["num_llm_calls"]:.0f} calls')
    return (
        f'<div class="ag-res"><div class="hd"><div class="nm">{swatch(key)}{esc(PIPES[key]["short"])}</div>{badge}</div>'
        + (f'<div class="sa">{esc(short)}</div>' if short else "")
        + f'<div class="an">{answer_html(body[:520] + ("…" if len(body) > 520 else ""), urls)}</div>'
        + f'<div class="mt">{esc(meta)}</div></div>'
    )


def page_benchmark() -> None:
    md('<div class="ag-hero"><div class="ag-eyebrow">Benchmark · 100 public questions</div>'
       "<h1>Where the graph earns its keep</h1>"
       "<p>Every pipeline answers the same questions over the same corpus with the same generation model. Exact match "
       "is scored with no model in the loop; the 1–5 judge scores are a 20% sample from a separate model.</p></div>")

    available = [k for k, (_, p) in SOURCES.items() if p.exists()]
    f1, f2, f3 = st.columns([1.75, 2.35, 1.0], gap="medium")
    with f1:
        source = st.segmented_control("Results", available, default=available[0], required=True, key="bm_src",
                                      format_func=lambda k: SOURCES[k][0])
    path = SOURCES[source][1]
    df, stats = load_bench(str(path), path.stat().st_mtime)
    if df.empty:
        st.error(f"No scored rows in {path.name}.")
        return
    qtypes_all = bench.qtype_order(df)
    with f2:
        picked = st.pills("Question types", qtypes_all, selection_mode="multi", default=qtypes_all, key="bm_q",
                          format_func=bench.qtype_label)
    with f3:
        latency_field = st.segmented_control("Latency", ["latency_sec", "total_latency_sec"], default="latency_sec",
                                             required=True, key="bm_lat",
                                             format_func=lambda f: "Pipeline" if f == "latency_sec" else "End-to-end")
    if not picked:
        st.info("Select at least one question type.")
        return
    view = df[df["qtype"].astype(str).isin(picked)]
    picked = [q for q in qtypes_all if q in picked]
    n_q = view["qid"].nunique()

    em = view.groupby("pipeline")["exact_match"].mean()
    if "rag" in em and AGENT in em:
        base, agent = em["rag"], em[AGENT]
        delta = (agent - base) * 100
        rel = (agent - base) / base * 100 if base else 0
        md(
            '<div class="ag-band">'
            f'<div><div class="lbl">{swatch("rag")}RAG baseline</div><div class="num">{base:.0%}</div>'
            f'<div class="cap">plain vector search · {n_q} questions</div></div>'
            f'<div><div class="lbl">{swatch(AGENT)}Agentic GraphRAG</div><div class="num">{agent:.0%}</div>'
            f'<div class="cap">the submitted agent · same model, same questions</div></div>'
            f'<div><div class="lbl">Improvement</div><div class="num ag-up">▲ {delta:+.0f} pts</div>'
            f'<div class="cap">{rel:+.0f}% relative to the baseline</div></div></div>'
        )
    excluded = stats.get("excluded_rows", 0)
    md(f'<div class="ag-sub">Source: <span class="mono">{esc(Path(stats["path"]).name)}</span> · '
       f'{stats["valid_rows"]} scored rows' + (f' · {excluded} error or retry rows excluded' if excluded else "") + "</div>")

    tabs = st.tabs([":material/dashboard: Overview", ":material/grid_view: By question type", ":material/speed: Cost & speed",
                    ":material/manage_search: Retrieval", ":material/quiz: Question explorer"])
    keys = present_keys(view)

    with tabs[0]:
        for start in range(0, len(keys), 3):
            cols = st.columns(3, gap="medium")
            for col, key in zip(cols, keys[start:start + 3]):
                with col:
                    md(kpi_tile(key, view[view["pipeline"] == key], latency_field))
        left, right = st.columns(2, gap="large")
        with left:
            show(exact_match_bars(view), "em-bars")
        with right:
            show(emphasis_scatter(view, "total_tokens", "exact_match", x_title="Tokens per question", y_title="Exact match",
                                  title="Accuracy against cost (up and left is better)"), "em-tokens")
        heading("All metrics", "Means over the questions in scope; latency and tokens are per question.")
        summary = bench.pipeline_summary(view)
        summary["Pipeline"] = summary["Pipeline"].map(lambda lbl: next((v["short"] for v in PIPES.values() if v["label"] == lbl), lbl))
        st.dataframe(summary, hide_index=True, width="stretch", column_config={
            "questions": st.column_config.NumberColumn("Questions", format="%d"),
            "Exact match": st.column_config.ProgressColumn("Exact match", format="percent", min_value=0, max_value=1),
            "Accuracy": st.column_config.NumberColumn(format="%.2f"),
            "Completeness": st.column_config.NumberColumn(format="%.2f"),
            "Groundedness": st.column_config.NumberColumn(format="%.2f"),
            "Doc precision": st.column_config.NumberColumn(format="%.2f"),
            "Doc recall": st.column_config.NumberColumn(format="%.2f"),
            "Pipeline latency (s)": st.column_config.NumberColumn(format="%.1f"),
            "End-to-end latency (s)": st.column_config.NumberColumn(format="%.1f"),
            "Total tokens": st.column_config.NumberColumn(format="%d"),
            "LLM calls": st.column_config.NumberColumn(format="%.2f"),
        })

    with tabs[1]:
        heading("Where each pipeline wins and loses",
                "Aggregation and superlative questions need every matching event at once, which top-k text retrieval cannot see.")
        show(qtype_heatmap(view, picked), "heatmap")
        heading("LLM judge scores", "A separate model scores a 20% sample, 1–5. Treat small gaps as noise.")
        scores = bench.long_judge_scores(view)
        if scores.empty:
            st.caption("No judged rows in scope.")
        else:
            overall = scores.groupby(["dimension", "pipeline_label"], observed=True)["score"].mean().reset_index()
            label_to_key = {v["label"]: k for k, v in PIPES.items()}
            overall["pipeline"] = overall["pipeline_label"].astype(str).map(label_to_key)
            show(grouped_bars(overall, "dimension", "score", title="Mean judge score by dimension", y_title="Score (1–5)",
                              y_range=[0, 5.3]), "judge")
            with st.expander("Table view"):
                table = overall.pivot(index="pipeline", columns="dimension", values="score").round(2)
                table.index = [PIPES[k]["short"] for k in table.index]
                st.dataframe(table, width="stretch")

    with tabs[2]:
        lat_label = "Pipeline latency (s)" if latency_field == "latency_sec" else "End-to-end latency (s)"
        left, right = st.columns(2, gap="large")
        with left:
            show(box_chart(view, latency_field, title="Latency per question", y_title=lat_label), "lat-box")
        with right:
            show(box_chart(view, "total_tokens", title="Tokens per question", y_title="Tokens"), "tok-box")
        show(emphasis_scatter(view, latency_field, "exact_match", x_title=lat_label, y_title="Exact match",
                              title="Accuracy against latency (up and left is better)", x_fmt=".1f"), "em-lat")

    with tabs[3]:
        heading("Did the pipeline find the right documents?",
                "Each pipeline's retrieved document ids against the gold ids for that question, before the model sees anything. "
                "Precision: how much of what it retrieved was relevant. Recall: how much of what was relevant it found.")
        retrieval = view.groupby("pipeline")[["doc_precision", "doc_recall"]].mean().reset_index()
        long = retrieval.melt(id_vars="pipeline", var_name="metric", value_name="value")
        long["metric"] = long["metric"].map({"doc_precision": "Doc precision", "doc_recall": "Doc recall"})
        show(grouped_bars(long, "metric", "value", title="Mean doc precision and recall", y_title="Mean (0–1)",
                          y_range=[0, 1.05]), "ret-bars")
        with st.expander("Table view"):
            table = retrieval.copy()
            table["pipeline"] = table["pipeline"].map(lambda k: PIPES[k]["short"])
            st.dataframe(table.rename(columns={"pipeline": "Pipeline", "doc_precision": "Doc precision", "doc_recall": "Doc recall"}),
                         hide_index=True, width="stretch", column_config={
                             "Doc precision": st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1),
                             "Doc recall": st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1)})

    with tabs[4]:
        questions = view.drop_duplicates("qid").set_index("qid")
        spread = view.groupby("qid")["exact_match"].agg(lambda s: s.dropna().nunique() > 1)
        c1, c2 = st.columns([4, 1.4], vertical_alignment="bottom")
        with c2:
            only_split = st.toggle("Only where pipelines disagree", value=False, key="bm_split")
        qids = sorted(questions.index, key=lambda q: (str(questions.loc[q, "qtype"]), q))
        if only_split:
            qids = [q for q in qids if spread.get(q, False)]
        if not qids:
            st.info("No questions match.")
            return
        with c1:
            qid = st.selectbox("Question", qids, key="bm_qid", format_func=lambda q: (
                f"{q} · {bench.qtype_label(questions.loc[q, 'qtype'])} · {str(questions.loc[q, 'question'])[:90]}"))
        head = questions.loc[qid]
        md(f'<div class="ag-qcard"><span class="ag-tag">{esc(bench.qtype_label(head["qtype"]))}</span>'
           f'<span class="ag-tag" style="margin-left:6px">{esc(qid)}</span>'
           f'<div class="qt">{esc(head["question"])}</div>'
           f'<div class="ref">Reference answer: <b>{esc(head["reference_answer"] or "–")}</b></div></div>')
        detail = view[view["qid"] == qid].set_index("pipeline")
        cols = st.columns(3, gap="medium")
        for i, key in enumerate([k for k in bench.PIPELINES if k in detail.index]):
            row = detail.loc[key]
            with cols[i % 3]:
                md(answer_card(key, row))
                trace = list(row.get("trace") or [])
                evidence = list(row.get("evidence") or [])
                if trace or evidence:
                    with st.expander("Steps and evidence"):
                        res = {"trace": trace, "evidence": evidence, "route": row.get("route")}
                        md(steps_html(steps_for(key, res), PIPES[key]["color"]))
                        items = evidence_items(key, res)
                        if items:
                            md(evidence_cards_html(items[:8], cited_ids(str(row.get("answer") or "")), PIPES[key]["color"]))
                reasoning = row.get("judge_reasoning")
                if isinstance(reasoning, str) and reasoning and reasoning != "not_sampled":
                    with st.expander("Judge reasoning"):
                        st.write(reasoning)


# --------------------------------------------------------------------------- graph page

QUERY_SPECS = {
    "events_at_venue": ("Every Olympic event held at a venue: Venue ← HELD_AT ← OlympicEvent.", [("venue", "venue")]),
    "events_by_games_sport": ("Events of one sport at one Games, optionally above a competitor count.",
                              [("games", "games"), ("sport", "sport"), ("min_competitors", "int")]),
    "events_in_previous_games": ("Events of a sport at the Games before the given one, via PREV_GAMES.",
                                 [("games", "games"), ("sport", "sport")]),
    "facts_as_of": ("Time-scoped facts valid on a date (office holders, reigning champions).",
                    [("predicate", "predicate"), ("subject_key", "text"), ("object_key", "text"), ("as_of", "date")]),
    "fact_timeline": ("Every interval of a fact, in order.", [("predicate", "predicate"), ("subject_key", "text"), ("object_key", "text")]),
    "vector_search_chunks": ("Nearest chunks to a text, via the TigerGraph vector index.", [("query_vector", "embed"), ("k", "int")]),
    "vector_search_entities": ("Nearest entities to a text, via the TigerGraph vector index.", [("query_vector", "embed"), ("k", "int")]),
    "entity_neighbors_1hop": ("Entities related to the seeds, plus chunks that mention them.", [("seeds", "entities")]),
}


@st.cache_data(ttl=3600, show_spinner=False)
def vertex_options(vertex_type: str, label_attr: str | None) -> list:
    rows = tg_conn().getVertices(vertex_type, limit=5000)
    out = [(r["v_id"], (r["attributes"].get(label_attr) if label_attr else None) or r["v_id"]) for r in rows]
    return sorted(out, key=lambda t: str(t[1]))


@st.cache_data(ttl=3600, show_spinner=False)
def fact_predicates() -> list:
    rows = tg_conn().getVertices("TemporalFact", select="predicate", limit=10000)
    return sorted({r["attributes"].get("predicate") for r in rows if r["attributes"].get("predicate")})


def result_tables(result) -> list:
    tables = []
    for block in result or []:
        for name, value in block.items():
            if isinstance(value, list) and value and isinstance(value[0], dict) and "attributes" in value[0] and "v_id" in value[0]:
                rows = [{"v_id": v["v_id"], **{k: x for k, x in v["attributes"].items() if k != "embedding"}} for v in value]
                tables.append((name, pd.DataFrame(rows)))
            elif isinstance(value, list) and value and isinstance(value[0], dict) and "from_id" in value[0]:
                rows = [{"from": e.get("from_id"), "edge": e.get("e_type"), "to": e.get("to_id"), **(e.get("attributes") or {})}
                        for e in value]
                tables.append((name, pd.DataFrame(rows)))
            elif isinstance(value, dict):
                tables.append((name, pd.DataFrame([{"key": k, "value": v} for k, v in value.items()])))
            else:
                tables.append((name, pd.DataFrame([{"value": value}]) if not isinstance(value, list) else pd.DataFrame(value)))
    return tables


def schema_dot(stats: dict) -> str:
    v, e = stats.get("vertices", {}), stats.get("edges", {})

    def vnode(name, accent=False):
        line = '#d55181' if accent else INK["node_line"]
        return (f'{name} [label=<<b>{name}</b><br/><font color="{INK["muted"]}" point-size="9">{fmt_int(v.get(name, 0))}</font>>, '
                f'color="{line}"];')

    def edge(a, b, name, undirected=False):
        return (f'{a} -> {b} [label=<<font color="{INK["muted"]}" point-size="8">{name} · {fmt_int(e.get(name, 0))}</font>>'
                + (", dir=none" if undirected else "") + "];")

    def cluster(name, label, members):
        return (f'subgraph cluster_{name} {{ graph [label="{label}", style="rounded", color="#2a2e35", fontcolor="#898781", '
                f'fontsize=10, fontname="Inter", margin=14]; ' + " ".join(members) + " }")

    return "\n".join([
        "digraph S {",
        'graph [bgcolor="transparent", rankdir=LR, pad="0.2", nodesep="0.35", ranksep="0.7", fontname="Inter"];',
        f'node [shape=box, style="rounded,filled", fillcolor="{INK["raised"]}", fontcolor="{INK["primary"]}", fontname="Inter", '
        'fontsize=11, margin="0.18,0.08", penwidth=1.2];',
        f'edge [color="{INK["node_line"]}", arrowsize=0.6, fontname="Inter"];',
        cluster("text", "Text and entity layer", [vnode(n) for n in ("Document", "Chunk", "Entity", "Community")]),
        cluster("event", "Structured event layer", [vnode(n, n == "OlympicEvent") for n in ("OlympicEvent", "Games", "Sport", "Venue")]),
        cluster("time", "Temporal layer", [vnode("TemporalFact")]),
        edge("Chunk", "Document", "PART_OF"),
        edge("Chunk", "Entity", "MENTIONS"),
        edge("Entity", "Entity", "RELATED_TO", True),
        edge("Entity", "Community", "IN_COMMUNITY"),
        edge("OlympicEvent", "Games", "IN_GAMES", True),
        edge("OlympicEvent", "Sport", "IN_SPORT", True),
        edge("OlympicEvent", "Venue", "HELD_AT", True),
        edge("OlympicEvent", "Document", "DESCRIBED_BY", True),
        edge("Games", "Games", "PREV_GAMES"),
        edge("TemporalFact", "Document", "FACT_SOURCE", True),
        "}",
    ])


def page_graph() -> None:
    md('<div class="ag-hero"><div class="ag-eyebrow">TigerGraph Savanna</div>'
       "<h1>Inside the graph</h1>"
       "<p>Three layers in one graph: text chunks and LLM-extracted entities with vector embeddings, a structured "
       "Olympic event layer built straight from the article infoboxes, and time-scoped facts with validity intervals.</p></div>")
    stats = graph_stats()
    if not stats.get("ok"):
        st.error(f"TigerGraph is unreachable: {stats.get('error')}")
        return
    v = stats["vertices"]
    tiles = [("Documents", "Document", "Wikipedia articles"), ("Chunks", "Chunk", "native vector index"),
             ("Entities", "Entity", "LLM-extracted"), ("Olympic events", "OlympicEvent", "from infoboxes"),
             ("Temporal facts", "TemporalFact", "validity intervals"), ("Relationships", None, "RELATED_TO edges")]
    cols = st.columns(6, gap="small")
    for col, (label, vt, cap) in zip(cols, tiles):
        value = v.get(vt, 0) if vt else stats["edges"].get("RELATED_TO", 0)
        with col:
            md(f'<div class="ag-kpi" style="padding:14px 15px"><div class="sub" style="color:var(--muted)">{esc(label)}</div>'
               f'<div class="val" style="font-size:1.6rem">{fmt_int(value)}</div><div class="sub">{esc(cap)}</div></div>')
    heading("Schema", "Vertex and edge counts are live from the graph.")
    with st.container(border=True):
        st.graphviz_chart(schema_dot(stats), width="content")

    heading("Run an installed query", "Pick one of the GSQL queries the pipelines use and run it against the live graph.")
    names = [q for q in QUERY_SPECS if q in stats["queries"]] or list(QUERY_SPECS)
    with st.container(border=True):
        qname = st.selectbox("Query", names, key="gq_name")
        desc, spec = QUERY_SPECS[qname]
        st.caption(desc)
        params, ready = {}, True
        cols = st.columns(max(1, len(spec)), gap="small")
        for col, (pname, kind) in zip(cols, spec):
            with col:
                if kind == "venue":
                    opts = vertex_options("Venue", "name")
                    default = next((i for i, (vid, _) in enumerate(opts) if vid == "richmond olympic oval"), 0)
                    vid = st.selectbox("venue", opts, index=default, format_func=lambda t: t[1], key="gq_venue")[0]
                    params["venue"] = (vid,)
                elif kind == "games":
                    opts = vertex_options("Games", None)
                    default = next((i for i, (vid, _) in enumerate(opts) if vid == "2018 Winter"), 0)
                    params["games"] = (st.selectbox("games", opts, index=default, format_func=lambda t: t[1], key="gq_games")[0],)
                elif kind == "sport":
                    opts = vertex_options("Sport", "name")
                    default = next((i for i, (vid, _) in enumerate(opts) if vid == "biathlon"), 0)
                    params["sport"] = (st.selectbox("sport", opts, index=default, format_func=lambda t: t[1], key="gq_sport")[0],)
                elif kind == "int":
                    params[pname] = int(st.number_input(pname, value=73 if pname == "min_competitors" else 5, step=1, key=f"gq_{pname}"))
                elif kind == "predicate":
                    preds = fact_predicates()
                    params[pname] = st.selectbox(pname, preds, index=preds.index("held_office") if "held_office" in preds else 0,
                                                 key="gq_pred")
                elif kind == "text":
                    from src.common.infobox import norm_key

                    default = "President of Russia" if pname == "object_key" else ""
                    raw = st.text_input(pname, value=default, key=f"gq_{pname}", help="Free text, normalized the way the agent does.")
                    params[pname] = norm_key(raw) if raw else ""
                elif kind == "date":
                    picked = st.date_input("as of", value=pd.Timestamp("2013-01-01"), key="gq_date",
                                           min_value=pd.Timestamp("1900-01-01"), max_value=pd.Timestamp("2030-12-31"))
                    params[pname] = int(picked.strftime("%Y%m%d"))
                elif kind == "embed":
                    text = st.text_input("text to embed", value="Richmond Olympic Oval speed skating 2010", key="gq_text")
                    params["__embed__"] = text
                    ready = bool(text.strip())
                elif kind == "entities":
                    raw = st.text_input("seed entity ids", value="vladimir_putin", key="gq_seeds", help="Comma-separated Entity ids.")
                    params[pname] = [s.strip() for s in raw.split(",") if s.strip()]
                    ready = bool(params[pname])
        run = st.button("Run query", type="primary", icon=":material/play_arrow:", disabled=not ready, key="gq_run")
    if run:
        shown = {k: (v[0] if isinstance(v, tuple) else v) for k, v in params.items()}
        call = ", ".join(f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}" for k, v in shown.items()
                         if k != "__embed__") or ""
        if "__embed__" in params:
            from src.common.llm import embed

            vec, _ = embed([params.pop("__embed__")], task_type="RETRIEVAL_QUERY", pipeline="console")
            params["query_vector"] = vec[0]
            call = (call + ", " if call else "") + f'query_vector=embed("{shown["__embed__"]}")'
        started = time.time()
        try:
            result = tg_conn().runInstalledQuery(qname, params=params)
            error = None
        except Exception as exc:
            result, error = None, f"{type(exc).__name__}: {exc}"
        elapsed = time.time() - started
        md(f'<div class="ag-sub" style="margin-top:.8rem"><span class="ag-chip">RUN QUERY {esc(qname)}({esc(call)})</span>'
           f" · {elapsed * 1000:.0f} ms round trip</div>")
        if error:
            st.error(error)
        else:
            for name, table in result_tables(result):
                heading(f"{name} · {len(table)} rows")
                st.dataframe(table, hide_index=True, width="stretch")
            with st.expander("Raw JSON response"):
                st.json(result, expanded=False)

    heading("Installed queries", "All installed on the graph; the pipelines call them through the REST endpoint.")
    st.dataframe(pd.DataFrame([{"Query": q, "Installed": q in stats["queries"], "What it does": QUERY_SPECS[q][0]}
                               for q in QUERY_SPECS]), hide_index=True, width="stretch")


# --------------------------------------------------------------------------- app

md(CSS)
topbar()
navigation = st.navigation(
    [
        st.Page(page_ask, title="Ask", icon=":material/travel_explore:", url_path="ask", default=True),
        st.Page(page_benchmark, title="Benchmark", icon=":material/monitoring:", url_path="benchmark"),
        st.Page(page_graph, title="Graph", icon=":material/hub:", url_path="graph"),
    ],
    position="top",
)
navigation.run()
