#!/usr/bin/env python3
"""Reproducible kinematic walking experiment driven by the Week 3 SO(2) CPG.

This is an intentionally small teaching simulator. It models gait timing and
foot placement, not rigid-body dynamics, contact forces, motor torque, or
stability of a physical robot.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


LEGS = ("LF", "RM", "LH", "RF", "LM", "RH")
TRIPOD_SIGN = {"LF": 1.0, "RM": 1.0, "LH": 1.0,
               "RF": -1.0, "LM": -1.0, "RH": -1.0}


@dataclass(frozen=True)
class Condition:
    name: str
    alpha: float
    phi: float
    description: str


CONDITIONS = {
    "baseline": Condition("baseline", 1.10, 0.20, "reference gait"),
    "fast": Condition("fast", 1.10, 0.40, "larger phase increment"),
    "high_gain": Condition("high_gain", 1.30, 0.20, "larger recurrent gain"),
}


def step_cpg(o1: float, o2: float, alpha: float, phi: float) -> tuple[float, float]:
    """One simultaneous SO(2) update using the equations from lec5.pptx."""
    c, s = math.cos(phi), math.sin(phi)
    a1 = alpha * (c * o1 + s * o2)
    a2 = alpha * (-s * o1 + c * o2)
    return math.tanh(a1), math.tanh(a2)


def rising_crossings(values: list[float]) -> list[int]:
    return [i for i in range(1, len(values)) if values[i - 1] <= 0.0 < values[i]]


def simulate(condition: Condition, dt: float, duration: float,
             warmup: float, stride_half: float, lift_height: float) -> tuple[list[dict], dict]:
    warmup_steps = round(warmup / dt)
    sample_steps = round(duration / dt)
    o1, o2 = 0.10, 0.00
    for _ in range(warmup_steps):
        o1, o2 = step_cpg(o1, o2, condition.alpha, condition.phi)

    body_x = 0.0
    foot_world = {leg: 0.0 for leg in LEGS}
    was_contact = {leg: False for leg in LEGS}
    rows: list[dict] = []

    for k in range(sample_steps + 1):
        t = k * dt
        leg_state = {}
        stance_constraints = []

        for leg in LEGS:
            sign = TRIPOD_SIGN[leg]
            x_rel = stride_half * sign * o1
            lift = lift_height * max(0.0, sign * o2)
            contact = sign * o2 <= 0.0
            leg_state[leg] = (x_rel, lift, contact)
            if contact and not was_contact[leg]:
                foot_world[leg] = body_x + x_rel
            if contact:
                stance_constraints.append(foot_world[leg] - x_rel)

        if stance_constraints:
            body_x = sum(stance_constraints) / len(stance_constraints)

        row = {
            "time_s": t,
            "body_x_m": body_x,
            "o1": o1,
            "o2": o2,
            "support_legs": sum(1 for state in leg_state.values() if state[2]),
        }
        for leg, (x_rel, lift, contact) in leg_state.items():
            if not contact:
                foot_world[leg] = body_x + x_rel
            row[f"{leg}_hip_rad"] = 0.55 * TRIPOD_SIGN[leg] * o1
            row[f"{leg}_lift_m"] = lift
            row[f"{leg}_contact"] = int(contact)
            row[f"{leg}_foot_world_x_m"] = foot_world[leg]
            was_contact[leg] = contact
        rows.append(row)
        o1, o2 = step_cpg(o1, o2, condition.alpha, condition.phi)

    initial_x = rows[0]["body_x_m"]
    for row in rows:
        row["body_x_m"] -= initial_x

    crossings = rising_crossings([row["o1"] for row in rows])
    periods = [(crossings[i] - crossings[i - 1]) * dt for i in range(1, len(crossings))]
    frequency = 1.0 / (sum(periods) / len(periods)) if periods else 0.0
    distance = rows[-1]["body_x_m"]
    support_values = [row["support_legs"] for row in rows]
    duty_factor = sum(row["LF_contact"] for row in rows) / len(rows)
    max_lift = max(row[f"{leg}_lift_m"] for row in rows for leg in LEGS)
    summary = {
        "condition": condition.name,
        "alpha": condition.alpha,
        "phi_rad": condition.phi,
        "dt_s": dt,
        "duration_s": duration,
        "warmup_s": warmup,
        "distance_m": round(distance, 6),
        "mean_speed_m_s": round(distance / duration, 6),
        "oscillation_frequency_hz": round(frequency, 6),
        "duty_factor_LF": round(duty_factor, 6),
        "minimum_support_legs": min(support_values),
        "maximum_support_legs": max(support_values),
        "maximum_foot_clearance_m": round(max_lift, 6),
        "model_scope": "kinematic teaching model; no rigid-body dynamics or contact forces",
    }
    return rows, summary


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def points(values: Iterable[float], x0: float, y0: float, width: float,
           height: float, ymin: float, ymax: float) -> str:
    vals = list(values)
    span = ymax - ymin or 1.0
    n = max(1, len(vals) - 1)
    return " ".join(
        f"{x0 + width * i / n:.2f},{y0 + height * (ymax - v) / span:.2f}"
        for i, v in enumerate(vals)
    )


def write_svg(path: Path, rows: list[dict], summary: dict) -> None:
    width, height = 1200, 720
    margin_x, chart_w = 90, 1040
    body = [row["body_x_m"] for row in rows]
    o1 = [row["o1"] for row in rows]
    o2 = [row["o2"] for row in rows]
    xmax = rows[-1]["time_s"]
    body_min, body_max = min(body), max(body)
    body_pad = max(0.01, (body_max - body_min) * 0.08)
    p_body = points(body, margin_x, 95, chart_w, 210, body_min - body_pad, body_max + body_pad)
    p_o1 = points(o1, margin_x, 410, chart_w, 200, -1.05, 1.05)
    p_o2 = points(o2, margin_x, 410, chart_w, 200, -1.05, 1.05)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="#ffffff"/>
<style>text{{font-family:Arial,sans-serif;fill:#21313c}} .axis{{stroke:#7d8b94;stroke-width:1}} .grid{{stroke:#dfe6ea;stroke-width:1}}</style>
<text x="60" y="45" font-size="26" font-weight="700">SO(2) CPG walking simulation — {summary['condition']}</text>
<text x="60" y="70" font-size="16">alpha={summary['alpha']}, phi={summary['phi_rad']} rad, duration={xmax:.1f} s, speed={summary['mean_speed_m_s']:.3f} m/s</text>
<rect x="{margin_x}" y="95" width="{chart_w}" height="210" fill="#f7fafb"/>
<line class="axis" x1="{margin_x}" y1="305" x2="{margin_x+chart_w}" y2="305"/>
<line class="axis" x1="{margin_x}" y1="95" x2="{margin_x}" y2="305"/>
<polyline points="{p_body}" fill="none" stroke="#006d77" stroke-width="4"/>
<text x="25" y="205" font-size="18" transform="rotate(-90 25 205)">body x (m)</text>
<text x="{margin_x+chart_w-150}" y="290" font-size="15">time (s)</text>
<rect x="{margin_x}" y="410" width="{chart_w}" height="200" fill="#f7fafb"/>
<line class="grid" x1="{margin_x}" y1="510" x2="{margin_x+chart_w}" y2="510"/>
<line class="axis" x1="{margin_x}" y1="610" x2="{margin_x+chart_w}" y2="610"/>
<line class="axis" x1="{margin_x}" y1="410" x2="{margin_x}" y2="610"/>
<polyline points="{p_o1}" fill="none" stroke="#006d77" stroke-width="3"/>
<polyline points="{p_o2}" fill="none" stroke="#e76f51" stroke-width="3"/>
<text x="25" y="545" font-size="18" transform="rotate(-90 25 545)">CPG output</text>
<line x1="870" y1="650" x2="915" y2="650" stroke="#006d77" stroke-width="4"/><text x="925" y="656" font-size="16">o1</text>
<line x1="1000" y1="650" x2="1045" y2="650" stroke="#e76f51" stroke-width="4"/><text x="1055" y="656" font-size="16">o2</text>
<text x="60" y="690" font-size="14" fill="#596a73">Kinematic teaching model: validates timing and foot-placement logic only.</text>
</svg>'''
    path.write_text(svg, encoding="utf-8")


def run_one(condition: Condition, output_dir: Path, dt: float,
            duration: float, warmup: float) -> dict:
    rows, summary = simulate(condition, dt, duration, warmup,
                             stride_half=0.055, lift_height=0.030)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / f"{condition.name}.csv", rows)
    write_svg(output_dir / f"{condition.name}.svg", rows, summary)
    (output_dir / f"{condition.name}_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", choices=[*CONDITIONS, "all"], default="all")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--dt", type=float, default=0.05)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--warmup", type=float, default=10.0)
    args = parser.parse_args()

    names = CONDITIONS if args.condition == "all" else [args.condition]
    summaries = [run_one(CONDITIONS[name], args.output_dir, args.dt,
                         args.duration, args.warmup) for name in names]
    if len(summaries) > 1:
        with (args.output_dir / "conditions_summary.csv").open(
                "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(summaries[0]))
            writer.writeheader()
            writer.writerows(summaries)
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
