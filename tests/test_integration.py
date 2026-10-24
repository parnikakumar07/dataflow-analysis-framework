"""
Integration tests
------------------
Unlike test_ir.py / test_cfg.py / test_solver.py / test_analyses.py, which
call the parser, CFG builder, solver, and analyses directly as Python
functions, these tests go through the real entry point: they invoke
`python3 -m dataflow.cli` as a subprocess, exactly as an evaluator would at
the command line. That is the actual integration boundary for this project
(file mode / interactive mode / --stdin mode all funnel into run_source(),
per cli.py) -- these tests exercise it from the outside, not from inside
the same process.
"""

import subprocess
import sys
import tempfile
import os
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
        # Ground truth re-confirmed from the real solver, not assumed --
        # these are the exact step counts documented in the Review 2 report.
        expected_steps = {
            "examples/sequential.tac": "1",
            "examples/branching.tac": "4",
        }
        for example, steps in expected_steps.items():
            result = run_cli([example])
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ("ReachingDefinitions", "AvailableExpressions",
                         "LiveVariables", "ConstantPropagation"):
                self.assertIn(f"=== {name}", result.stdout)
            self.assertEqual(
                result.stdout.count(f"converged in {steps} worklist steps"), 4,
                f"expected all 4 analyses on {example} to converge in {steps} steps",
            )

    def test_looping_example_has_the_documented_per_analysis_step_counts(self):
        result = run_cli(["examples/looping.tac"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("converged in 9 worklist steps", result.stdout)  # Reaching Defs
        self.assertIn("converged in 6 worklist steps", result.stdout)  # Available Exprs
        self.assertIn("converged in 13 worklist steps", result.stdout)  # Constant Prop

    def test_single_analysis_flag_runs_only_that_analysis(self):
        result = run_cli(["examples/looping.tac", "--analysis", "live"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("=== LiveVariables", result.stdout)
        self.assertNotIn("=== ReachingDefinitions", result.stdout)
        self.assertNotIn("=== AvailableExpressions", result.stdout)
        self.assertNotIn("=== ConstantPropagation", result.stdout)


class TestCLIAlternateInputModes(unittest.TestCase):
    def test_stdin_mode_produces_the_same_result_as_file_mode(self):
        with open("examples/sequential.tac") as f:
            source = f.read()
        file_result = run_cli(["examples/sequential.tac", "--analysis", "constprop"])
        stdin_result = run_cli(["--stdin", "--analysis", "constprop"], input_text=source)
        self.assertEqual(stdin_result.returncode, 0, stdin_result.stderr)
        self.assertEqual(file_result.stdout, stdin_result.stdout)

    def test_interactive_mode_reads_until_end_sentinel(self):
        typed = "x = 1\ny = 2\nz = x + y\nEND\n"
        result = run_cli(["--analysis", "constprop"], input_text=typed)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OUT = {x=1, y=2, z=3}", result.stdout)


class TestCLIDotExport(unittest.TestCase):
    def test_dot_export_matches_the_known_branching_cfg_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            dot_path = os.path.join(tmp, "cfg.dot")
            result = run_cli(["examples/branching.tac", "--dot", dot_path])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(os.path.exists(dot_path))
            with open(dot_path) as f:
                dot = f.read()
            self.assertIn("digraph CFG", dot)
            for node in ('"B0"', '"B3"', '"L_true"', '"L_end"'):
                self.assertIn(node, dot)
            self.assertIn('"B0" -> "L_true"', dot)
            self.assertIn('"B0" -> "B3"', dot)


class TestCLIErrorHandling(unittest.TestCase):
    """
    The unit-level tests (test_ir.py, test_cfg.py) already confirm that
    ParseError/ValueError are raised correctly on bad input. These
    integration tests confirm something different: that the real CLI
    catches those errors and fails cleanly, instead of leaking an internal
    Python traceback to whoever is running the demo.
    """

    def test_malformed_line_fails_cleanly_without_a_python_traceback(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tac", delete=False) as f:
            f.write("x ==== garbage\n")
            path = f.name
        try:
            result = run_cli([path])
        finally:
            os.unlink(path)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback (most recent call last)", result.stderr)
        self.assertIn("Error:", result.stderr)

    def test_undefined_label_fails_cleanly_without_a_python_traceback(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tac", delete=False) as f:
            f.write("goto L_missing\n")
            path = f.name
        try:
            result = run_cli([path])
        finally:
            os.unlink(path)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback (most recent call last)", result.stderr)
        self.assertIn("Error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
