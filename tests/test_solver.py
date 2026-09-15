import unittest
from dataflow import ir, cfg as cfg_mod, solver, analyses


class TestSolverMechanics(unittest.TestCase):
    def test_empty_program_produces_no_blocks(self):
        g = cfg_mod.build_cfg([])
        IN, OUT, steps = solver.solve(g, analyses.ReachingDefinitions(g))
        self.assertEqual(IN, {})
        self.assertEqual(OUT, {})

    def test_forward_boundary_condition_applies_only_to_entry(self):
        g = cfg_mod.build_cfg(ir.parse_program("x = 1\ny = 2\n"))
        rd = analyses.ReachingDefinitions(g)
        IN, OUT, _ = solver.solve(g, rd)
        self.assertEqual(IN[g.entry], frozenset())

    def test_backward_boundary_condition_applies_to_exit_blocks(self):
        g = cfg_mod.build_cfg(ir.parse_program("x = 1\nreturn x\n"))
        lv = analyses.LiveVariables(g)
        IN, OUT, _ = solver.solve(g, lv)
        for exit_block in g.exits:
            self.assertEqual(OUT[exit_block], frozenset())


if __name__ == "__main__":
    unittest.main()
