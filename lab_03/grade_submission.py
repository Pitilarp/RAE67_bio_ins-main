#!/usr/bin/env python3
"""Behavioral checker for a Lab 03 student_cpg.py submission."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import traceback
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("lab03_student", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def close(a: float, b: float, tol: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def check(name, fn):
    try:
        fn()
        return {"name": name, "passed": True, "detail": "OK"}
    except Exception as exc:  # report student-facing failure without stopping other checks
        return {"name": name, "passed": False,
                "detail": f"{type(exc).__name__}: {exc}"}


def evaluate(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    module = load_module(path)

    def no_todos():
        if "TODO 1" in source or "TODO 2" in source or "TODO 3" in source:
            raise AssertionError("พบ TODO ที่ยังไม่เสร็จ")

    def so2_equation():
        got = module.so2_step(0.10, -0.20, 1.10, 0.20)
        c, s = math.cos(0.20), math.sin(0.20)
        expected = (math.tanh(1.10 * (c * 0.10 + s * -0.20)),
                    math.tanh(1.10 * (-s * 0.10 + c * -0.20)))
        if not all(close(a, b) for a, b in zip(got, expected)):
            raise AssertionError(f"expected {expected}, got {got}")

    def simultaneous_update():
        got = module.so2_step(0.33, 0.27, 1.17, 0.31)
        c, s = math.cos(0.31), math.sin(0.31)
        expected2 = math.tanh(1.17 * (-s * 0.33 + c * 0.27))
        if not close(got[1], expected2):
            raise AssertionError("o2 ใหม่ต้องคำนวณจาก o1,o2 เวลาเดิม")

    def tripod_decoder():
        state = module.decode_tripod(0.4, 0.6, 0.05, 0.03)
        if set(state) != {"LF", "RM", "LH", "RF", "LM", "RH"}:
            raise AssertionError("ชื่อขาไม่ครบหกขา")
        if any(state[x]["contact"] for x in ("LF", "RM", "LH")):
            raise AssertionError("เมื่อ o2>0 Tripod A ต้องเป็น swing")
        if not all(state[x]["contact"] for x in ("RF", "LM", "RH")):
            raise AssertionError("เมื่อ o2>0 Tripod B ต้องเป็น stance")
        if not all(state[x]["lift"] > 0 for x in ("LF", "RM", "LH")):
            raise AssertionError("Tripod A ต้องมี lift เป็นบวก")

    def bounded_mapping():
        normal = module.bounded_modulation(1.0)
        high = module.bounded_modulation(99.0)
        low = module.bounded_modulation(-99.0)
        if not (close(normal[0], 0.40) and close(normal[1], 0.065)):
            raise AssertionError(f"mapping m=1 ไม่ถูกต้อง: {normal}")
        if high[0] > 0.45 or high[1] > 0.070 or low[0] < 0.10 or low[1] < 0.040:
            raise AssertionError("คำสั่งต้องไม่ออกนอก bounds")

    checks = [
        check("ไม่มี TODO ค้าง", no_todos),
        check("สมการ SO(2)", so2_equation),
        check("simultaneous update", simultaneous_update),
        check("alternating tripod decoder", tripod_decoder),
        check("bounded Week 4 handoff", bounded_mapping),
    ]
    return {
        "student_file": str(path.resolve()),
        "passed": all(c["passed"] for c in checks),
        "passed_count": sum(c["passed"] for c in checks),
        "total_count": len(checks),
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--student-file", type=Path, default=Path("student_cpg.py"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.student_file)
    except Exception as exc:
        result = {"student_file": str(args.student_file), "passed": False,
                  "fatal_error": f"{type(exc).__name__}: {exc}",
                  "traceback": traceback.format_exc()}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    raise SystemExit(0 if result.get("passed") else 1)


if __name__ == "__main__":
    main()
