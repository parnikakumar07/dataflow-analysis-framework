"""
Validates solver results against hand-derived expected values, per the
Review 1 feasibility slide: "Correctness validated against manually
derived expected results" on sequential / branching / looping cases.
"""

import unittest
from dataflow import ir, cfg as cfg_mod, solver, analyses


def load(path):
    with open(path) as f:
        return cfg_mod.build_cfg(ir.parse_program(f.read()))


def block(g, name):
    return next(b for b in g.blocks if b.name == name)


class TestReachingDefinitions(unittest.TestCase):
    def test_merge_point_unions_both_branches(self):
        g = load("examples/branching.tac")
        IN, OUT, _ = solver.solve(g, analyses.ReachingDefinitions(g))
        l_end = block(g, "L_end")
        vars_reaching = {d[2] for d in IN[l_end]}
        # both branches define z; both definitions must reach the merge block
        z_defs = [d for d in IN[l_end] if d[2] == "z"]
        self.assertEqual(len(z_defs), 2)
        self.assertIn("x", vars_reaching)
        self.assertIn("y", vars_reaching)

    def test_sequential_has_exactly_one_def_per_var_at_exit(self):
        g = load("examples/sequential.tac")
        IN, OUT, _ = solver.solve(g, analyses.ReachingDefinitions(g))
        exit_block = g.blocks[-1]
        vars_out = [d[2] for d in OUT[exit_block]]
        self.assertEqual(sorted(vars_out), ["w", "x", "y", "z"])


class TestAvailableExpressions(unittest.TestCase):
    def test_expression_not_available_unless_computed_on_all_paths(self):
        g = load("examples/branching.tac")
        IN, OUT, _ = solver.solve(g, analyses.AvailableExpressions(g))
        l_end = block(g, "L_end")
        # x+y is only computed on the L_true path, not the B3 path -> not
        # available at the merge point (must-analysis, intersection meet)
        self.assertNotIn(("x", "+", "y"), IN[l_end])

    def test_available_within_the_computing_block(self):
        g = load("examples/branching.tac")
        IN, OUT, _ = solver.solve(g, analyses.AvailableExpressions(g))
        l_true = block(g, "L_true")
        self.assertIn(("x", "+", "y"), OUT[l_true])


class TestLiveVariables(unittest.TestCase):
    def test_dead_store_has_empty_liveness_after_return(self):
        g = load("examples/sequential.tac")
        IN, OUT, _ = solver.solve(g, analyses.LiveVariables(g))
        only_block = g.blocks[0]
        self.assertEqual(OUT[only_block], frozenset())  # nothing live after `return w`

    def test_loop_variables_stay_live_across_the_back_edge(self):
        g = load("examples/looping.tac")
        IN, OUT, _ = solver.solve(g, analyses.LiveVariables(g))
        l_head = block(g, "L_head")
        self.assertIn("i", IN[l_head])
        self.assertIn("s", IN[l_head])


class TestConstantPropagation(unittest.TestCase):
    def test_straight_line_constants_are_folded(self):
        g = load("examples/sequential.tac")
        IN, OUT, _ = solver.solve(g, analyses.ConstantPropagation(g))
        only_block = g.blocks[0]
        self.assertEqual(OUT[only_block]["x"], 1)
        self.assertEqual(OUT[only_block]["y"], 2)
        self.assertEqual(OUT[only_block]["z"], 3)
        self.assertEqual(OUT[only_block]["w"], 3)

    def test_conflicting_values_at_merge_become_nac(self):
        g = load("examples/branching.tac")
        IN, OUT, _ = solver.solve(g, analyses.ConstantPropagation(g))
        l_end = block(g, "L_end")
        # z = 99 on one path, z = 3 on the other -> not a single constant
        self.assertEqual(IN[l_end]["z"], analyses.NAC)

    def test_loop_variable_is_not_a_constant(self):
        g = load("examples/looping.tac")
        IN, OUT, _ = solver.solve(g, analyses.ConstantPropagation(g))
        l_head = block(g, "L_head")
        self.assertEqual(IN[l_head]["i"], analyses.NAC)


class TestSolverConverges(unittest.TestCase):
    def test_all_analyses_terminate_on_all_examples(self):
        for path in ("examples/sequential.tac", "examples/branching.tac", "examples/looping.tac"):
            g = load(path)
            for cls in (analyses.ReachingDefinitions, analyses.AvailableExpressions,
                        analyses.LiveVariables, analyses.ConstantPropagation):
                IN, OUT, steps = solver.solve(g, cls(g))
                self.assertGreater(steps, 0)


if __name__ == "__main__":
    unittest.main()
