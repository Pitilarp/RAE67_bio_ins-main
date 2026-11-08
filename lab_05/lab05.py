#!/usr/bin/env python3
"""Lab 05: scheduled-input AHM -> SO(2) -> tripod kinematics.

All controller/robot choices here are proposed course model. See SOURCES.md.
Run with Python 3.10+; the standard library is sufficient.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from pathlib import Path

from course_model import (LEGS, RATES, advance_body, decode, hormone_step,
                          mapped_parameters, step_cpg, valid_stimulus)

HERE = Path(__file__).resolve().parent
DT = 0.05
CONDITIONS = ("B0", "B1", "B2", "B3")
PROFILES = ("step", "zero", "one", "spike", "fault")
DESCRIPTIONS = {"B0": "Fixed R=0", "B1": "Direct R=S",
                "B2": "Hormone: production=.8 clearance=.6 binding=.2",
                "B3": "Binding ablation: production=.8 clearance=.6 binding=0"}
MODEL_BOUNDARY = "proposed course model; scheduled input; kinematic motion; no terrain/contact-force feedback"


def load_contract(path: Path) -> dict:
    contract = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "phi_rad": {"baseline": .20, "gain": .20, "bounds": [.10, .45]},
        "stride_half_m": {"baseline": .055, "gain": .010, "bounds": [.040, .070]},
    }
    if contract.get("controlled_parameters") != expected or contract.get("fixed_parameters") != {
            "alpha": 1.10, "dt_s": .05, "lift_height_m": .03}:
        raise ValueError("Contract differs from Lab03/04 values; use a separately documented model for changes")
    return contract


def grid_steps(seconds: float, name: str, allow_zero: bool = False) -> int:
    if not math.isfinite(seconds) or seconds < 0 or (seconds == 0 and not allow_zero):
        raise ValueError(name + " must be finite and " + ("nonnegative" if allow_zero else "positive"))
    n = round(seconds / DT)
    if n == 0 and not allow_zero:
        raise ValueError(name + " must contain at least one dt=0.05 s interval")
    if not math.isclose(n * DT, seconds, rel_tol=0, abs_tol=1e-9):
        raise ValueError(name + " must be a multiple of dt=0.05 s")
    return n


def stimulus(k: int, profile: str) -> float:
    if profile not in PROFILES:
        raise ValueError("unknown stimulus profile")
    if profile == "zero":
        return 0.0
    if profile == "one":
        return 1.0
    if profile == "spike":
        return float(k == 200)
    if profile == "fault" and k == 300:
        return float("nan")
    return float(200 <= k < 400)


def state_row(time: float, o1: float, o2: float, body: float, h, r: float,
              decoded: dict, feet: dict) -> dict:
    row = dict(state_time_s=round(time, 10), o1=o1, o2=o2, body_x_m=body,
               h=h, r=r, support_legs=sum(x["contact"] for x in decoded.values()))
    for leg, data in decoded.items():
        for key, value in data.items():
            row[leg + "_" + key] = value
        row[leg + "_foot_world_x_m"] = feet[leg]
    return row


def simulate(condition: str, profile: str = "step", mapping_mode: str = "both",
             duration: float = 30.0, warmup: float = 10.0, contract: dict | None = None) -> tuple:
    if condition not in CONDITIONS:
        raise ValueError("unknown condition")
    if profile not in PROFILES:
        raise ValueError("unknown stimulus profile")
    count, warm_count = grid_steps(duration, "duration"), grid_steps(warmup, "warmup", True)
    contract = load_contract(HERE / "handoff_contract.json") if contract is None else contract
    # Validate mode before warmup, including B0 trials.
    mapped_parameters(0.0, contract, mapping_mode)
    fixed = contract["fixed_parameters"]
    o1, o2 = .10, 0.0
    for _ in range(warm_count):
        o1, o2 = step_cpg(o1, o2, fixed["alpha"], .20)
    initial = dict(o1=o1, o2=o2, hormone_h=0.0 if condition in RATES else None,
                   receptor_r=0.0, body_x_m=0.0)
    h, r, body = initial["hormone_h"], 0.0, 0.0
    decoded = decode(o1, o2, .055, fixed["lift_height_m"])
    feet = {leg: data["x_rel_m"] for leg, data in decoded.items()}
    contact = {leg: data["contact"] for leg, data in decoded.items()}
    states = [state_row(0, o1, o2, body, h, r, decoded, feet)]
    intervals = []
    for k in range(count):
        s = stimulus(k, profile)
        fault = int(not valid_stimulus(s))
        h_before, r_before = h, r
        # Fault fallback precedes the command for this very interval.
        h_used = 0.0 if fault and h is not None else h
        if condition == "B0":
            r_used = 0.0
        elif condition == "B1":
            r_used = 0.0 if fault else s  # algebraic direct path at t_k
        else:
            r_used = 0.0 if fault else r
        cmd = mapped_parameters(r_used, contract, mapping_mode)
        old_o1, old_o2 = o1, o2
        o1, o2 = step_cpg(old_o1, old_o2, fixed["alpha"], cmd["phi_rad"])
        decoded = decode(o1, o2, cmd["stride_half_m"], fixed["lift_height_m"])
        body, feet, contact = advance_body(body, feet, contact, decoded)
        if condition in RATES:
            update = hormone_step(h_used, s, DT, RATES[condition])
            h, r = update["h"], update["r"]
        else:
            h, r = None, r_used
            update = dict(raw=None, p=None, c=None, b=None,
                          upper_clamp=0, lower_clamp=0)
        intervals.append(dict(
            step=k, input_time_s=round(k * DT, 10), command_time_s=round(k * DT, 10),
            state_time_s=round((k + 1) * DT, 10), stimulus=s if not fault else None,
            stimulus_raw="NaN" if fault else str(s), fault=fault,
            h_state_start=h_before, h_used=h_used, r_state_start=r_before, r_used=r_used,
            **cmd, h_raw=update["raw"], production=update["p"], clearance=update["c"],
            binding=update["b"], h_upper_clamp=update["upper_clamp"],
            h_lower_clamp=update["lower_clamp"], h_state_end=h, r_state_end=r,
            o1_start=old_o1, o2_start=old_o2, o1_end=o1, o2_end=o2))
        states.append(state_row((k + 1) * DT, o1, o2, body, h, r, decoded, feet))
    return states, intervals, initial


def total_variation(values: list[float]) -> float:
    return sum(abs(b - a) for a, b in zip(values, values[1:]))


def crossing_times(states: list[dict], start: float, end: float) -> list[float]:
    # Use the pair across each crossing; include an interpolated event only in
    # [start,end). Interpolation estimates timing, never fills missing sensor data.
    times = []
    for a, b in zip(states, states[1:]):
        if a["o1"] <= 0 < b["o1"]:
            fraction = -a["o1"] / (b["o1"] - a["o1"])
            time = a["state_time_s"] + fraction * (b["state_time_s"] - a["state_time_s"])
            if start <= time < end:
                times.append(time)
    return times


def segment_metrics(states: list[dict], intervals: list[dict], start: float, end: float) -> dict:
    left, right = round(start / DT), round(end / DT)
    segment_states = states[left:right + 1]
    segment_commands = intervals[left:right]
    crossings = crossing_times(states, start, end)
    periods = [b - a for a, b in zip(crossings, crossings[1:])]
    frequency = 1.0 / (sum(periods) / len(periods)) if periods else None
    distance = segment_states[-1]["body_x_m"] - segment_states[0]["body_x_m"]
    return dict(start_s=start, end_s=end, interval_count=len(segment_commands),
                distance_m=distance, mean_speed_m_s=distance / (end - start),
                frequency_hz=frequency, complete_period_count=len(periods),
                frequency_reason=None if periods else "fewer than two rising crossings in this segment",
                crossing_times_s=crossings,
                mean_phi_rad=sum(r["phi_rad"] for r in segment_commands) / len(segment_commands),
                mean_stride_half_m=sum(r["stride_half_m"] for r in segment_commands) / len(segment_commands),
                min_support_legs=min(r["support_legs"] for r in segment_states),
                max_support_legs=max(r["support_legs"] for r in segment_states))


def metrics(states: list[dict], intervals: list[dict], condition: str, profile: str,
            mapping_mode: str, contract: dict) -> dict:
    duration = states[-1]["state_time_s"]
    timing = dict(command_latency_s=None, command_recovery_s=None,
                  command_rise_10_90_s=None, state_latency_s=None)
    reasons = {}
    if profile == "step" and condition != "B0":
        on_commands = [r for r in intervals if 10 <= r["command_time_s"] < 20]
        on_states = [r for r in states if 10 <= r["state_time_s"] <= 20]
        peak = max((r["r_used"] for r in on_commands), default=0.0)
        def first(seq, time_field, field, threshold, below=False):
            return next((r[time_field] for r in seq if (r[field] <= threshold if below else r[field] >= threshold)), None)
        t = first(on_commands, "command_time_s", "r_used", .1)
        timing["command_latency_s"] = None if t is None else t - 10
        t = first(on_states, "state_time_s", "r", .1)
        timing["state_latency_s"] = None if t is None else t - 10
        if peak > 0:
            a = first(on_commands, "command_time_s", "r_used", .1 * peak)
            b = first(on_commands, "command_time_s", "r_used", .9 * peak)
            timing["command_rise_10_90_s"] = None if a is None or b is None else b - a
            off = [r for r in intervals if r["command_time_s"] >= 20]
            t = first(off, "command_time_s", "r_used", .1 * peak, below=True)
            timing["command_recovery_s"] = None if t is None else t - 20
        for name, value in timing.items():
            if value is None:
                reasons[name] = "event/threshold not observed before trial ended"
    else:
        reasons.update({name: "timing is defined only for B1/B2/B3 with step profile" for name in timing})
    base = mapped_parameters(0.0, contract, mapping_mode)
    # Includes transition from the declared initial baseline into command_0;
    # no imaginary command after the trial is included.
    phi = [base["phi_rad"]] + [r["phi_rad"] for r in intervals]
    stride = [base["stride_half_m"]] + [r["stride_half_m"] for r in intervals]
    segments = {}
    for name, start, end in (("pre", 0.0, 10.0), ("on", 10.0, 20.0), ("off", 20.0, duration)):
        end = min(end, duration)
        if end > start:
            segments[name] = segment_metrics(states, intervals, start, end)
    h_vals = [r["h"] for r in states if r["h"] is not None]
    return dict(condition=condition, profile=profile, mapping_mode=mapping_mode,
                duration_s=duration, state_rows=len(states), updates=len(intervals),
                distance_m=states[-1]["body_x_m"] - states[0]["body_x_m"],
                mean_speed_m_s=(states[-1]["body_x_m"] - states[0]["body_x_m"]) / duration,
                peak_h=max(h_vals) if h_vals else None,
                peak_r_used=max(r["r_used"] for r in intervals),
                auc_h_left_normalized_s=sum(r["h"] for r in states[:-1]) * DT if h_vals else None,
                phi_total_variation_rad=total_variation(phi),
                stride_total_variation_m=total_variation(stride),
                phi_max_step_rad=max(abs(b-a) for a, b in zip(phi, phi[1:])),
                stride_max_step_m=max(abs(b-a) for a, b in zip(stride, stride[1:])),
                fault_count=sum(r["fault"] for r in intervals),
                h_upper_clamp_fraction=sum(r["h_upper_clamp"] for r in intervals) / len(intervals) if h_vals else None,
                h_lower_clamp_fraction=sum(r["h_lower_clamp"] for r in intervals) / len(intervals) if h_vals else None,
                phi_clamp_count=sum(r["phi_rad_clamp"] for r in intervals),
                stride_clamp_count=sum(r["stride_half_m_clamp"] for r in intervals),
                **timing, na_reasons=reasons, segments=segments,
                paper_stability=None, paper_harmony=None, paper_displacement=None,
                paper_metric_reason="not measured: no body dynamics/sensor indices or declared Vmax/task normalization",
                claim_boundary=MODEL_BOUNDARY)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_output(path: Path) -> None:
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError("Output path is not an empty directory; choose a new directory to preserve existing results")
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def run(output_dir: Path, conditions: tuple = CONDITIONS, profile: str = "step",
        mapping_mode: str = "both", duration: float = 30.0, warmup: float = 10.0,
        contract_path: Path = HERE / "handoff_contract.json") -> dict:
    contract = load_contract(contract_path)
    # Validate and compute before creating output; an invalid request leaves no
    # partial result directory. Existing results are never overwritten.
    if not conditions or any(c not in CONDITIONS for c in conditions):
        raise ValueError("Select at least one valid condition")
    simulations = {c: simulate(c, profile, mapping_mode, duration, warmup, contract) for c in conditions}
    prepare_output(output_dir)
    summary, traces, initials = {}, {}, {}
    for condition, (states, intervals, initial) in simulations.items():
        write_csv(output_dir / (condition + "_states.csv"), states)
        write_csv(output_dir / (condition + "_intervals.csv"), intervals)
        summary[condition] = metrics(states, intervals, condition, profile, mapping_mode, contract)
        traces[condition] = dict(states=states, intervals=intervals)
        initials[condition] = initial
    config = dict(schema_version=1, dt_s=DT, duration_s=duration, warmup_s=warmup,
                  warmup_command=dict(alpha=1.10, phi_rad=.20),
                  warmup_reset="H/R, body origin, foot anchors, and logs reset after common baseline CPG warmup",
                  conditions={c: dict(description=DESCRIPTIONS[c], rates=RATES.get(c)) for c in conditions},
                  initial_states=initials, profile=profile, mapping_mode=mapping_mode,
                  schedule=dict(on_start_s=10, off_start_s=20, fault_input_s=15, spike_width_s=DT),
                  randomness="none; deterministic repeated runs are not independent trials",
                  time_convention="input/command t_k -> simultaneous CPG/body -> hormone end state t_(k+1); direct B1 uses S_k immediately",
                  contract_sha256=sha256(contract_path), claim_boundary=MODEL_BOUNDARY,
                  source=dict(doi="10.1109/ACCESS.2020.2992794", role="architecture/reference; this runner does not reproduce the paper controller"))
    write_json(output_dir / "config.json", config)
    write_json(output_dir / "metrics.json", summary)
    flat = [{k: v for k, v in m.items() if not isinstance(v, (dict, list))} for m in summary.values()]
    write_csv(output_dir / "metrics.csv", flat)
    segment_rows = [dict(condition=c, segment=s, **{k: v for k, v in m.items() if not isinstance(v, list)})
                    for c, metrics_c in summary.items() for s, m in metrics_c["segments"].items()]
    write_csv(output_dir / "segment_metrics.csv", segment_rows)
    shutil.copyfile(contract_path, output_dir / "handoff_contract.json")
    snapshot = output_dir / "source_snapshot"
    snapshot.mkdir()
    for name in ("lab05.py", "course_model.py", "report_template.html", "SOURCES.md"):
        shutil.copyfile(HERE / name, snapshot / name)
    shutil.copyfile(contract_path, snapshot / "handoff_contract.json")
    payload = json.dumps(dict(config=config, metrics=summary, traces=traces), ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    html = (HERE / "report_template.html").read_text(encoding="utf-8").replace("__DATA_JSON__", payload)
    (output_dir / "report.html").write_text(html, encoding="utf-8")
    files = sorted(p for p in output_dir.rglob("*") if p.is_file())
    write_json(output_dir / "manifest.json", {p.relative_to(output_dir).as_posix(): sha256(p) for p in files})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition", choices=("all", *CONDITIONS), default="all")
    parser.add_argument("--profile", choices=PROFILES, default="step")
    parser.add_argument("--mapping", choices=("both", "phi-only", "stride-only"), default="both")
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--warmup", type=float, default=10.0)
    parser.add_argument("--contract", type=Path, default=HERE / "handoff_contract.json")
    parser.add_argument("--output-dir", type=Path, default=Path("results/comparison"))
    args = parser.parse_args()
    try:
        selected = CONDITIONS if args.condition == "all" else (args.condition,)
        summary = run(args.output_dir, selected, args.profile, args.mapping,
                      args.duration, args.warmup, args.contract)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, "Lab05: " + str(exc) + "\n")
    print(json.dumps({c: dict(distance_m=m["distance_m"], command_latency_s=m["command_latency_s"],
                             command_recovery_s=m["command_recovery_s"], updates=m["updates"])
                      for c, m in summary.items()}, ensure_ascii=False, indent=2, allow_nan=False))
    print("Report: " + str(args.output_dir / "report.html"))


if __name__ == "__main__":
    main()
