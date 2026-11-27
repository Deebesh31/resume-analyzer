"""Run the local synthetic benchmark for ResuMate's deterministic score rubric."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = Path(__file__).with_name("structure_score_cases.json")
FACTOR_NAMES = (
    "Text extraction",
    "Section structure",
    "Work-history detail",
    "Contact details",
    "Skills visibility",
    "Achievement evidence",
)


def load_score_function():
    sys.path.insert(0, str(REPOSITORY_ROOT))
    from resume_service import calculate_resume_statistics, calculate_structure_score

    return calculate_resume_statistics, calculate_structure_score


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Path to a benchmark JSON file (defaults to structure_score_cases.json).",
    )
    args = parser.parse_args()

    try:
        dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        parser.error(f"could not read benchmark dataset: {error}")

    cases = dataset.get("cases")
    documents = dataset.get("documents")
    profiles = dataset.get("profiles")
    if not isinstance(cases, list) or not cases:
        parser.error("dataset must contain at least one case")
    if not isinstance(documents, dict) or not isinstance(profiles, dict):
        parser.error("dataset must contain documents and profiles objects")

    calculate_resume_statistics, calculate_structure_score = load_score_function()
    score_errors = []
    factor_errors = {name: [] for name in FACTOR_NAMES}
    score_exact = 0
    factor_exact = 0
    print(f"{dataset.get('dataset_name', 'Structure score benchmark')} ({len(cases)} cases)")
    print("Case                              Actual  Expected  Result")
    print("-" * 65)

    for case in cases:
        case_id = case.get("id", "<unnamed>")
        try:
            text = documents[case["document"]]
            profile = profiles[case["profile"]]
            readability = case["readability"]
            expected_score = float(case["expected_score"])
            expected_label = case["expected_label"]
            expected_breakdown = case["expected_breakdown"]
        except (KeyError, TypeError, ValueError) as error:
            parser.error(f"invalid case {case_id!r}: {error}")

        stats = calculate_resume_statistics(text, profile)
        actual = calculate_structure_score(text, stats, readability, profile)
        actual_breakdown = {item["name"]: item["score"] for item in actual["breakdown"]}
        score_error = abs(float(actual["value"]) - expected_score)
        score_errors.append(score_error)

        exact_factors_for_case = True
        for factor in FACTOR_NAMES:
            actual_points = actual_breakdown.get(factor)
            expected_points = expected_breakdown.get(factor)
            if actual_points is None or expected_points is None:
                exact_factors_for_case = False
                factor_errors[factor].append(math.inf)
                continue
            error = abs(float(actual_points) - float(expected_points))
            factor_errors[factor].append(error)
            exact_factors_for_case &= error == 0

        passed = (
            score_error == 0
            and exact_factors_for_case
            and actual["label"] == expected_label
            and set(actual_breakdown) == set(expected_breakdown)
        )
        score_exact += score_error == 0
        factor_exact += exact_factors_for_case
        print(
            f"{case_id[:32]:32} {actual['value']:>6}/100 {expected_score:>8.0f}/100  "
            f"{'PASS' if passed else 'FAIL'}"
        )
        if not passed:
            print(f"  expected label: {expected_label}; actual label: {actual['label']}")
            for factor in FACTOR_NAMES:
                if actual_breakdown.get(factor) != expected_breakdown.get(factor):
                    print(
                        f"  {factor}: expected {expected_breakdown.get(factor)}, "
                        f"got {actual_breakdown.get(factor)}"
                    )

    mean_absolute_score_error = sum(score_errors) / len(score_errors)
    print("-" * 65)
    print(f"Exact total scores: {score_exact}/{len(cases)}")
    print(f"Exact factor breakdowns: {factor_exact}/{len(cases)}")
    print(f"Mean absolute score error: {mean_absolute_score_error:.2f} points (out of 100)")
    print("Mean absolute error by factor:")
    for factor, errors in factor_errors.items():
        mean_error = sum(errors) / len(errors)
        print(f"  {factor}: {mean_error:.2f} points")
    return 0 if score_exact == len(cases) and factor_exact == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
