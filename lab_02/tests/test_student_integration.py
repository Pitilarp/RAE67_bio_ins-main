import inspect
import tempfile
import unittest
from pathlib import Path

from grade_submission import evaluate_submission
from lab02 import (
    LabConfig,
    StudentControllerAdapter,
    load_student_factory,
    run_protocol,
    simulate_trial,
)
from student_controller import Parameters, StudentController


class CompletedStudentController(StudentController):
    def update_filter(self, raw_distance_m):
        if self.filtered_distance is None:
            self.filtered_distance = raw_distance_m
        else:
            self.filtered_distance = (
                self.p.beta * raw_distance_m + (1 - self.p.beta) * self.filtered_distance
            )
        return self.filtered_distance

    def update_state_single_threshold(self, distance_m):
        return "NEAR" if distance_m < self.p.threshold_m else "FAR"

    def update_state_hysteresis(self, distance_m):
        if self.state == "FAR" and distance_m < self.p.enter_threshold_m:
            return "NEAR"
        if self.state == "NEAR" and distance_m > self.p.exit_threshold_m:
            return "FAR"
        return self.state

    def proportional_command(self, distance_m):
        command = self.p.kp * (self.p.target_distance_m - distance_m)
        return max(self.p.command_min, min(self.p.command_max, command))


def working_factory(condition, config):
    return StudentControllerAdapter(condition, config, CompletedStudentController, Parameters)


class StudentIntegrationTests(unittest.TestCase):
    def test_adapter_runs_all_conditions(self):
        for condition in ("C0", "C1", "C2", "C3"):
            with self.subTest(condition=condition):
                rows = simulate_trial(condition, 0.01, 0, 7, controller_factory=working_factory)
                reference = simulate_trial(condition, 0.01, 0, 7)
                self.assertEqual(len(rows), 1001)
                self.assertEqual(rows[0]["condition"], condition)
                self.assertEqual(
                    [(row["state"], row["command"]) for row in rows],
                    [(row["state"], row["command"]) for row in reference],
                )

    def test_invalid_sample_uses_student_safe_command(self):
        adapter = working_factory("C2", LabConfig())
        self.assertEqual(adapter.step(0.0, None, False), ("FAR", 0.0, None))

    def test_unfinished_starter_fails_before_writing_results(self):
        student_file = Path(__file__).resolve().parents[1] / "student_controller.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "student_results"
            with self.assertRaisesRegex(NotImplementedError, "unfinished TODO"):
                run_protocol(
                    "controller-comparison", output, trials=1,
                    controller_source="student", student_file=student_file,
                )
            self.assertFalse(output.exists())

    def test_diagnostic_report_identifies_unfinished_starter(self):
        student_file = Path(__file__).resolve().parents[1] / "student_controller.py"
        report = evaluate_submission(student_file)
        self.assertGreater(report["failed"], 0)
        self.assertEqual(report["checks"][0]["status"], "PASS")

    def test_loader_accepts_student_file(self):
        student_file = Path(__file__).resolve().parents[1] / "student_controller.py"
        factory = load_student_factory(student_file)
        adapter = factory("C0", LabConfig())
        self.assertEqual(adapter.step(5.0, None, False)[0], "NEAR")

    def test_complete_submission_runs_protocol_and_grader(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            student_file = Path(temp_dir) / "completed_submission.py"
            student_file.write_text(
                "from student_controller import Parameters, StudentController\n\n"
                + inspect.getsource(CompletedStudentController)
                + "\nStudentController = CompletedStudentController\n",
                encoding="utf-8",
            )
            report = evaluate_submission(student_file)
            self.assertEqual(report["failed"], 0, report["checks"])
            output = Path(temp_dir) / "results"
            trials, aggregate = run_protocol(
                "controller-comparison", output, trials=1,
                controller_source="student", student_file=student_file,
            )
            self.assertEqual(len(trials), 4)
            self.assertEqual(len(aggregate), 4)
            self.assertTrue((output / "run_config.json").is_file())


if __name__ == "__main__":
    unittest.main()
