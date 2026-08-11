"""Run a small, reproducible retrieval evaluation against the live API."""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_CASES = Path(__file__).parents[1] / "evaluation" / "retrieval_cases.json"


def evaluate_case(case: dict[str, Any], response: dict[str, Any]) -> list[str]:
    """Return human-readable failures for one retrieval response."""

    failures: list[str] = []
    expected_answerable = case["expected_answerable"]
    if response.get("answerable") is not expected_answerable:
        failures.append(
            f"answerable={response.get('answerable')!r}; "
            f"expected {expected_answerable!r}"
        )

    expected_source = case.get("expected_source")
    sources = {result.get("source") for result in response.get("results", [])}
    if expected_source and expected_source not in sources:
        failures.append(
            f"expected source {expected_source!r}; received {sorted(sources)!r}"
        )

    expected_reason = case.get("expected_reason")
    if expected_reason and response.get("reason") != expected_reason:
        failures.append(
            f"reason={response.get('reason')!r}; expected {expected_reason!r}"
        )

    if not expected_answerable and response.get("results"):
        failures.append("negative case returned document context")

    return failures


def post_search(api_url: str, query: str, top_k: int) -> dict[str, Any]:
    """Call POST /search using only the Python standard library."""

    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/search",
        data=json.dumps({"query": query, "top_k": top_k}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--top-k", type=int, default=2)
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    passed = 0
    for case in cases:
        try:
            response = post_search(args.api_url, case["query"], args.top_k)
            failures = evaluate_case(case, response)
        except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            failures = [f"request failed: {exc}"]

        if failures:
            print(f"FAIL {case['id']}")
            for failure in failures:
                print(f"  - {failure}")
        else:
            passed += 1
            results = response.get("results", [])
            top_score = results[0]["score"] if results else None
            score_text = f" top_score={top_score:.3f}" if top_score is not None else ""
            print(f"PASS {case['id']}{score_text}")

    print(f"\nRetrieval evaluation: {passed}/{len(cases)} passed")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
