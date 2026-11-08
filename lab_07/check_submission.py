"""Check a student's transition table in a separate, time-limited subprocess.

This removes inherited secrets/environment and Python startup hooks, but is not
an OS security sandbox. Only check code you trust; use a restricted OS account
or a disposable offline VM when grading code from other people.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

STATES = ("normal", "interested", "happy", "afraid", "sleepy")
EVENTS = ("fault", "near", "clear", "touch", "button", "approach", "timeout", "idle")


def check_outputs(outputs, contract):
    failures = []
    for (state, event), value in outputs.items():
        if value is not None and value not in STATES:
            failures.append({"state": state, "event": event, "actual": value,
                             "issue": "return a valid state name or None"})
    checks = [(s, "fault", "normal") for s in STATES]
    checks += [(s, "near", "afraid") for s in STATES]
    checks += [(s, "clear", "normal") for s in STATES]
    checks += [("afraid", e, None) for e in ("touch", "button", "approach", "timeout", "idle")]
    checks += [(s, "timeout", "normal") for s in ("interested", "happy")]
    checks += [(s, "timeout", None) for s in ("normal", "sleepy")]
    checks += [("normal", "idle", "sleepy")]
    checks += [(s, "idle", None) for s in ("interested", "happy", "sleepy")]
    if contract == "baseline":
        checks += [(s, "touch", "happy") for s in STATES if s != "afraid"]
        checks += [(s, e, "interested") for s in STATES if s != "afraid" for e in ("button", "approach")]
    else:
        for state in STATES:
            for event in ("button", "touch", "approach"):
                if state != "afraid" and outputs[state, event] not in ("interested", "happy"):
                    failures.append({"state": state, "event": event, "actual": outputs[state, event],
                                     "issue": "group positive input must enter interested or happy"})
    for state, event, required in checks:
        value = outputs[state, event]
        if value != required:
            failures.append({"state": state, "event": event, "actual": value,
                             "issue": f"transition does not satisfy the {contract} worksheet contract"})
    reached = {"normal"}
    while True:
        expanded = reached | {outputs[state, event] for state in reached for event in EVENTS
                              if outputs[state, event] in STATES}
        if expanded == reached:
            break
        reached = expanded
    if contract == "group" and set(STATES) != reached:
        failures.append({"state": "normal", "event": "reachability", "actual": sorted(reached),
                         "issue": "all five states must be reachable from normal"})
    return failures


def worker(path, contract):
    spec = importlib.util.spec_from_file_location("submission", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    outputs = {}
    for state in STATES:
        for event in EVENTS:
            value = module.transition(state, event)
            outputs[state, event] = value
    # Behavioral requirements are checks, not a second executable answer policy.
    failures = check_outputs(outputs, contract)
    print(json.dumps({"checked": len(outputs), "failure_count": len(failures), "failures": failures}))
    return bool(failures)


def main():
    parser = argparse.ArgumentParser(description="Check the 5 x 8 transition contract; starter has intentional TODO failures")
    parser.add_argument("--policy-file", default=str(Path(__file__).parent / "lamp_week07" / "student_policy.py"))
    parser.add_argument("--contract", choices=("baseline", "group"), default="baseline")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    path = Path(args.policy_file).resolve()
    if args.worker:
        return worker(path, args.contract)
    if not path.is_file():
        parser.error("Policy file does not exist")
    safe_env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "TEMP", "TMP") if key in os.environ}
    try:
        result = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--worker", "--policy-file", str(path),
                                 "--contract", args.contract],
                                cwd=path.parent, env=safe_env, timeout=5, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print("FAIL: policy exceeded 5 seconds; check loops/import side effects")
        return 1
    if result.returncode not in (0, 1):
        print("FAIL: policy process crashed")
        print(result.stderr[:2000])
        return 1
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("FAIL: policy printed unexpected output or failed to return a valid result")
        print(result.stderr[:2000])
        return 1
    print(f'Checked {data["checked"]} transition pairs; contract={args.contract}; failures={data["failure_count"]}')
    for failure in data["failures"]:
        print(f'  {failure["state"]} + {failure["event"]}: returned {failure["actual"]!r}; {failure["issue"]}')
    print("PASS: transition contract complete" if not data["failure_count"] else "FAIL: complete TODOs in student_policy.py, then check again")
    return bool(data["failure_count"])


if __name__ == "__main__":
    raise SystemExit(main())
