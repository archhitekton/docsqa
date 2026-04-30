#!/usr/bin/env python3
"""Eval harness: test RAG system against golden QA dataset."""

import asyncio
import json
import requests
import time
import logging
from pathlib import Path
from datetime import datetime
import anthropic

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

API_URL = "http://127.0.0.1:8000"
GOLDEN_FILE = "eval/golden.json"
REPORT_FILE = "eval/report.json"

# Voyage pricing: $0.00000002 per token
VOYAGE_COST_PER_TOKEN = 0.00000002
# Claude Haiku pricing: $0.00000025 per input token, $0.00000125 per output token
CLAUDE_INPUT_COST = 0.00000025
CLAUDE_OUTPUT_COST = 0.00000125


def load_golden():
    """Load golden QA dataset."""
    with open(GOLDEN_FILE) as f:
        return json.load(f)


def parse_sse_response(response_text: str) -> tuple[str, list]:
    """Parse SSE response: stream of tokens + sources JSON."""
    answer = ""
    sources = []

    for line in response_text.strip().split("\n"):
        if not line.startswith("data: "):
            continue

        data = line[6:]  # Strip "data: " prefix

        if data == "[DONE]":
            continue

        try:
            obj = json.loads(data)
            if "token" in obj:
                answer += obj["token"]
            elif "sources" in obj:
                sources = obj["sources"]
        except json.JSONDecodeError:
            pass

    return answer, sources


def query_api(question: str, top_k: int = 5, min_score: float = 0.75) -> dict:
    """Call /query endpoint and parse response."""
    start = time.time()

    try:
        response = requests.post(
            f"{API_URL}/query",
            json={"question": question, "top_k": top_k, "min_score": min_score},
            stream=True,
        )
        response.raise_for_status()

        # Read streaming response
        response_text = ""
        for chunk in response.iter_content(decode_unicode=True):
            if chunk:
                response_text += chunk

        latency_ms = (time.time() - start) * 1000

        # Check if fallback response (not streaming)
        try:
            data = json.loads(response_text)
            if "answer" in data and "sources" in data:
                # Fallback response
                return {
                    "answer": data["answer"],
                    "sources": data["sources"],
                    "latency_ms": latency_ms,
                    "is_fallback": True,
                }
        except json.JSONDecodeError:
            pass

        # Parse SSE stream
        answer, sources = parse_sse_response(response_text)

        return {
            "answer": answer,
            "sources": sources,
            "latency_ms": latency_ms,
            "is_fallback": False,
        }

    except Exception as e:
        logger.error(f"Query failed: {e}")
        return {"error": str(e), "latency_ms": (time.time() - start) * 1000}


def check_fallback(answer: str) -> bool:
    """Check if answer is the fallback response."""
    fallback_text = "I don't have that information in the provided documents"
    return fallback_text in answer


def check_source_in_top3(sources: list, relevant_doc: str) -> bool:
    """Check if relevant_doc appears in top-3 sources."""
    if not sources:
        return False
    top3_docs = [s["filename"] for s in sources[:3]]
    return relevant_doc in top3_docs


def get_source_rank(sources: list, relevant_doc: str) -> int:
    """Get 1-indexed rank of relevant_doc in sources, or 0 if not found."""
    for i, source in enumerate(sources):
        if source["filename"] == relevant_doc:
            return i + 1
    return 0


def compute_mrr(sources: list, relevant_doc: str) -> float:
    """Compute MRR: 1/rank if found, else 0."""
    rank = get_source_rank(sources, relevant_doc)
    return 1.0 / rank if rank > 0 else 0.0


def judge_answer(question: str, expected: str, actual: str) -> bool:
    """Use Claude to judge if actual answer is correct."""
    client = anthropic.Anthropic()

    prompt = f"""Question: {question}

Expected answer (for reference): {expected}

Actual answer: {actual}

Does the actual answer correctly address the question? Reply with exactly PASS or FAIL and one sentence explaining why."""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )

    answer = response.content[0].text.strip().upper()
    return answer.startswith("PASS")


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def main():
    """Run eval harness."""
    logger.info("Loading golden dataset...")
    golden = load_golden()
    logger.info(f"Loaded {len(golden)} QA pairs")

    results = []
    answerable_count = sum(1 for q in golden if q["answerable"])
    unanswerable_count = len(golden) - answerable_count

    logger.info(f"Answerable: {answerable_count}, Unanswerable: {unanswerable_count}")
    logger.info("Running evaluation...")

    for i, qa in enumerate(golden, 1):
        question = qa["question"]
        logger.info(f"[{i}/{len(golden)}] {question[:60]}...")

        # Query API
        result = query_api(question)

        if "error" in result:
            logger.error(f"  ERROR: {result['error']}")
            continue

        answer = result["answer"]
        sources = result["sources"]
        latency_ms = result["latency_ms"]
        is_fallback = result["is_fallback"]

        # Evaluate
        if not qa["answerable"]:
            # Unanswerable question
            passed = check_fallback(answer)
            result_type = "PASS (fallback)" if passed else "FAIL (hallucination)"
            logger.info(f"  {result_type}, latency={latency_ms:.0f}ms")

            # Cost: voyage only (no Claude call)
            voyage_tokens = estimate_tokens(question)
            cost_usd = voyage_tokens * VOYAGE_COST_PER_TOKEN

            results.append({
                "question": question,
                "answerable": False,
                "passed": passed,
                "answer": answer,
                "sources": sources,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd,
            })
        else:
            # Answerable question
            p3 = check_source_in_top3(sources, qa["relevant_doc"])
            rank = get_source_rank(sources, qa["relevant_doc"])
            mrr = compute_mrr(sources, qa["relevant_doc"])

            # Judge answer
            judge_passed = judge_answer(question, qa["expected"], answer)

            logger.info(
                f"  Judge: {'PASS' if judge_passed else 'FAIL'}, "
                f"P@3={p3}, rank={rank}, latency={latency_ms:.0f}ms"
            )

            # Cost: voyage + claude
            voyage_tokens = estimate_tokens(question)
            claude_input_tokens = estimate_tokens(question + answer)
            claude_output_tokens = estimate_tokens(answer)

            voyage_cost = voyage_tokens * VOYAGE_COST_PER_TOKEN
            claude_cost = (
                claude_input_tokens * CLAUDE_INPUT_COST
                + claude_output_tokens * CLAUDE_OUTPUT_COST
            )
            cost_usd = voyage_cost + claude_cost

            results.append({
                "question": question,
                "answerable": True,
                "passed": judge_passed,
                "answer": answer,
                "sources": sources,
                "precision_at_3": 1.0 if p3 else 0.0,
                "rank": rank,
                "mrr": mrr,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd,
            })

    # Compute report
    logger.info("Computing report...")

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    score = passed / total if total > 0 else 0.0

    # Hallucination rate: unanswerable questions that were answered (FAIL)
    unanswerable_results = [r for r in results if not r["answerable"]]
    failed_unanswerable = sum(1 for r in unanswerable_results if not r["passed"])
    hallucination_rate = (
        failed_unanswerable / len(unanswerable_results)
        if unanswerable_results
        else 0.0
    )

    # Precision@3 and MRR: only for answerable questions that were evaluated
    answerable_results = [r for r in results if r["answerable"]]
    precision_at_3 = (
        sum(r["precision_at_3"] for r in answerable_results) / len(answerable_results)
        if answerable_results
        else 0.0
    )
    mrr = (
        sum(r["mrr"] for r in answerable_results) / len(answerable_results)
        if answerable_results
        else 0.0
    )

    # Costs and latency
    avg_cost_usd = sum(r["cost_usd"] for r in results) / len(results) if results else 0.0
    avg_latency_ms = sum(r["latency_ms"] for r in results) / len(results) if results else 0.0

    report = {
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "answerable": answerable_count,
        "unanswerable": unanswerable_count,
        "passed": passed,
        "score": score,
        "hallucination_rate": hallucination_rate,
        "precision_at_3": precision_at_3,
        "mrr": mrr,
        "avg_cost_usd": avg_cost_usd,
        "avg_latency_ms": avg_latency_ms,
        "results": results,
    }

    # Write report
    Path("eval").mkdir(exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "=" * 80)
    print("EVAL REPORT")
    print("=" * 80)
    print(f"Total: {total} questions")
    print(f"Passed: {passed}/{total} ({score*100:.1f}%)")
    print(f"Hallucination rate: {hallucination_rate*100:.1f}% ({failed_unanswerable}/{len(unanswerable_results)})")
    print(f"Precision@3: {precision_at_3:.3f}")
    print(f"MRR: {mrr:.3f}")
    print(f"Avg cost: ${avg_cost_usd:.6f}/query")
    print(f"Avg latency: {avg_latency_ms:.0f}ms")
    print(f"Report: {REPORT_FILE}")
    print("=" * 80)

    logger.info(f"Eval complete. Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
