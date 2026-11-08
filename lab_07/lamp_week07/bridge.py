"""Shared offline/rclpy engine; no ROS imports and no completed student policy.

Sensor guards, expressive poses and protocol are attributed to Lab06. Transport
and logging are Week07 extensions. Receipt freshness is distinct from sensor age.
"""
from dataclasses import asdict
import importlib.util
import math
from pathlib import Path
from .course_model import Config, STATES, PRIORITY, RGB, SensorFilter, target_pose, bounded_step

TOPICS = {
    '/lamp/input/button': ('std_msgs/msg/Bool', 'bool'),
    '/lamp/input/touch': ('std_msgs/msg/Bool', 'bool'),
    '/lamp/input/distance': ('std_msgs/msg/Float32', 'm'),
    '/lamp/interaction': ('std_msgs/msg/String', 'event name'),
    '/lamp/emotion': ('std_msgs/msg/String', 'state name'),
    '/lamp/servo_command': ('std_msgs/msg/Float32MultiArray', 'rad [tilt, extend, nod]'),
    '/lamp/rgb_command': ('std_msgs/msg/ColorRGBA', 'normalized [0,1]; alpha=1'),
}

def load_policy(path):
    path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location('week07_student_policy', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, 'transition', None)):
        raise ValueError('Policy requires transition(state, event)')
    return module.transition

def normalized_rgb(values):
    if len(values) != 3 or any(not isinstance(x, int) or not 0 <= x <= 255 for x in values):
        raise ValueError('RGB requires three integer channels 0..255')
    return tuple(x / 255. for x in values) + (1.,)

def servo_message(values):
    if len(values) != 3 or not all(math.isfinite(x) for x in values):
        raise ValueError('Servo requires three finite radian values')
    return list(values)  # Explicit semantic order; no implicit degree conversion.

class Engine:
    def __init__(self, transition, config=Config()):
        self.transition, self.config = transition, config
        self.filter = SensorFilter(config, True)
        self.state, self.entry, self.last_activity = 'normal', 0., 0.
        self.pose, self.color = (0., 0., 0.), RGB['normal']
        self.queue, self.events = [], []
        self.owner = None

    def step(self, frame):
        t, cfg = frame.time_s, self.config
        candidates, faults = self.filter.process(frame)
        if not faults:
            if self.state in ('interested', 'happy') and t - self.entry >= cfg.active_timeout_s - 1e-9:
                candidates.append(self.filter.event('timeout', self.entry + cfg.active_timeout_s, t, 'internal_timeout'))
            if self.state == 'normal' and t - self.last_activity >= cfg.sleep_after_s - 1e-9:
                candidates.append(self.filter.event('idle', self.last_activity + cfg.sleep_after_s, t, 'internal_idle'))
        candidates.sort(key=lambda e: PRIORITY[e.kind])
        event_name = ''
        if candidates:
            winner = candidates[0]
            event_name = winner.kind
            for event in candidates:
                event.old_state, event.decision_time_s = self.state, t
                event.status = 'discarded_priority' if event is not winner else 'policy_held'
            result = self.transition(self.state, winner.kind)
            if result is not None and result not in STATES:
                raise ValueError('Policy returned an unknown state')
            if winner.kind == 'fault': result = 'normal'
            if winner.kind == 'near': result = 'afraid'
            if self.state == 'afraid' and winner.kind not in ('clear', 'fault', 'near'): result = None
            if winner.kind in ('button', 'touch', 'approach', 'near', 'clear'): self.last_activity = t
            if result == self.state:
                winner.status, winner.new_state = 'no_state_change', self.state
            elif result is not None:
                if self.owner and self.owner.status in ('pending', 'responded_partial'):
                    self.owner.status = 'preempted'
                self.queue.clear()
                self.state, self.entry, self.owner = result, t, winner
                winner.status, winner.new_state, winner.queued_time_s = 'pending', result, t
            self.events.extend(candidates)
        if faults:
            self.state = 'normal'
            if self.owner and self.owner.kind != 'fault':
                if self.owner.status in ('pending', 'responded_partial'): self.owner.status = 'preempted_by_fault'
                self.owner = None
            self.queue = [job for job in self.queue if job[3] is None or job[3].kind == 'fault']
        self.queue.append((round(t + cfg.scheduler_delay_s, 8), target_pose(self.state, max(0., t - self.entry)), RGB[self.state], self.owner))
        ready = [job for job in self.queue if job[0] <= t + 1e-9]
        self.queue = [job for job in self.queue if job[0] > t + 1e-9]
        for _, desired, color, owner in ready:
            old_pose, old_color = self.pose, self.color
            self.pose, _ = bounded_step(self.pose, desired, cfg)
            self.color = color
            if owner and owner.status in ('pending', 'responded_partial', 'responded'):
                if owner.applied_time_s is None: owner.applied_time_s = t
                if owner.first_motion_s is None and any(abs(a-b) > 1e-9 for a,b in zip(old_pose, self.pose)): owner.first_motion_s = t
                if owner.first_rgb_s is None and old_color != self.color: owner.first_rgb_s = t
                owner.status = 'responded' if owner.first_motion_s is not None and owner.first_rgb_s is not None else 'responded_partial'
        return {'time_s': t, 'interaction': event_name, 'emotion': self.state,
                'fault_channels': faults, 'tilt_rad': self.pose[0], 'extend_rad': self.pose[1], 'nod_rad': self.pose[2],
                'rgb_r': normalized_rgb(self.color)[0], 'rgb_g': normalized_rgb(self.color)[1], 'rgb_b': normalized_rgb(self.color)[2], 'rgb_a': 1.}

    def event_rows(self):
        rows = []
        for event in self.events:
            row = asdict(event)
            both = max(event.first_motion_s, event.first_rgb_s) if event.first_motion_s is not None and event.first_rgb_s is not None else None
            row['both_latency_s'] = None if both is None else round(both-event.source_time_s, 8)
            rows.append(row)
        return rows
