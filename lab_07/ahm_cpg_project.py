"""Paired offline AHM-to-SO(2) CPG project simulation.

This is a proposed course model, not ROS/DDS or physical robot validation.
"""
import argparse
import csv
import hashlib
import html
import json
import math
from pathlib import Path
import statistics


DT_S = 0.05
DURATION_S = 40.0
WARMUP_END_S = 10.0
STIMULUS_DURATION_S = 10.0
CPG_ALPHA = 1.10
AHM_RATES = (0.8, 0.6, 0.2)
NOD_AMPLITUDE_RAD = 0.10
MAX_SLEW_RAD_S = 0.8
ACTUATOR_TAU_S = 0.15
SEEDS = (41, 42, 43)


def clamp(value, low, high):
    return max(low, min(high, value))


def positive_crossings(samples, start_s, end_s):
    crossings = []
    previous = None
    for row in samples:
        if not start_s <= row["time_s"] <= end_s:
            continue
        current = (row["time_s"], row["applied_nod_rad"])
        if previous is not None and previous[1] <= 0.0 < current[1]:
            t0, y0 = previous
            t1, y1 = current
            fraction = -y0 / (y1 - y0)
            crossings.append(t0 + fraction * (t1 - t0))
        previous = current
    return crossings


def simulate(condition, seed):
    if condition not in ("C0", "C1"):
        raise ValueError(f"Unknown condition: {condition}")
    if seed not in SEEDS:
        raise ValueError(f"Seed must be one of {SEEDS}")

    # Pair-wise source timing: every seed uses the same trace in C0 and C1.
    source_offset_s = (seed - SEEDS[0]) * DT_S
    stimulus_on_s = WARMUP_END_S + source_offset_s
    stimulus_off_s = stimulus_on_s + STIMULUS_DURATION_S

    h = 0.0
    o1, o2 = 0.10, 0.0
    applied_nod = 0.0
    samples = []
    steps = round(DURATION_S / DT_S)
    for index in range(steps + 1):
        t = round(index * DT_S, 10)
        stimulus = float(stimulus_on_s <= t < stimulus_off_s)
        r_old = clamp(h, 0.0, 1.0)
        p = AHM_RATES[0] * stimulus
        c = AHM_RATES[1] * h
        b = AHM_RATES[2] * r_old
        raw_h = h + DT_S * (p - c - b)
        h = clamp(raw_h, 0.0, 1.0)
        receptor = clamp(h, 0.0, 1.0)

        if condition == "C0":
            phi = 0.20
        else:
            phi = clamp(0.20 + 0.20 * receptor, 0.10, 0.45)

        cosine, sine = math.cos(phi), math.sin(phi)
        a1 = CPG_ALPHA * (cosine * o1 + sine * o2)
        a2 = CPG_ALPHA * (-sine * o1 + cosine * o2)
        next_o1, next_o2 = math.tanh(a1), math.tanh(a2)
        o1, o2 = next_o1, next_o2
        target_nod = NOD_AMPLITUDE_RAD * o1
        desired_step = (target_nod - applied_nod) * min(1.0, DT_S / ACTUATOR_TAU_S)
        max_step = MAX_SLEW_RAD_S * DT_S
        applied_nod += clamp(desired_step, -max_step, max_step)
        samples.append({
            "time_s": t,
            "source_id": "project_stimulus_seed_" + str(seed),
            "stimulus": stimulus,
            "h": h,
            "receptor": receptor,
            "production_per_s": p,
            "clearance_per_s": c,
            "binding_per_s": b,
            "phi_rad_per_update": phi,
            "alpha": CPG_ALPHA,
            "o1": o1,
            "o2": o2,
            "target_nod_rad": target_nod,
            "applied_nod_rad": applied_nod,
        })

    frequency_crossings = positive_crossings(samples, stimulus_on_s, stimulus_off_s)
    frequency_hz = (
        (len(frequency_crossings) - 1) /
        (frequency_crossings[-1] - frequency_crossings[0])
        if len(frequency_crossings) >= 2 else None
    )
    analyzed = [row for row in samples
                if WARMUP_END_S <= row["time_s"] <= DURATION_S]
    rmse = math.sqrt(statistics.mean(
        (row["applied_nod_rad"] - row["target_nod_rad"]) ** 2
        for row in analyzed
    ))
    metrics = {
        "condition": condition,
        "seed": seed,
        "source_offset_s": source_offset_s,
        "stimulus_on_s": stimulus_on_s,
        "stimulus_off_s": stimulus_off_s,
        "frequency_window_s": STIMULUS_DURATION_S,
        "positive_crossings_during_stimulus": len(frequency_crossings),
        "nod_frequency_hz": frequency_hz,
        "tracking_rmse_rad": rmse,
        "rmse_window_start_s": WARMUP_END_S,
        "rmse_window_end_s": DURATION_S,
        "rmse_sample_count": len(analyzed),
        "mean_phi_during_stimulus_rad": statistics.mean(
            row["phi_rad_per_update"] for row in samples
            if stimulus_on_s <= row["time_s"] < stimulus_off_s
        ),
        "final_h": h,
        "physical_measurement": "N/A; semantic applied command in offline model only",
        "measurement_scope": "offline proposed course model; no ROS/DDS/hardware",
    }
    return samples, metrics


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(output_dir):
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"Output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    all_metrics = []
    for seed in SEEDS:
        for condition in ("C0", "C1"):
            samples, metrics = simulate(condition, seed)
            folder = output_dir / f"{condition}_seed{seed}"
            folder.mkdir()
            write_csv(folder / "trace.csv", samples)
            (folder / "metrics.json").write_text(
                json.dumps(metrics, ensure_ascii=False, indent=2, allow_nan=False),
                encoding="utf-8",
            )
            (folder / "config.json").write_text(json.dumps({
                "provenance": "proposed course model",
                "condition": condition,
                "seed": seed,
                "paired_source_offset_s": metrics["source_offset_s"],
                "dt_s": DT_S,
                "duration_s": DURATION_S,
                "warmup_end_s": WARMUP_END_S,
                "stimulus_duration_s": STIMULUS_DURATION_S,
                "cpg_alpha": CPG_ALPHA,
                "ahm_rates": {
                    "k_prod_normalized_h_per_s": AHM_RATES[0],
                    "k_clear_per_s": AHM_RATES[1],
                    "k_bind_normalized_h_per_s": AHM_RATES[2],
                },
                "nod_amplitude_rad": NOD_AMPLITUDE_RAD,
                "actuator_time_constant_s": ACTUATOR_TAU_S,
                "max_slew_rad_s": MAX_SLEW_RAD_S,
                "integration": (
                    "C0 fixed phi=.20 rad/update; C1 phi=clamp(.20+.20*R,.10,.45)"
                ),
                "physical_hardware": "not connected or measured",
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            all_metrics.append(metrics)

    summary = []
    for condition in ("C0", "C1"):
        items = [item for item in all_metrics if item["condition"] == condition]
        frequencies = [item["nod_frequency_hz"] for item in items
                       if item["nod_frequency_hz"] is not None]
        summary.append({
            "condition": condition,
            "repeats": len(items),
            "seeds": [item["seed"] for item in items],
            "mean_nod_frequency_hz": statistics.mean(frequencies) if frequencies else None,
            "nod_frequency_observed_trials": len(frequencies),
            "mean_tracking_rmse_rad": statistics.mean(
                item["tracking_rmse_rad"] for item in items
            ),
            "physical_trials": 0,
            "interpretation": "offline synthetic simulation only",
        })
    (output_dir / "summary.json").write_text(
        json.dumps({"trials": all_metrics, "conditions": summary},
                   ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    rows = "".join(
        "<tr>" + "".join(
            f"<td>{html.escape('N/A' if item[key] is None else str(item[key]))}</td>"
            for key in ("condition", "seed", "nod_frequency_hz", "tracking_rmse_rad",
                        "mean_phi_during_stimulus_rad", "physical_measurement")
        ) + "</tr>"
        for item in all_metrics
    )
    (output_dir / "report.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>AHM-CPG project simulation</title>"
        "<style>body{font-family:sans-serif;margin:2em}table{border-collapse:collapse}"
        "td,th{border:1px solid #bbb;padding:.5em}</style>"
        "<h1>Paired AHM–SO(2) CPG project simulation</h1>"
        "<p>Proposed course model; offline semantic actuator only. "
        "No ROS/DDS, physical robot, or participant trials.</p>"
        "<table><tr><th>Condition</th><th>Seed</th><th>Frequency (Hz)</th>"
        "<th>Tracking RMSE (rad)</th><th>Mean phi (rad/update)</th>"
        "<th>Physical measurement</th></tr>" + rows + "</table>",
        encoding="utf-8",
    )
    manifest = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            manifest[path.relative_to(output_dir).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    (output_dir / "manifest.json").write_text(json.dumps({
        "sha256": manifest,
        "immutability": "preserve raw project results; rerun into a new directory",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="results/project_ahm_cpg")
    args = parser.parse_args()
    try:
        summary = run(Path(args.output_dir))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    for item in summary:
        print(
            f"{item['condition']}: repeats={item['repeats']} "
            f"mean_frequency={item['mean_nod_frequency_hz']} Hz "
            f"mean_RMSE={item['mean_tracking_rmse_rad']} rad"
        )
    print(f"Wrote offline project simulation to {args.output_dir}; physical latency=N/A")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
