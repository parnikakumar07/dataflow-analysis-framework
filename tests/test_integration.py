"""
Integration tests
------------------
These tests invoke the actual CLI as a subprocess, just as an evaluator
would from the command line. They cover file mode, interactive mode,
stdin mode, DOT export, and clean error handling.
"""

import os
import subprocess
import sys
import tempfile
import unittest


def run_cli(args, input_text=None):
    return subprocess.run(
        [sys.executable, "-m", "dataflow.cli"] + args,
        input=input_text,
        capture_output=True,
        text=True,
    )


class TestCLIFileMode(unittest.TestCase):
    def test_all_four_analyses_run_on_every_example_with_known_step_counts(self):
        expected_steps = {
            "examples/sequential.tac": {
                "ReachingDefinitions": 1,
                "AvailableExpressions": 1,
                "LiveVariables": 1,
                "ConstantPropagation": 1,
            },
            "examples/branching.tac": {
                "ReachingDefinitions": 4,
                "AvailableExpressions": 4,
                "LiveVariables": 7,
                "ConstantPropagation": 4,
            },
        }

        for example, per_analysis in expected_steps.items():
            result = run_cli([example])
            self.assertEqual(result.returncode, 0, result.stderr)

            for name, steps in per_analysis.items():
                self.assertIn(f"=== {name}", result.stdout)
                section = result.stdout.split(f"=== {name}", 1)[1]
                section = section.split("=== ", 1)[0]

                self.assertIn(
                    f"converged in {steps} worklist steps",
                    section,
                    f"unexpected step count for {name} on {example}",
                )

    def test_looping_example_has_the_documented_per_analysis_step_counts(self):
        result = run_cli(["examples/looping.tac"])
        self.assertEqual(result.returncode, 0, result.stderr)

        self.assertIn(
            "converged in 9 worklist steps", result.stdout
        )  # Reaching Definitions

        self.assertIn(
            "converged in 6 worklist steps", result.stdout
        )  # Available Expressions

        self.assertIn(
            "converged in 11 worklist steps", result.stdout
        )  # Live Variables

        self.assertIn(
            "converged in 13 worklist steps", result.stdout
        )  # Constant Propagation

    def test_single_analysis_flag_runs_only_that_analysis(self):
        result = run_cli(
            ["examples/looping.tac", "--analysis", "live"]
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("=== LiveVariables", result.stdout)
        self.assertNotIn("=== ReachingDefinitions", result.stdout)
        self.assertNotIn("=== AvailableExpressions", result.stdout)
        self.assertNotIn("=== ConstantPropagation", result.stdout)


class TestCLIAlternateInputModes(unittest.TestCase):
    def test_stdin_mode_produces_the_same_result_as_file_mode(self):
        with open("examples/sequential.tac") as handle:
            source = handle.read()

        file_result = run_cli(
            ["examples/sequential.tac", "--analysis", "constprop"]
        )

        stdin_result = run_cli(
            ["--stdin", "--analysis", "constprop"],
            input_text=source,
        )

        self.assertEqual(stdin_result.returncode, 0, stdin_result.stderr)
        self.assertEqual(file_result.stdout, stdin_result.stdout)

    def test_interactive_mode_reads_until_end_sentinel(self):
        typed = "x = 1\ny = 2\nz = x + y\nEND\n"

        result = run_cli(
            ["--analysis", "constprop"],
            input_text=typed,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OUT = {x=1, y=2, z=3}", result.stdout)


class TestCLIDotExport(unittest.TestCase):
    def test_dot_export_matches_the_known_branching_cfg_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            dot_path = os.path.join(tmp, "cfg.dot")

            result = run_cli(
                ["examples/branching.tac", "--dot", dot_path]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(os.path.exists(dot_path))

            with open(dot_path) as handle:
                dot = handle.read()

            self.assertIn("digraph CFG", dot)

            for node in ('"B0"', '"B3"', '"L_true"', '"L_end"'):
                self.assertIn(node, dot)

            self.assertIn('"B0" -> "L_true"', dot)
            self.assertIn('"B0" -> "B3"', dot)


class TestCLIErrorHandling(unittest.TestCase):
    def test_malformed_line_fails_cleanly_without_a_python_traceback(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tac", delete=False
        ) as handle:
            handle.write("x ==== garbage\n")
            path = handle.name

        try:
            result = run_cli([path])
        finally:
            os.unlink(path)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(
            "Traceback (most recent call last)", result.stderr
        )
        self.assertIn("Error:", result.stderr)

    def test_undefined_label_fails_cleanly_without_a_python_traceback(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tac", delete=False
        ) as handle:
            handle.write("goto L_missing\n")
            path = handle.name

        try:
            result = run_cli([path])
        finally:
            os.unlink(path)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(
            "Traceback (most recent call last)", result.stderr
        )
        self.assertIn("Error:", result.stderr)


if __name__ == "__main__":
    unittest.main()