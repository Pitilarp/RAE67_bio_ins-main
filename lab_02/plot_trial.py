"""Create the required Lab 02 time-series plot from one trial CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def optional_float(value: str) -> float | None:
    return None if value == "" else float(value)


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def plot_trial(csv_path: Path, output_path: Path) -> None:
    rows = load_rows(csv_path)
    if not rows:
        raise ValueError(f"empty CSV: {csv_path}")

    time_s = [float(row["time_s"]) for row in rows]
    true_distance = [float(row["true_distance_m"]) for row in rows]
    raw_distance = [optional_float(row["raw_distance_m"]) for row in rows]
    filtered_distance = [optional_float(row["filtered_distance_m"]) for row in rows]
    command = [float(row["command"]) for row in rows]
    state = [1 if row["state"] == "NEAR" else 0 for row in rows]
    condition = rows[0]["condition"]

    figure, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, constrained_layout=True)
    distance_ax, command_ax = axes

    distance_ax.plot(time_s, true_distance, color="#161616", linewidth=2, label="true distance")
    distance_ax.plot(time_s, raw_distance, color="#A7ADB1", linewidth=1, alpha=0.8, label="raw")
    if any(value is not None for value in filtered_distance):
        distance_ax.plot(time_s, filtered_distance, color="#147A8C", linewidth=2, label="filtered")
    distance_ax.axhline(0.35, color="#B84A4A", linestyle="--", linewidth=1.5, label="T = 0.35 m")
    if condition == "C2":
        distance_ax.axhline(0.32, color="#147A8C", linestyle=":", linewidth=1.2, label="T_enter")
        distance_ax.axhline(0.38, color="#C17824", linestyle=":", linewidth=1.2, label="T_exit")
    distance_ax.set_ylabel("distance (m)")
    distance_ax.grid(True, alpha=0.25)
    distance_ax.legend(loc="best", ncol=3)

    command_ax.plot(time_s, command, color="#C17824", linewidth=2, label="command")
    command_ax.step(time_s, state, where="post", color="#147A8C", linewidth=1.5, label="state: NEAR=1")
    command_ax.set_xlabel("time (s)")
    command_ax.set_ylabel("command / state")
    command_ax.grid(True, alpha=0.25)
    command_ax.legend(loc="best")

    for row in rows:
        if row["event_label"] in ("ENTER_NEAR", "EXIT_NEAR", "INVALID"):
            time = float(row["time_s"])
            command_ax.axvline(time, color="#B84A4A", alpha=0.25, linewidth=0.8)

    figure.suptitle(
        f"{rows[0]['trial_id']} | {condition} | sigma={rows[0]['noise_sigma_m']} m | delay={rows[0]['delay_ms']} ms"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    output_path = args.out or args.csv_path.with_suffix(".png")
    plot_trial(args.csv_path, output_path)
    print(f"wrote plot to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
