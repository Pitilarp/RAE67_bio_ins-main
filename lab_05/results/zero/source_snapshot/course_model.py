"""Working teaching scaffold: proposed course model, not the paper's MNLC.

SO(2) recurrence/decoder: Lab 03. Bounded Euler hormone/mapping: Lab 04.
No imports of student code and no third-party dependencies.
"""
from __future__ import annotations

import math

LEGS = ("LF", "RM", "LH", "RF", "LM", "RH")
TRIPOD_SIGN = {leg: (1 if i < 3 else -1) for i, leg in enumerate(LEGS)}
RATES = {"B2": (0.8, 0.6, 0.2), "B3": (0.8, 0.6, 0.0)}


def clamp(x: float, low: float, high: float) -> float:
    return max(low, min(high, x))


def valid_stimulus(s: float) -> bool:
    return math.isfinite(s) and 0.0 <= s <= 1.0


def hormone_step(h: float, s: float, dt: float, rates: tuple) -> dict:
    if not math.isfinite(h) or not 0 <= h <= 1:
        raise ValueError("H state must be finite and within [0,1]")
    if not math.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be positive and finite")
    if len(rates) != 3 or any(not math.isfinite(x) or x < 0 for x in rates):
        raise ValueError("rates must be three nonnegative finite values")
    if not valid_stimulus(s):
        return dict(h=0.0, r=0.0, raw=0.0, p=0.0, c=0.0, b=0.0,
                    fault=1, upper_clamp=0, lower_clamp=0)
    prod, clear, bind = rates
    p, c, b = prod * s, clear * h, bind * h  # R_old=H_old
    raw = h + dt * (p - c - b)
    new_h = clamp(raw, 0.0, 1.0)
    return dict(h=new_h, r=new_h, raw=raw, p=p, c=c, b=b, fault=0,
                upper_clamp=int(raw > 1.0), lower_clamp=int(raw < 0.0))


def mapped_parameters(r: float, contract: dict, mode: str = "both") -> dict:
    if not math.isfinite(r) or not 0 <= r <= 1:
        raise ValueError("R must be finite and within [0,1]")
    if mode not in ("both", "phi-only", "stride-only"):
        raise ValueError("unknown mapping mode")
    values = {}
    for name, spec in contract["controlled_parameters"].items():
        active = mode == "both" or (mode == "phi-only" and name == "phi_rad") or (
            mode == "stride-only" and name == "stride_half_m")
        raw = spec["baseline"] + (spec["gain"] * r if active else 0.0)
        values[name] = clamp(raw, *spec["bounds"])
        values[name + "_raw"] = raw
        values[name + "_clamp"] = int(raw < spec["bounds"][0] or raw > spec["bounds"][1])
    return values


def step_cpg(o1: float, o2: float, alpha: float, phi: float) -> tuple[float, float]:
    """Both new outputs depend on the same old pair; Lab 03 convention."""
    c, s = math.cos(phi), math.sin(phi)
    return (math.tanh(alpha * (c * o1 + s * o2)),
            math.tanh(alpha * (-s * o1 + c * o2)))


def decode(o1: float, o2: float, stride_half: float, lift_height: float) -> dict:
    return {leg: dict(x_rel_m=stride_half * sign * o1,
                      lift_m=lift_height * max(0.0, sign * o2),
                      contact=int(sign * o2 <= 0.0),
                      hip_rad=0.55 * sign * o1)
            for leg, sign in TRIPOD_SIGN.items()}


def advance_body(body_x: float, foot_world: dict, old_contact: dict,
                 decoded: dict) -> tuple[float, dict, dict]:
    """Lab 03 stance-anchor constraints. Contact is from the decoder, not sensing.

    Newly grounded feet anchor at the old body pose. Existing stance anchors
    determine the new body pose by their mean; swing feet follow that new pose.
    No mass, force, slip, friction, CoM, terrain, or actuator dynamics.
    """
    feet = dict(foot_world)
    constraints = []
    for leg, state in decoded.items():
        if state["contact"] and not old_contact[leg]:
            feet[leg] = body_x + state["x_rel_m"]
        if state["contact"]:
            constraints.append(feet[leg] - state["x_rel_m"])
    new_x = sum(constraints) / len(constraints) if constraints else body_x
    for leg, state in decoded.items():
        if not state["contact"]:
            feet[leg] = new_x + state["x_rel_m"]
    return new_x, feet, {leg: state["contact"] for leg, state in decoded.items()}
