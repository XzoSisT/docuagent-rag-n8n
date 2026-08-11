"""Tests for deterministic retrieval evaluation checks."""

from scripts.evaluate_retrieval import evaluate_case


def test_positive_case_requires_the_expected_source() -> None:
    case = {
        "expected_answerable": True,
        "expected_source": "guide.pdf",
    }

    assert evaluate_case(
        case,
        {
            "answerable": True,
            "reason": "context_found",
            "results": [{"source": "guide.pdf"}],
        },
    ) == []

    failures = evaluate_case(
        case,
        {
            "answerable": True,
            "reason": "context_found",
            "results": [{"source": "other.pdf"}],
        },
    )
    assert "expected source" in failures[0]


def test_negative_case_requires_empty_results_and_expected_reason() -> None:
    case = {
        "expected_answerable": False,
        "expected_reason": "no_relevant_context",
    }

    assert evaluate_case(
        case,
        {
            "answerable": False,
            "reason": "no_relevant_context",
            "results": [],
        },
    ) == []

    failures = evaluate_case(
        case,
        {
            "answerable": True,
            "reason": "context_found",
            "results": [{"source": "unrelated.pdf"}],
        },
    )
    assert len(failures) == 3
