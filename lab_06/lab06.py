"""Deterministic offline lamp FSM runner (Python standard library only)."""
import argparse
from collections import Counter
import csv
from dataclasses import asdict
import hashlib
import html
import importlib.util
import json
import math
from pathlib import Path
import statistics

from course_model import (BOUNDS, Config, Event, Frame, PRIORITY, RGB, STATES,
                          SensorFilter, bounded_step, config_dict, protocol, target_pose)

ROOT = Path(__file__).resolve().parent


def load_policy(name="student"):
    path = ROOT / ("instructor/reference_policy.py" if name == "reference" else "student_policy.py")
    if not path.is_file():
        raise ValueError("Reference policy is instructor-only and is not included in the student package")
    spec = importlib.util.spec_from_file_location("lab06_policy", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.transition


def simulate(frames, transition, config=Config(), condition="C1"):
    """Decide -> queue -> apply; an FSM timestamp never counts as response onset."""
    guard = SensorFilter(config, condition == "C1")
    state, entry, last_activity = "normal", 0., 0.
    pose, color = (0., 0., 0.), RGB["normal"]
    events, rows, queue = [], [], []
    epoch, owner, command_clamps = 0, None, 0
    previous_time = None
    for frame in frames:
        t = frame.time_s
        if not math.isfinite(t) or t < 0 or (previous_time is not None and abs(t - previous_time - config.dt_s) > 1e-7):
            raise ValueError("Replay requires finite nonnegative times spaced exactly by dt_s")
        previous_time = t
        candidates, faults = guard.process(frame)
        if not faults:
            if state in ("interested", "happy") and t - entry >= config.active_timeout_s - 1e-9:
                candidates.append(guard.event("timeout", entry + config.active_timeout_s, t, "internal_timeout"))
            if state == "normal" and t - last_activity >= config.sleep_after_s - 1e-9:
                candidates.append(guard.event("idle", last_activity + config.sleep_after_s, t, "internal_idle"))
        candidates.sort(key=lambda e: PRIORITY[e.kind])
        if candidates:
            winner = candidates[0]
            for event in candidates:
                event.decision_time_s = t
                event.old_state = state
                if event is not winner:
                    event.status, event.reason = "discarded_priority", f"higher priority {winner.kind}"
            result = transition(state, winner.kind)
            if result is not None and result not in STATES:
                raise ValueError(f"Policy returned invalid state {result!r}")
            # Safety is common to both conditions and cannot be disabled by student code.
            if winner.kind == "fault":
                result = "normal"
            elif winner.kind == "near":
                result = "afraid"
            if state == "afraid" and winner.kind not in ("clear", "fault", "near"):
                result = None
            if winner.kind in ("button", "touch", "approach", "near", "clear"):
                last_activity = t
            if result is None:
                winner.status, winner.reason = "policy_held", "no transition / afraid guard"
            elif result == state:
                winner.status, winner.reason = "no_state_change", "same state; no new expression required"
                winner.new_state = result
            else:
                # Cancel all old-generation commands before applying anything at this tick.
                if owner is not None and owner.status in ("pending", "responded_partial"):
                    owner.status, owner.reason = ("preempted_before_apply" if owner.status == "pending" else "preempted_partial"), f"preempted by {winner.event_id}"
                queue.clear()
                epoch += 1
                state, entry, owner = result, t, winner
                winner.new_state, winner.status, winner.queued_time_s = state, "pending", t
            events.extend(candidates)
        # Sustained invalid data always requests neutral, including an already normal state.
        if faults:
            if owner is not None and owner.status == "pending" and owner.kind != "fault":
                owner.status, owner.reason = "preempted_before_apply", "sustained sensor fault"
            queue = [job for job in queue if job[3] is None or job[3].kind == "fault"]
            state = "normal"
        due = round(t + config.scheduler_delay_s, 8)
        queue.append((due, target_pose(state, max(0., t - entry)), RGB[state], owner, epoch))
        applied_owner = None
        applied_scheduled_s = None
        ready = [job for job in queue if job[0] <= t + 1e-9]
        queue = [job for job in queue if job[0] > t + 1e-9]
        for scheduled, desired, rgb, event, job_epoch in ready:
            if job_epoch != epoch:
                continue
            old_pose, old_rgb = pose, color
            pose, clamp_count = bounded_step(pose, desired, config)
            command_clamps += clamp_count
            color = tuple(max(0, min(255, int(v))) for v in rgb)
            applied_owner, applied_scheduled_s = event, scheduled
            if event is not None and event.status in ("pending", "responded_partial", "responded"):
                if event.applied_time_s is None:
                    event.applied_time_s = t
                if event.first_motion_s is None and any(abs(a - b) > 1e-9 for a, b in zip(old_pose, pose)):
                    event.first_motion_s = t
                if event.first_rgb_s is None and color != old_rgb:
                    event.first_rgb_s = t
                event.status = "responded" if event.first_motion_s is not None and event.first_rgb_s is not None else "responded_partial"
        rows.append({**asdict(frame), "sensor_faults": faults, "state": state,
                     "state_entry_s": entry, "queue_count": len(queue), "epoch": epoch,
                     "applied_event_id": applied_owner.event_id if applied_owner else "",
                     "scheduled_application_s": applied_scheduled_s,
                     "actual_application_s": t if applied_scheduled_s is not None else None,
                     "tilt_rad": pose[0], "extend_rad": pose[1], "nod_rad": pose[2],
                     "rgb_r": color[0], "rgb_g": color[1], "rgb_b": color[2]})
    for event in events:
        if event.status == "pending":
            event.status, event.reason = "censored_end", "no output application before trial end"
        elif event.status == "responded_partial":
            event.reason = "at least one output modality never changed before trial end"
    return rows, events, command_clamps


def event_dict(event):
    value = asdict(event)
    value["motion_latency_s"] = None if event.first_motion_s is None else round(event.first_motion_s - event.source_time_s, 8)
    value["rgb_latency_s"] = None if event.first_rgb_s is None else round(event.first_rgb_s - event.source_time_s, 8)
    both = max(event.first_motion_s, event.first_rgb_s) if event.first_motion_s is not None and event.first_rgb_s is not None else None
    value["both_onset_s"] = both
    value["both_latency_s"] = None if both is None else round(both - event.source_time_s, 8)
    value["pass_1s_both"] = None if both is None else value["both_latency_s"] <= 1. + 1e-9
    return value


def external_inputs(frames):
    inputs = {}
    for frame in frames:
        for channel in ("button", "touch", "distance"):
            input_id = getattr(frame, channel + "_input_id")
            if not input_id or input_id in inputs:
                continue
            kind = ("fault" if input_id.startswith(("stale", "invalid")) else
                    channel if channel != "distance" else frame.expected_event)
            inputs[input_id] = {"input_id": input_id, "kind": kind,
                                "source_time_s": getattr(frame, channel + "_source_s"),
                                "primary_expected_both": input_id in
                                ("button_01", "touch_01", "approach_01", "clear_01", "near_01", "clear_02", "button_02")}
    return list(inputs.values())


def summarize(frames, rows, events, condition, repeat, seed, clamps):
    edicts = [event_dict(e) for e in events]
    source_outcomes = []
    for source in external_inputs(frames):
        matches = [e for e in edicts if e["input_id"] == source["input_id"] and e["kind"] == source["kind"]]
        # Interaction-level onset can span candidates produced by the same original source.
        # Per-event attribution and cancellations remain independently available in events.csv.
        first = matches[0] if matches else None
        motion = min((e["first_motion_s"] for e in matches if e["first_motion_s"] is not None), default=None)
        rgb = min((e["first_rgb_s"] for e in matches if e["first_rgb_s"] is not None), default=None)
        both = max(motion, rgb) if motion is not None and rgb is not None else None
        motion_latency = round(motion - source["source_time_s"], 8) if motion is not None else None
        rgb_latency = round(rgb - source["source_time_s"], 8) if rgb is not None else None
        both_latency = round(both - source["source_time_s"], 8) if both is not None else None
        source_outcomes.append({**source, "recognized_count": len(matches),
                                "event_id": first["event_id"] if first else None,
                                "status": "responded" if both is not None else first["status"] if first else "filtered_not_recognized",
                                "first_candidate_status": first["status"] if first else None,
                                "candidate_status_counts": dict(Counter(e["status"] for e in matches)),
                                "first_motion_s": motion, "first_rgb_s": rgb, "both_onset_s": both,
                                "motion_latency_s": motion_latency, "rgb_latency_s": rgb_latency,
                                "both_latency_s": both_latency,
                                "pass_1s_both": None if both_latency is None else both_latency <= 1. + 1e-9})
    responded = [x for x in source_outcomes if x["both_latency_s"] is not None]
    primary = [x for x in source_outcomes if x["primary_expected_both"]]
    primary_onset = [x for x in primary if x["both_latency_s"] is not None]
    return {"condition": condition, "repeat": repeat, "seed": seed,
            "event_count": len(events), "external_input_count": len(source_outcomes),
            "external_responded_both_count": len(responded),
            "external_pass_1s_both_count": sum(x["pass_1s_both"] is True for x in responded),
            "external_no_both_onset_count": len(source_outcomes) - len(responded),
            "primary_expected_count": len(primary),
            "primary_both_onset_count": len(primary_onset),
            "primary_pass_1s_both_count": sum(x["pass_1s_both"] is True for x in primary_onset),
            "primary_missing_both_count": len(primary) - len(primary_onset),
            "max_both_latency_s": max((x["both_latency_s"] for x in responded), default=None),
            "median_both_latency_s": statistics.median([x["both_latency_s"] for x in responded]) if responded else None,
            "states_observed": sorted({row["state"] for row in rows}),
            "state_transition_count": sum(a["state"] != b["state"] for a, b in zip(rows, rows[1:])),
            "event_status_counts": dict(Counter(e.status for e in events)),
            "external_status_counts": dict(Counter(x["status"] for x in source_outcomes)),
            "command_clamp_count": clamps, "source_outcomes": source_outcomes,
            "latency_denominator": "all external inputs retained; pass count applies only to both observed onsets",
            "primary_denominator": "predeclared 7 baseline expression/recovery sources; excludes intentional conflict and already-neutral faults",
            "source_onset_aggregation": "earliest motion and RGB across all candidates with same input_id and kind; per-event onset retained separately",
            "claim_scope": "simulated commanded pose/RGB onset only; physical device response unmeasured"}


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_frames(path):
    frames = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            values = {key: float(value) if key not in ("button_input_id", "touch_input_id", "distance_input_id", "expected_event") else value
                      for key, value in row.items()}
            frames.append(Frame(**values))
    if not frames:
        raise ValueError("Replay CSV is empty")
    return frames


def fmt(value):
    return "N/A" if value is None else f"{value:.3f}" if isinstance(value, float) else str(value)


def trace_svg(rows, title):
    width, height, left, top = 900, 220, 55, 25
    duration = max(row["time_s"] for row in rows) or 1
    def line(field, bound, color):
        points = " ".join(f'{left + row["time_s"] / duration * 820:.1f},{110 - row[field] / bound * 70:.1f}' for row in rows)
        return f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.5"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">'
            '<rect width="900" height="220" fill="white"/><path d="M55 40V180H875M55 110H875" stroke="#ddd" fill="none"/>'
            f'<text x="55" y="18" font-size="14">{html.escape(title)} — semantic joints / own bound</text>'
            + line("tilt_rad", BOUNDS[0], "#0466c8") + line("extend_rad", BOUNDS[1], "#b45309")
            + line("nod_rad", BOUNDS[2], "#15803d")
            + f'<text x="55" y="205" font-size="13">0 s</text><text x="820" y="205" font-size="13">{duration:g} s</text>'
            '<text x="180" y="205" fill="#0466c8">tilt</text><text x="260" y="205" fill="#b45309">extend</text><text x="350" y="205" fill="#15803d">nod</text></svg>')


def write_report(output, runs, rows_by_run, config):
    summaries, charts, details = [], [], []
    for run in runs:
        tag = f'{run["condition"]}_r{run["repeat"]:02}'
        summaries.append("<tr>" + "".join(f"<td>{html.escape(fmt(run[field]))}</td>" for field in
            ("condition", "repeat", "seed", "state_transition_count", "external_input_count",
             "external_responded_both_count", "external_pass_1s_both_count", "external_no_both_onset_count",
             "primary_expected_count", "primary_pass_1s_both_count", "primary_missing_both_count", "max_both_latency_s")) + "</tr>")
        svg = trace_svg(rows_by_run[tag], tag)
        (output / f"trace_{tag}.svg").write_text(svg, encoding="utf-8")
        charts.append(f'<h3>{tag}</h3>{svg}<p>Observed states: {", ".join(run["states_observed"])}</p>')
        detail_rows = []
        for source in run["source_outcomes"]:
            detail_rows.append("<tr>" + "".join(f"<td>{html.escape(fmt(source[field]))}</td>" for field in
                ("input_id", "kind", "status", "recognized_count", "motion_latency_s", "rgb_latency_s", "both_latency_s")) + "</tr>")
        details.append(f'<details><summary>{tag}: every external input, including no onset</summary><table><tr><th>Input</th><th>Event</th><th>Status</th><th>Candidates</th><th>Motion s</th><th>RGB s</th><th>Both s</th></tr>{"".join(detail_rows)}</table></details>')
    text = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Lab06 lamp interaction</title><style>body{font:16px system-ui;margin:24px auto;max-width:1120px;color:#172334}table{border-collapse:collapse;width:100%;margin:14px 0}th,td{border:1px solid #d5dde5;padding:7px;text-align:left}th{background:#eef3f7}svg{width:100%;height:auto}code{background:#f0f3f7;padding:2px}details{padding:8px;border:1px solid #ddd;margin:8px 0}</style><h1>Lab06 — Lamp interaction</h1>'
    text += '<p><strong>Proposed course model. Synthetic offline simulation; fixed rules and parameters; no learning.</strong> C0 raw and C1 guarded use the same transition policy, movement, RGB, safety, scheduler and paired seeds.</p>'
    text += '<p>Response latency = source interaction time to the first actually applied pose/RGB change. Both = max(motion onset, RGB onset) only when both occur. A decision or queued command is not a response. N/A means no measured onset; discarded, held, no state change, preempted and censored inputs remain visible. Simulated ≤1 s does not certify physical device timing.</p>'
    text += '<table><tr><th>Condition</th><th>Repeat</th><th>Seed</th><th>Transitions</th><th>All sources</th><th>Both onset</th><th>≤1s both</th><th>No both onset</th><th>Primary expected</th><th>Primary ≤1s</th><th>Primary missing</th><th>Max observed s</th></tr>' + ''.join(summaries) + '</table>'
    text += '<p>Primary expectation is declared before running: seven button/touch/approach/near/clear expression or recovery inputs. Intentional conflicting touch and two already-neutral fault inputs remain in all ten sources. Source-level motion and RGB onset use the earliest observations across all candidates with the same input ID and event kind; these may belong to different candidate events. Candidate-level latency, cancellations and statuses remain in events CSV and JSON.</p>'
    text += '<p>Seeded synthetic replications test behavior under specified noise, not independent physical trials. Do not interpret observed-onset success as success for all sources. Read source statuses and raw CSV before a claim.</p>'
    text += ''.join(details) + ''.join(charts)
    text += '<h2>Configuration</h2><pre>' + html.escape(json.dumps(config_dict(config), ensure_ascii=False, indent=2)) + '</pre></html>'
    (output / "report.html").write_text(text, encoding="utf-8")


def run(output, policy="student", conditions=("C0", "C1"), repeats=3, replay=None, config=Config()):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory is not empty; choose a new directory to preserve raw results")
    output.mkdir(parents=True, exist_ok=True)
    transition = load_policy(policy)
    runs, rows_by_run = [], {}
    for repeat in range(1, repeats + 1):
        # Replay does not draw new random values; do not falsely label the recorded
        # input with this run's default seed when the original seed is unavailable.
        seed = None if replay else config.seed + repeat - 1
        frames = read_frames(replay) if replay else protocol(config, seed)
        if replay and (len(frames) != round(config.duration_s / config.dt_s) + 1
                       or abs(frames[0].time_s) > 1e-9 or abs(frames[-1].time_s - config.duration_s) > 1e-9):
            raise ValueError("Replay requires the saved 0..22 s baseline protocol at dt=.02 s")
        write_csv(output / f"inputs_r{repeat:02}.csv", [asdict(f) for f in frames])
        write_csv(output / f"source_inputs_r{repeat:02}.csv", external_inputs(frames))
        for condition in conditions:
            tag = f"{condition}_r{repeat:02}"
            rows, events, clamps = simulate(frames, transition, config, condition)
            write_csv(output / f"raw_{tag}.csv", rows)
            write_csv(output / f"events_{tag}.csv", [event_dict(e) for e in events])
            metrics = summarize(frames, rows, events, condition, repeat, seed, clamps)
            runs.append(metrics)
            rows_by_run[tag] = rows
    saved_config = {**config_dict(config), "policy": policy, "conditions": list(conditions),
                    "repeat_count": repeats, "replay": Path(replay).name if replay else None,
                    "replay_input_sha256": hashlib.sha256(Path(replay).read_bytes()).hexdigest() if replay else None,
                    "replay_seed": "unavailable; recorded inputs used without a new random draw" if replay else None}
    (output / "config.json").write_text(json.dumps(saved_config, indent=2), encoding="utf-8")
    (output / "metrics.json").write_text(json.dumps({"schema_version": 1, "runs": runs}, indent=2), encoding="utf-8")
    scalar_metrics = [{key: value for key, value in run_metrics.items() if not isinstance(value, (dict, list))}
                      for run_metrics in runs]
    write_csv(output / "metrics.csv", scalar_metrics)
    write_report(output, runs, rows_by_run, config)
    snapshot = output / "source_snapshot"
    snapshot.mkdir()
    sources = [ROOT / "course_model.py", ROOT / "lab06.py", ROOT / "student_policy.py", ROOT / "interface_contract.json"]
    if policy == "reference":
        sources.append(ROOT / "instructor/reference_policy.py")
    for path in sources:
        target = snapshot / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    files = sorted(path for path in output.rglob("*") if path.is_file())
    manifest = {str(path.relative_to(output)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", choices=("student", "reference"), default="student")
    parser.add_argument("--condition", choices=("all", "C0", "C1"), default="all")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output-dir", default="results/student_run")
    parser.add_argument("--replay", help="Replay saved inputs_rNN.csv with the same dt/config")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be >=1; use >=3 for the required comparison")
    if args.replay and args.repeats != 1:
        parser.error("Replay one recorded input file with --repeats 1")
    conditions = ("C0", "C1") if args.condition == "all" else (args.condition,)
    try:
        runs = run(args.output_dir, args.policy, conditions, args.repeats, args.replay)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    for metric in runs:
        print(f'{metric["condition"]} r{metric["repeat"]:02} seed={metric["seed"]}: transitions={metric["state_transition_count"]}; '
              f'both onset={metric["external_responded_both_count"]}/{metric["external_input_count"]}; '
              f'observed <=1s={metric["external_pass_1s_both_count"]}; no both onset={metric["external_no_both_onset_count"]}; '
              f'max observed={fmt(metric["max_both_latency_s"])}s')
    print(f"Offline report: {Path(args.output_dir) / 'report.html'}")


if __name__ == "__main__":
    main()
