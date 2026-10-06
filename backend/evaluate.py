"""Read-only live smoke evals through the same ADK runner as the website.

Run: uv run --directory backend python evaluate.py --output /tmp/hotel-evals.json
The checks are deterministic assertions, not LLM quality scores. Review the answers.
"""
import argparse
import asyncio
import json
import time
from datetime import date
from pathlib import Path

from app import agent
from app.db import connect
from app.settings import Settings


def failures(result, checks):
    errors = []
    text = result["answer"].lower()
    availability = result.get("availability") or {}
    for key in ("check_in", "check_out"):
        if key in checks and availability.get(key) != checks[key]:
            errors.append(f"{key}: expected {checks[key]}, got {availability.get(key)}")
    if "availability_status" in checks and availability.get("status") != checks["availability_status"]:
        errors.append(f"availability: {availability.get('status')}")
    if "card_ids" in checks and sorted(card["id"] for card in availability.get("cards", [])) != sorted(checks["card_ids"]):
        errors.append("Unexpected villa cards")
    sources = {source["id"] for source in result.get("sources", [])}
    errors.extend(f"Missing source: {source}" for source in checks.get("sources", []) if source not in sources)
    errors.extend(f"Missing phrase: {phrase}" for phrase in checks.get("contains", []) if phrase.lower() not in text)
    errors.extend(f"Forbidden phrase: {phrase}" for phrase in checks.get("absent", []) if phrase.lower() in text)
    if checks.get("no_availability") and result.get("availability"):
        errors.append("Availability checked without enough information")
    if checks.get("no_request") and result.get("hotel_request"):
        errors.append("Unexpected hotel request")
    return errors


async def run(args):
    dataset = json.loads(args.dataset.read_text())
    settings = Settings()
    context = agent.current_date_context
    agent.current_date_context = lambda: context(date.fromisoformat(dataset["property_date"]))
    pool = await connect(settings)
    semaphore = asyncio.Semaphore(3)

    async def case_run(case):
        async with semaphore:
            history, turns = [], []
            for turn in case["turns"]:
                started = time.monotonic()
                try:
                    result = None
                    async with asyncio.timeout(90):
                        async for event in agent.answer(pool, settings, history, turn["question"]):
                            if event["type"] == "result":
                                result = event
                    if result is None:
                        raise RuntimeError("No final answer")
                    errors = failures(result, turn["checks"])
                    history.append({"question": turn["question"], "answer": result["answer"]})
                    turns.append({"question": turn["question"], "result": result, "failures": errors, "seconds": round(time.monotonic() - started, 2)})
                except Exception as error:
                    turns.append({"question": turn["question"], "failures": [f"{type(error).__name__}: {error}"]})
                    break
            passed = all(not turn["failures"] for turn in turns)
            print(f"{'PASS' if passed else 'FAIL'} {case['id']}", flush=True)
            return {"id": case["id"], "passed": passed, "turns": turns}

    try:
        selected = [case for case in dataset["cases"] if bool(case.get("holdout")) == args.holdout]
        if args.case:
            selected = [case for case in selected if case["id"] == args.case]
        if not selected:
            raise ValueError("No matching evaluation cases")
        results = await asyncio.gather(*(case_run(case) for case in selected))
        args.output.write_text(json.dumps({"model": settings.gemini_model, "property_date": dataset["property_date"], "cases": results}, indent=2))
        return all(case["passed"] for case in results)
    finally:
        agent.current_date_context = context
        await pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path(__file__).resolve().parents[1] / "evals/demo-smoke.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--holdout", action="store_true")
    parser.add_argument("--case", help="Run one named case")
    raise SystemExit(0 if asyncio.run(run(parser.parse_args())) else 1)
