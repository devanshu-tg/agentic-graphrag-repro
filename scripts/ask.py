"""Ask the live graph a question from the terminal (added locally for the reproduction;
not part of the original submission).

    .venv/bin/python scripts/ask.py "Who won gold at Richmond Olympic Oval on 14 February 2010?"
    .venv/bin/python scripts/ask.py --pipeline rag "..."      # rag | graphrag | agentic | event_graph | investigator
    .venv/bin/python scripts/ask.py --compare "..."           # same question through all five pipelines
    .venv/bin/python scripts/ask.py                           # interactive: type questions, blank line to quit

Every call hits the TigerGraph graph in .env and spends Gemini quota. No TypeSafe key needed.
"""
import argparse
import importlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.tg_conn import get_connection  # noqa: E402
from src.common.token_tracker import TokenTracker  # noqa: E402

PIPELINES = ["rag", "graphrag", "agentic", "event_graph", "investigator"]
BOLD, DIM, GREEN, RESET = "\033[1m", "\033[2m", "\033[32m", "\033[0m"


def ask(conn, pipeline: str, question: str, verbose: bool = True) -> dict:
    module = importlib.import_module(f"src.pipelines.{pipeline}.pipeline")
    tracker = TokenTracker()
    started = time.time()
    result = module.answer_question(conn, question, tracker=tracker, question_id="live")
    elapsed = time.time() - started
    totals = tracker.totals_for("live")

    print(f"\n{BOLD}[{pipeline}]{RESET} {GREEN}{result.get('short_answer') or result['answer'][:200]}{RESET}")
    if verbose:
        for step in result.get("trace", []) or []:
            if step.get("action"):
                detail = step.get("event_query") or step.get("fact_query") or step.get("query") or ""
                print(f"   {DIM}step {step.get('iteration', '?')}: {step['action']} {detail}{RESET}")
                if step.get("tool_result"):
                    print(f"   {DIM}   -> {str(step['tool_result'])[:220]}{RESET}")
        if result.get("route"):
            print(f"   {DIM}route: {result['route']}{RESET}")
        print(f"   answer: {result['answer'][:600]}")
        if result.get("retrieved_doc_ids"):
            print(f"   {DIM}sources: {', '.join(result['retrieved_doc_ids'][:8])}{RESET}")
    print(f"   {DIM}{elapsed:.1f}s · {totals.get('num_llm_calls', 0)} model calls · "
          f"{totals.get('total_tokens', 0):,} tokens{RESET}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("question", nargs="*")
    parser.add_argument("--pipeline", "-p", default="investigator", choices=PIPELINES)
    parser.add_argument("--compare", "-c", action="store_true", help="run all five pipelines")
    args = parser.parse_args()

    conn = get_connection()
    pipelines = PIPELINES if args.compare else [args.pipeline]

    questions = [" ".join(args.question)] if args.question else None
    if questions:
        for p in pipelines:
            ask(conn, p, questions[0], verbose=not args.compare)
        return 0

    print(f"Connected to graph '{conn.graphname}'. Pipeline: {', '.join(pipelines)}. Blank line to quit.")
    while True:
        try:
            q = input(f"\n{BOLD}question>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            break
        for p in pipelines:
            try:
                ask(conn, p, q, verbose=not args.compare)
            except Exception as exc:  # keep the session alive on one bad question
                print(f"   [{p}] failed: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
