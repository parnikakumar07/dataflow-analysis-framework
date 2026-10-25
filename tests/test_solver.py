
import unittest
from dataflow import ir, cfg as cfg_mod, solver, analyses


class TestSolverMechanics(unittest.TestCase):
    def test_empty_program_produces_no_blocks(self):
        g = cfg_mod.build_cfg([])
        IN, OUT, steps = solver.solve(
            g, analyses.ReachingDefinitions(g)
        )
        self.assertEqual(IN, {})
        self.assertEqual(OUT, {})

    def test_forward_boundary_condition_applies_only_to_entry(self):
        g = cfg_mod.build_cfg(
            ir.parse_program("x = 1\ny = 2\n")
        )
        rd = analyses.ReachingDefinitions(g)
        IN, OUT, _ = solver.solve(g, rd)
        self.assertEqual(IN[g.entry], frozenset())

    def test_backward_boundary_condition_applies_to_exit_blocks(self):
        g = cfg_mod.build_cfg(
            ir.parse_program("x = 1\nreturn x\n")
        )
        lv = analyses.LiveVariables(g)
        IN, OUT, _ = solver.solve(g, lv)
        for exit_block in g.exits:
            self.assertEqual(OUT[exit_block], frozenset())

    def test_backward_boundary_condition_applies_independently_to_every_exit(self):
        # Every return block must receive its own backward boundary value.
        g = cfg_mod.build_cfg(
            ir.parse_program(
                "if x < y goto L1\n"
                "return x\n"
                "L1:\n"
                "return y\n"
            )
        )
        self.assertEqual(len(g.exits), 2)
        lv = analyses.LiveVariables(g)
        IN, OUT, _ = solver.solve(g, lv)
        for exit_block in g.exits:
            self.assertEqual(OUT[exit_block], frozenset())

    def test_unreachable_block_is_still_solved_and_feeds_its_successor(self):
        # The solver processes the CFG as given, including unreachable blocks.
        g = cfg_mod.build_cfg(
            ir.parse_program(
                "goto L1\n"
                "x = 1\n"
                "L1:\n"
                "y = 2\n"
                "return y\n"
            )
        )
        unreachable = next(
            b for b in g.blocks if b.name == "B1"
        )
        l1 = next(b for b in g.blocks if b.name == "L1")
        self.assertEqual(g.preds[unreachable], [])

        rd = analyses.ReachingDefinitions(g)
        IN, OUT, _ = solver.solve(g, rd)
        self.assertIn((unreachable.name, 0, "x"), OUT[unreachable])
        self.assertIn((unreachable.name, 0, "x"), IN[l1])

    def test_iteration_limit_raises_runtime_error(self):
        # A zero iteration limit must reject a non-empty worklist.
        g = cfg_mod.build_cfg(
            ir.parse_program("x = 1\n")
        )
        rd = analyses.ReachingDefinitions(g)

        with self.assertRaisesRegex(RuntimeError, "max_iterations"):
            solver.solve(g, rd, max_iterations=0)


if __name__ == "__main__":
    unittest.main()
