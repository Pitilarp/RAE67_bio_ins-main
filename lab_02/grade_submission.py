"""Diagnostic checks for a Lab 02 student_controller.py submission.

This checks controller behavior only. The instructor must still assess the
diagram, experimental integrity, analysis, and interpretation in the rubric.
Run untrusted student code in an isolated environment without credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Callable

from lab02 import LabConfig, calculate_metrics, load_student_factory, simulate_trial


def evaluate_submission(student_file: Path) -> dict[str, object]:
    student_file = student_file.resolve()
    report: dict[str, object] = {
        "student_file": str(student_file),
        "student_file_sha256": hashlib.sha256(student_file.read_bytes()).hexdigest()
        if student_file.is_file() else None,
        "checks": [],
        "scope": "Diagnostic controller checks only; not an automatic 20-point grade.",
    }
    checks: list[dict[str, str]] = report["checks"]  # type: ignore[assignment]

    try:
        factory = load_student_factory(student_file)
    except Exception as error:
        checks.append({"name": "load_submission", "status": "FAIL", "detail": f"{type(error).__name__}: {error}"})
        report["passed"] = 0
        report["failed"] = 1
        return report

    checks.append({"name": "load_submission", "status": "PASS", "detail": "StudentController and Parameters found"})

    def check(name: str, action: Callable[[], None]) -> None:
        try:
            action()
        except Exception as error:
            checks.append({"name": name, "status": "FAIL", "detail": f"{type(error).__name__}: {error}"})
        else:
            checks.append({"name": name, "status": "PASS", "detail": ""})

    def assert_close(actual: object, expected: float) -> None:
        if not isinstance(actual, (int, float)) or not math.isclose(actual, expected, abs_tol=1e-9):
            raise AssertionError(f"expected {expected}, got {actual!r}")

    def filter_check() -> None:
        student = factory("C2", LabConfig()).student
        assert_close(student.update_filter(0.6), 0.6)
        assert_close(student.update_filter(0.2), 0.5)

    def threshold_check() -> None:
        student = factory("C1", LabConfig()).student
        if student.update_state_single_threshold(0.34) != "NEAR":
            raise AssertionError("0.34 m must be NEAR")
        if student.update_state_single_threshold(0.35) != "FAR":
            raise AssertionError("0.35 m must be FAR")

    def hysteresis_check() -> None:
        student = factory("C2", LabConfig()).student
        for distance, expected in ((0.31, "NEAR"), (0.35, "NEAR"), (0.39, "FAR"), (0.35, "FAR")):
            state = student.update_state_hysteresis(distance)
            if state != expected:
                raise AssertionError(f"at {distance} m expected {expected}, got {state!r}")
            student.state = state

    def proportional_check() -> None:
        student = factory("C3", LabConfig()).student
        for distance, expected in ((0.0, 0.6), (0.35, 0.0), (1.0, -0.6)):
            assert_close(student.proportional_command(distance), expected)

    def invalid_check() -> None:
        state, command, filtered = factory("C2", LabConfig()).step(0.0, None, False)
        if state != "FAR" or command != 0.0 or filtered is not None:
            raise AssertionError("invalid sample must keep FAR and use zero safe command")

    check("filter", filter_check)
    check("single_threshold", threshold_check)
    check("hysteresis", hysteresis_check)
    check("proportional_and_clamp", proportional_check)
    check("invalid_sample", invalid_check)

    for condition in ("C0", "C1", "C2", "C3"):
        def trial_check(selected: str = condition) -> None:
            rows = simulate_trial(
                selected, noise_sigma_m=0.01, delay_ms=0, seed=202602,
                controller_factory=factory,
            )
            if len(rows) != 1001:
                raise AssertionError(f"expected 1001 samples, got {len(rows)}")
            calculate_metrics(rows)
            reference = simulate_trial(selected, noise_sigma_m=0.01, delay_ms=0, seed=202602)
            state_mismatches = sum(a["state"] != b["state"] for a, b in zip(rows, reference))
            max_command_error = max(
                abs(float(a["command"]) - float(b["command"]))
                for a, b in zip(rows, reference)
            )
            filter_mismatches = sum(
                (a["filtered_distance_m"] is None) != (b["filtered_distance_m"] is None)
                or (
                    a["filtered_distance_m"] is not None
                    and b["filtered_distance_m"] is not None
                    and abs(float(a["filtered_distance_m"]) - float(b["filtered_distance_m"])) > 1e-8
                )
                for a, b in zip(rows, reference)
            )
            if state_mismatches or max_command_error > 1e-8 or filter_mismatches:
                raise AssertionError(
                    f"vs reference: {state_mismatches} state mismatches, "
                    f"{filter_mismatches} filter mismatches, "
                    f"max command error {max_command_error:.6g}"
                )

        check(f"full_trial_{condition}", trial_check)

    report["passed"] = sum(item["status"] == "PASS" for item in checks)
    report["failed"] = sum(item["status"] == "FAIL" for item in checks)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student-file", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="new JSON report path; existing files are not overwritten")
    args = parser.parse_args()
    report = evaluate_submission(args.student_file)
    for item in report["checks"]:
        print(f"{item['status']:4}  {item['name']}: {item['detail']}")
    print(f"Passed: {report['passed']}  Failed: {report['failed']}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(f"Report: {args.out.resolve()}")
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
