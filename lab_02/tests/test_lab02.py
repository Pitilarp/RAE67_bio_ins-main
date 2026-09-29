import tempfile
import unittest
from pathlib import Path

from lab02 import (
    Controller,
    LabConfig,
    calculate_metrics,
    run_protocol,
    simulate_trial,
    true_distance_m,
)


class TrajectoryTests(unittest.TestCase):
    def test_reference_trajectory_key_times(self):
        self.assertAlmostEqual(true_distance_m(0.0), 0.60)
        self.assertAlmostEqual(true_distance_m(8.0), 0.25)
        self.assertAlmostEqual(true_distance_m(16.0), 0.60)


class ControllerTests(unittest.TestCase):
    def test_hysteresis_preserves_state_inside_band(self):
        controller = Controller("C2", LabConfig(beta=1.0))
        state, _, _ = controller.step(0.0, 0.31, True)
        self.assertEqual(state, "NEAR")
        state, _, _ = controller.step(0.1, 0.35, True)
        self.assertEqual(state, "NEAR")
        state, _, _ = controller.step(0.2, 0.39, True)
        self.assertEqual(state, "FAR")

    def test_proportional_command_is_clamped(self):
        controller = Controller("C3", LabConfig(beta=1.0))
        _, command_near, _ = controller.step(0.0, 0.0, True)
        _, command_far, _ = controller.step(0.1, 1.0, True)
        self.assertEqual(command_near, 0.6)
        self.assertEqual(command_far, -0.6)

    def test_invalid_sample_uses_safe_command(self):
        controller = Controller("C2", LabConfig())
        state, command, filtered = controller.step(0.0, None, False)
        self.assertEqual(state, "FAR")
        self.assertEqual(command, 0.0)
        self.assertIsNone(filtered)


class ExperimentTests(unittest.TestCase):
    def test_sensor_delay_increases_enter_latency(self):
        no_delay = simulate_trial("C1", noise_sigma_m=0.0, delay_ms=0, seed=1)
        delayed = simulate_trial("C1", noise_sigma_m=0.0, delay_ms=300, seed=1)
        no_delay_metrics = calculate_metrics(no_delay)
        delayed_metrics = calculate_metrics(delayed)
        self.assertGreater(
            delayed_metrics["latency_enter_s"], no_delay_metrics["latency_enter_s"]
        )

    def test_controller_comparison_writes_expected_trials(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            trial_metrics, aggregate = run_protocol(
                "controller-comparison", Path(temp_dir) / "run", trials=2
            )
            self.assertEqual(len(trial_metrics), 8)
            self.assertEqual(len(aggregate), 4)


if __name__ == "__main__":
    unittest.main()
