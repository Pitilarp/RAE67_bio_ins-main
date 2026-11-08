#!/usr/bin/env python3
"""Synthetic expected/actual contact lesson, not robot feedback or paper Eq.(3).

The explicit paired-product Pearson definition is a proposed course model.
Input generation is synthetic; this module never feeds Lab05's hormone/CPG.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

from course_model import LEGS
from lab05 import DT, HERE, grid_steps, prepare_output, sha256, write_csv, write_json

WINDOW = 50
CASES = ("matched", "gain-offset", "mixed-delay", "all-inverted", "constant", "fault")


def pearson(expected: list[float], actual: list[float]) -> tuple[float | None, str]:
    if len(expected) != len(actual):
        raise ValueError("Paired windows must have equal length")
    if len(expected) != WINDOW:
        return None, "incomplete_window"
    if any(not math.isfinite(x) for x in expected + actual):
        return None, "nonfinite_window"
    if any(not 0 <= x <= 1 for x in expected + actual):
        return None, "out_of_range_window"
    ma, mb = sum(expected) / WINDOW, sum(actual) / WINDOW
    a, b = [x - ma for x in expected], [x - mb for x in actual]
    va, vb = sum(x * x for x in a), sum(x * x for x in b)
    if va <= 1e-12 or vb <= 1e-12:
        return None, "zero_variance"
    value = sum(x * y for x, y in zip(a, b)) / math.sqrt(va * vb)
    return max(-1.0, min(1.0, value)), "valid"


def population_sif(si: list[float | None]) -> float | None:
    if len(si) != 6:
        raise ValueError("SIF requires six leg correlations")
    if any(x is None for x in si):
        return None  # do not replace unavailable SI with zero
    if any(not math.isfinite(x) or not -1 <= x <= 1 for x in si):
        raise ValueError("SI must be valid finite correlations")
    mean = sum(si) / 6
    return math.sqrt(sum((x - mean) ** 2 for x in si) / 6)


def synthetic_pair(k: int, i: int, case: str) -> tuple[float, float]:
    phase = 0.0 if i < 3 else math.pi
    def wave(step):
        return .5 + .5 * math.sin(2 * math.pi * step * DT + phase)
    predicted = wave(k)
    if case == "constant":
        return .5, .5
    if case == "gain-offset":
        actual = .2 + .5 * predicted  # remains in [0,1], affine mismatch
    elif case == "mixed-delay":
        actual = predicted if i < 3 else wave(k - 5)  # 0.25 s delay
    elif case == "all-inverted":
        actual = 1.0 - predicted
    elif case == "fault" and i == 0 and k == 300:
        actual = float("nan")
    else:
        actual = predicted
    return predicted, actual


def simulate_contact(case: str, duration: float = 30.0) -> tuple[list, dict]:
    if case not in CASES:
        raise ValueError("unknown contact case")
    count = grid_steps(duration, "duration")
    histories = {leg: ([], []) for leg in LEGS}
    rows = []
    for k in range(count):
        correlations, row = [], dict(sample=k, sample_time_s=round(k * DT, 10))
        for i, leg in enumerate(LEGS):
            predicted, actual = synthetic_pair(k, i, case)
            x, y = histories[leg]
            x.append(predicted)
            y.append(actual)
            si, reason = pearson(x[-WINDOW:], y[-WINDOW:])
            row.update({leg + "_expected": predicted, leg + "_actual": actual if math.isfinite(actual) else None,
                        leg + "_actual_raw": str(actual), leg + "_si": si,
                        leg + "_validity": reason,
                        leg + "_abs_error": abs(predicted - actual) if math.isfinite(actual) else None})
            correlations.append(si)
        sif = population_sif(correlations)
        row["sif"] = sif
        row["release_eq1_ci1"] = 1 / (1 + math.exp(-sif)) if sif is not None else None
        row["valid_legs"] = sum(si is not None for si in correlations)
        row["window_samples"] = min(k + 1, WINDOW)
        rows.append(row)
    valid = [row for row in rows if row["sif"] is not None]
    errors = [row[leg + "_abs_error"] for row in rows for leg in LEGS if row[leg + "_abs_error"] is not None]
    summary = dict(case=case, samples=count, valid_sif_rows=len(valid),
                   unavailable_sif_rows=count-len(valid),
                   mean_absolute_error=sum(errors) / len(errors),
                   mean_sif=sum(row["sif"] for row in valid) / len(valid) if valid else None,
                   mean_si={leg: (sum(row[leg + "_si"] for row in valid) / len(valid) if valid else None) for leg in LEGS},
                   first_valid_sample_s=valid[0]["sample_time_s"] if valid else None,
                   claim_boundary="synthetic paired signals; proposed Pearson definition; no robot/terrain/hormone feedback")
    return rows, summary


def run_contact(output_dir: Path, duration: float = 30.0) -> dict:
    data = {case: simulate_contact(case, duration) for case in CASES}
    prepare_output(output_dir)
    summary = {}
    for case, (rows, result) in data.items():
        write_csv(output_dir / (case + ".csv"), rows)
        summary[case] = result
    write_json(output_dir / "metrics.json", summary)
    write_json(output_dir / "config.json", dict(dt_s=DT, duration_s=duration, window_samples=WINDOW,
                window_inclusion="last 50 paired samples including current; first valid sample time=2.45 s, not 50*dt after first sample",
                generator="continuous sine contact proxy, 1 Hz; 3+3 opposite phase; not binary foot sensing",
                perturbations=dict(gain_offset="actual=.2+.5*expected", mixed_delay="last three legs delayed 5 samples=.25 s",
                                   all_inverted="actual=1-expected", fault="LF actual=NaN at sample_time=15.00 s"),
                correlation="paired-product Pearson; explicitly proposed course definition, not reproduction of printed Eq.(3)",
                sif="population SD across all six valid SI; unavailable if any leg invalid",
                release="printed Eq.(1), CI=1; Cg/HR/MI recurrence not run",
                randomness="none; deterministic synthetic input"))
    snapshot = output_dir / "source_snapshot"
    snapshot.mkdir()
    for name in ("contact_demo.py", "course_model.py", "lab05.py", "SOURCES.md",
                 "handoff_contract.json", "report_template.html"):
        shutil.copyfile(HERE / name, snapshot / name)
    table_rows = []
    for case, result in summary.items():
        si = result["mean_si"]["LF"]
        table_rows.append(f"<tr><td><a href='{case}.csv'>{case}</a></td><td>{result['valid_sif_rows']}</td>"
                          f"<td>{'N/A' if si is None else format(si,'.4f')}</td>"
                          f"<td>{'N/A' if result['mean_sif'] is None else format(result['mean_sif'],'.4f')}</td>"
                          f"<td>{result['mean_absolute_error']:.4f}</td></tr>")
    payload = json.dumps({case: rows for case, (rows, _) in data.items()}, allow_nan=False).replace("</", "<\\/")
    template = (HERE / "contact_report_template.html").read_text(encoding="utf-8")
    html = template.replace("__TABLE_ROWS__", "".join(table_rows)).replace("__DATA_JSON__", payload)
    (output_dir / "report.html").write_text(html, encoding="utf-8")
    shutil.copyfile(HERE / "contact_report_template.html", snapshot / "contact_report_template.html")
    write_json(output_dir / "manifest.json", {p.relative_to(output_dir).as_posix(): sha256(p)
                                              for p in sorted(output_dir.rglob("*")) if p.is_file()})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--output-dir", type=Path, default=Path("results/contact"))
    args = parser.parse_args()
    try:
        summary = run_contact(args.output_dir, args.duration)
    except (ValueError, OSError) as exc:
        parser.exit(2, "Contact demo: " + str(exc) + "\n")
    print(json.dumps({case: dict(valid_rows=m["valid_sif_rows"], mae=m["mean_absolute_error"], mean_sif=m["mean_sif"])
                      for case, m in summary.items()}, indent=2, allow_nan=False))
    print("Report: " + str(args.output_dir / "report.html"))


if __name__ == "__main__":
    main()
