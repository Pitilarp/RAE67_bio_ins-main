"""Offline lamp model. Every numeric value/mapping is a proposed course model."""
from dataclasses import asdict, dataclass
import math
import random

STATES = ("normal", "interested", "happy", "afraid", "sleepy")
PRIORITY = {name: i for i, name in enumerate(
    ("fault", "near", "clear", "touch", "button", "approach", "timeout", "idle"))}
BOUNDS = (.35, .25, .30)  # Semantic tilt/extend/nod [rad], not a robot linkage.
RGB = {"normal": (60, 90, 140), "interested": (255, 180, 0),
       "happy": (40, 220, 80), "afraid": (230, 30, 30), "sleepy": (50, 40, 100)}


@dataclass(frozen=True)
class Config:
    dt_s: float = .02
    duration_s: float = 22.
    scheduler_delay_s: float = .04
    debounce_s: float = .06
    stale_s: float = .12
    near_enter_m: float = .20
    near_exit_m: float = .28
    approach_enter_m: float = .80
    approach_exit_m: float = .95
    active_timeout_s: float = 2.
    sleep_after_s: float = 6.
    max_slew_rad_s: float = .8
    seed: int = 41


@dataclass(frozen=True)
class Frame:
    time_s: float
    button: float
    touch: float
    distance_m: float
    button_sample_s: float
    touch_sample_s: float
    distance_sample_s: float
    button_source_s: float
    touch_source_s: float
    distance_source_s: float
    button_input_id: str = ""
    touch_input_id: str = ""
    distance_input_id: str = ""
    expected_event: str = ""


@dataclass
class Event:
    event_id: str
    kind: str
    source_time_s: float
    recognized_time_s: float
    input_id: str
    status: str = "candidate"
    decision_time_s: float | None = None
    queued_time_s: float | None = None
    first_motion_s: float | None = None
    first_rgb_s: float | None = None
    applied_time_s: float | None = None
    old_state: str = ""
    new_state: str = ""
    reason: str = ""


def target_pose(state, elapsed_s):
    return {"normal": (0., 0., 0.), "interested": (.22, .18, .06),
            "happy": (.10, .10, .18 * math.sin(2 * math.pi * elapsed_s)),
            "afraid": (-.22, -.22, -.16), "sleepy": (0., -.15, -.20)}[state]


def bounded_step(current, desired, config):
    if len(desired) != 3 or not all(math.isfinite(v) for v in desired):
        raise ValueError("Pose must contain three finite radian values")
    step = config.max_slew_rad_s * config.dt_s
    clamped = tuple(max(-bound, min(bound, value)) for value, bound in zip(desired, BOUNDS))
    output = tuple(a + max(-step, min(step, b - a)) for a, b in zip(current, clamped))
    return output, sum(a != b for a, b in zip(desired, clamped))


def protocol(config, seed):
    """Synthetic input truth and seeded noise; repeat seeds are paired across C0/C1."""
    rng = random.Random(seed)
    frames = []
    for n in range(round(config.duration_s / config.dt_s) + 1):
        t = round(n * config.dt_s, 8)
        button, touch, distance = 0., 0., 1.2
        bs, ts, ds = t, t, t
        bi = ti = di = expected = ""
        if 1 <= t < 1.24:
            button = float(t >= 1.06 or n % 2 == 0)
            bs, bi = 1., "button_01"
            expected = "button"
        if 3 <= t < 3.22:
            touch, ts, ti, expected = 1., 3., "touch_01", "touch"
        if 5 <= t < 6.4:
            distance, ds, di, expected = .79, 5., "approach_01", "approach"
        if 6.4 <= t < 7:
            ds, di, expected = 6.4, "clear_01", "clear"
        if 7 <= t < 9:
            distance, ds, di, expected = .18, 7., "near_01", "near"
        if 7 <= t < 7.22:
            touch, ts, ti = 1., 7., "touch_conflict"
        if 9 <= t < 11:
            ds, di, expected = 9., "clear_02", "clear"
        if 11 <= t < 11.14:
            distance, ds, di, expected = float("nan"), 11., "invalid_01", "fault"
        touch_sample = t - .5 if 12 <= t < 12.26 else t
        if 12 <= t < 12.26:
            ts, ti, expected = 12., "stale_01", "fault"
        if 18 <= t < 18.22:
            button, bs, bi, expected = 1., 18., "button_02", "button"
        if math.isfinite(distance):
            distance += rng.uniform(-.035, .035)
        frames.append(Frame(t, button, touch, distance, t, touch_sample, t,
                            bs, ts, ds, bi, ti, di, expected))
    return frames


class SensorFilter:
    def __init__(self, config, guarded):
        self.config, self.guarded = config, guarded
        self.digital = {k: {"raw": False, "stable": False, "since": 0., "source": 0., "id": ""}
                        for k in ("button", "touch")}
        self.near = self.approach = False
        self.faulted = False
        self.counter = 0

    def event(self, kind, source, now, input_id):
        self.counter += 1
        return Event(f"e{self.counter:04}", kind, source, now, input_id)

    def process(self, frame):
        cfg, now = self.config, frame.time_s
        faults = []
        for channel in ("button", "touch", "distance"):
            value = getattr(frame, "distance_m" if channel == "distance" else channel)
            sampled = getattr(frame, channel + "_sample_s")
            source = getattr(frame, channel + "_source_s")
            valid_value = math.isfinite(value) and (0 <= value <= 4 if channel == "distance" else value in (0, 1))
            valid_time = (math.isfinite(sampled) and math.isfinite(source)
                          and 0 <= source <= now + 1e-9 and 0 <= now - sampled <= cfg.stale_s + 1e-9)
            if not valid_value or not valid_time:
                faults.append(channel)
        if faults:
            was_faulted = self.faulted
            self.faulted = True
            self.near = self.approach = False
            for values in self.digital.values():
                values.update(raw=False, stable=False, since=now)
            if was_faulted:
                return [], ",".join(faults)
            channel = faults[0]
            source = getattr(frame, channel + "_source_s")
            if not math.isfinite(source) or not 0 <= source <= now:
                source = now
            return [self.event("fault", source, now, getattr(frame, channel + "_input_id"))], ",".join(faults)
        if self.faulted:
            self.faulted = False
        events = []
        for channel, values in self.digital.items():
            raw = bool(getattr(frame, channel))
            if raw != values["raw"]:
                values.update(raw=raw, since=now, source=getattr(frame, channel + "_source_s"),
                              id=getattr(frame, channel + "_input_id"))
            debounce = cfg.debounce_s if self.guarded else 0.
            if raw != values["stable"] and now - values["since"] >= debounce - 1e-9:
                values["stable"] = raw
                if raw:
                    events.append(self.event(channel, values["source"], now, values["id"]))
        distance, old_near, old_approach = frame.distance_m, self.near, self.approach
        near_exit = cfg.near_exit_m if self.guarded else cfg.near_enter_m
        approach_exit = cfg.approach_exit_m if self.guarded else cfg.approach_enter_m
        self.near = distance < near_exit if old_near else distance <= cfg.near_enter_m
        self.approach = distance < approach_exit if old_approach else distance <= cfg.approach_enter_m
        if self.near and not old_near:
            events.append(self.event("near", frame.distance_source_s, now, frame.distance_input_id))
        if (old_near and not self.near) or (old_approach and not self.approach):
            events.append(self.event("clear", frame.distance_source_s, now, frame.distance_input_id))
        if self.approach and not old_approach and not self.near:
            events.append(self.event("approach", frame.distance_source_s, now, frame.distance_input_id))
        return events, ""


def config_dict(config):
    return {"provenance": "proposed course model", **asdict(config),
            "states": STATES, "semantic_joint_bounds_rad": BOUNDS, "rgb": RGB,
            "learning": "none; fixed rules and fixed parameters", "latency_limit_s": 1.,
            "timing_scope": "simulated first applied motion/RGB; physical onset not measured",
            "priority": list(PRIORITY), "repeats": "seeded synthetic replications, not physical trials"}
