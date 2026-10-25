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


def solve_src(src, analysis_cls):
    """Build a CFG from inline TAC text and run one analysis over it."""
    g = cfg_mod.build_cfg(ir.parse_program(src))
    IN, OUT, _ = solver.solve(g, analysis_cls(g))
    return g, IN, OUT


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

    def test_same_block_redefinition_kills_earlier_definition(self):
        # Single block B0: GEN keeps only the LAST definition of each
        # variable, so (B0,0,x) is killed by (B0,1,x).
        # OUT[B0] = GEN[B0] u (IN[B0] - KILL[B0]), IN[B0] = {} (boundary).
        g, IN, OUT = solve_src("x = 1\nx = 2\ny = x\nreturn y\n",
                               analyses.ReachingDefinitions)
        self.assertEqual([b.name for b in g.blocks], ["B0"])
        b0 = block(g, "B0")
        self.assertEqual(IN[b0], frozenset())
        self.assertEqual(OUT[b0], frozenset({("B0", 1, "x"), ("B0", 2, "y")}))
        self.assertNotIn(("B0", 0, "x"), OUT[b0])

    def test_definitions_from_different_predecessors_reach_merge(self):
        # B0 -> B2 -> E and B0 -> L -> E. Each branch defines x once and
        # neither kills the other (different paths): IN[E] = OUT[B2] u OUT[L].
        src = ("c = 1\nif c < 2 goto L\nx = 1\ngoto E\n"
               "L:\nx = 2\nE:\nreturn x\n")
        g, IN, OUT = solve_src(src, analyses.ReachingDefinitions)
        self.assertEqual([b.name for b in g.blocks], ["B0", "B2", "L", "E"])
        dc, dx1, dx2 = ("B0", 0, "c"), ("B2", 0, "x"), ("L", 1, "x")
        self.assertEqual(OUT[block(g, "B0")], frozenset({dc}))
        self.assertEqual(OUT[block(g, "B2")], frozenset({dc, dx1}))
        self.assertEqual(OUT[block(g, "L")], frozenset({dc, dx2}))
        self.assertEqual(IN[block(g, "E")], frozenset({dc, dx1, dx2}))
        self.assertEqual(OUT[block(g, "E")], frozenset({dc, dx1, dx2}))

    def test_definition_on_one_path_kills_only_on_that_path(self):
        # x=1 reaches the merge L via the taken branch (skipping x=5) AND is
        # killed on the fall-through path by x=5, so both definitions reach L.
        src = "x = 1\nif x < 2 goto L\nx = 5\nL:\ny = x\nreturn y\n"
        g, IN, OUT = solve_src(src, analyses.ReachingDefinitions)
        self.assertEqual([b.name for b in g.blocks], ["B0", "B2", "L"])
        d1, d5, dy = ("B0", 0, "x"), ("B2", 0, "x"), ("L", 1, "y")
        self.assertEqual(OUT[block(g, "B0")], frozenset({d1}))
        self.assertEqual(OUT[block(g, "B2")], frozenset({d5}))  # d1 killed here
        self.assertEqual(IN[block(g, "L")], frozenset({d1, d5}))
        self.assertEqual(OUT[block(g, "L")], frozenset({d1, d5, dy}))

    def test_loop_back_edge_definitions_reach_loop_header(self):
        # examples/looping.tac. L_body redefines s and i, killing the B0
        # definitions on that path; its definitions reach L_head only via the
        # back edge, so the solver must reprocess L_head to see them.
        g = load("examples/looping.tac")
        IN, OUT, _ = solver.solve(g, analyses.ReachingDefinitions(g))
        self.assertEqual([b.name for b in g.blocks],
                         ["B0", "L_head", "B4", "L_body", "L_end"])
        i0, s0 = ("B0", 0, "i"), ("B0", 1, "s")
        s1, i1 = ("L_body", 1, "s"), ("L_body", 2, "i")
        every = frozenset({i0, s0, s1, i1})
        self.assertEqual(IN[block(g, "B0")], frozenset())
        self.assertEqual(OUT[block(g, "B0")], frozenset({i0, s0}))
        self.assertEqual(IN[block(g, "L_head")], every)
        self.assertEqual(OUT[block(g, "L_head")], every)
        self.assertEqual(IN[block(g, "L_body")], every)
        self.assertEqual(OUT[block(g, "L_body")], frozenset({s1, i1}))  # i0, s0 killed
        self.assertEqual(IN[block(g, "L_end")], every)


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

    def test_redefining_left_operand_in_later_block_invalidates_expression(self):
        # OUT[B0] = {a+b}; IN[L] = OUT[B0]; KILL[L] contains a+b, GEN[L] = {}
        # OUT[L] = GEN[L] u (IN[L] - KILL[L]) = {}
        src = "a = 1\nb = 2\nt = a + b\ngoto L\nL:\na = 9\nreturn t\n"
        g, IN, OUT = solve_src(src, analyses.AvailableExpressions)
        self.assertEqual([b.name for b in g.blocks], ["B0", "L"])
        ab = frozenset({("a", "+", "b")})
        self.assertEqual(OUT[block(g, "B0")], ab)
        self.assertEqual(IN[block(g, "L")], ab)
        self.assertEqual(OUT[block(g, "L")], frozenset())

    def test_redefining_right_operand_in_later_block_invalidates_expression(self):
        src = "a = 1\nb = 2\nt = a + b\ngoto L\nL:\nb = 9\nreturn t\n"
        g, IN, OUT = solve_src(src, analyses.AvailableExpressions)
        self.assertEqual([b.name for b in g.blocks], ["B0", "L"])
        ab = frozenset({("a", "+", "b")})
        self.assertEqual(OUT[block(g, "B0")], ab)
        self.assertEqual(IN[block(g, "L")], ab)
        self.assertEqual(OUT[block(g, "L")], frozenset())

    def test_loop_invariant_expression_stays_available_around_loop(self):
        # a+b is computed once before the loop; the body neither recomputes
        # nor kills it (t = t + 1 only kills expressions using t). With the
        # back edge, IN[L] = OUT[B0] n OUT[L_body], so a+b survives only if
        # non-entry blocks start at the universe and meet down to {a+b}.
        src = ("a = 1\nb = 2\nt = a + b\nL:\nif t < 9 goto L_body\n"
               "return t\nL_body:\nt = t + 1\ngoto L\n")
        g, IN, OUT = solve_src(src, analyses.AvailableExpressions)
        self.assertEqual([b.name for b in g.blocks], ["B0", "L", "B5", "L_body"])
        ab = frozenset({("a", "+", "b")})
        self.assertEqual(IN[block(g, "B0")], frozenset())
        self.assertEqual(OUT[block(g, "B0")], ab)
        for name in ("L", "B5", "L_body"):
            self.assertEqual(IN[block(g, name)], ab, f"IN[{name}]")
            self.assertEqual(OUT[block(g, name)], ab, f"OUT[{name}]")

    def test_operand_redefined_inside_loop_removes_expression_at_header(self):
        # L recomputes a+b but then does a = a + 1, which kills it before the
        # back edge: GEN[L] = {}, so IN[L] = OUT[B0] n OUT[L] = {a+b} n {} = {}.
        src = ("a = 1\nb = 2\nt = a + b\nL:\nu = a + b\na = a + 1\n"
               "if u < 9 goto L\nreturn u\n")
        g, IN, OUT = solve_src(src, analyses.AvailableExpressions)
        self.assertEqual([b.name for b in g.blocks], ["B0", "L", "B7"])
        self.assertEqual(OUT[block(g, "B0")], frozenset({("a", "+", "b")}))
        for name in ("L", "B7"):
            self.assertEqual(IN[block(g, name)], frozenset(), f"IN[{name}]")
            self.assertEqual(OUT[block(g, name)], frozenset(), f"OUT[{name}]")

    def test_repeated_operand_expression_is_killed_and_can_be_regenerated(self):
        # a+a has both operands equal to `a`; a redefinition of `a` kills it.
        # (i) killed, not recomputed -> {}; (ii) killed then recomputed -> {a+a};
        # (iii) generated in one block, killed in the next -> IN {a+a}, OUT {}.
        aa = frozenset({("a", "+", "a")})
        g, IN, OUT = solve_src("a = 3\nt = a + a\na = 4\nreturn t\n",
                               analyses.AvailableExpressions)
        self.assertEqual(OUT[g.blocks[0]], frozenset())
        g, IN, OUT = solve_src("a = 3\nt = a + a\na = 4\nu = a + a\nreturn u\n",
                               analyses.AvailableExpressions)
        self.assertEqual(OUT[g.blocks[0]], aa)
        g, IN, OUT = solve_src("a = 3\nt = a + a\ngoto L\nL:\na = 4\nreturn t\n",
                               analyses.AvailableExpressions)
        self.assertEqual([b.name for b in g.blocks], ["B0", "L"])
        self.assertEqual(IN[block(g, "L")], aa)
        self.assertEqual(OUT[block(g, "L")], frozenset())

    def test_every_binary_operator_is_invalidated_by_operand_redefinition(self):
        # -, /, % are tracked like +: all three are available after being
        # computed, and redefining `b` kills all of them.
        computed = "a = 1\nb = 2\nt = a % b\nu = a / b\nv = a - b\n"
        keys = frozenset({("a", "%", "b"), ("a", "/", "b"), ("a", "-", "b")})
        g, IN, OUT = solve_src(computed + "return t\n", analyses.AvailableExpressions)
        self.assertEqual(OUT[g.blocks[0]], keys)
        g, IN, OUT = solve_src(computed + "goto L\nL:\nb = 5\nreturn t\n",
                               analyses.AvailableExpressions)
        self.assertEqual(OUT[block(g, "B0")], keys)
        self.assertEqual(IN[block(g, "L")], keys)
        self.assertEqual(OUT[block(g, "L")], frozenset())


class TestAvailableExpressionsCommutativity(unittest.TestCase):
    def test_commutative_expression_recognized_across_both_orderings(self):
        # a+b and b+a compute the same value -- one branch writes it as
        # "a + b", the other as "b + a". A must-analysis that doesn't
        # normalize commutative operands would treat these as two
        # different expressions and (wrongly) conclude neither is
        # available at the merge point.
        src = "if x < y goto L1\nz = a + b\ngoto L2\nL1:\nz = b + a\nL2:\nw = z\nreturn w\n"
        g = cfg_mod.build_cfg(ir.parse_program(src))
        IN, OUT, _ = solver.solve(g, analyses.AvailableExpressions(g))
        l2 = block(g, "L2")
        matches = [e for e in IN[l2] if e[1] == "+" and set((e[0], e[2])) == {"a", "b"}]
        self.assertEqual(len(matches), 1, f"expected exactly one canonical a+b key, got {IN[l2]}")

    def test_non_commutative_expression_stays_distinct_across_orderings(self):
        # a-b and b-a are NOT the same value -- this must keep behaving
        # like a normal must-analysis: since each branch only computes one
        # ordering, neither should be "available" at the merge.
        src = "if x < y goto L1\nz = a - b\ngoto L2\nL1:\nz = b - a\nL2:\nw = z\nreturn w\n"
        g = cfg_mod.build_cfg(ir.parse_program(src))
        IN, OUT, _ = solver.solve(g, analyses.AvailableExpressions(g))
        l2 = block(g, "L2")
        self.assertNotIn(("a", "-", "b"), IN[l2])
        self.assertNotIn(("b", "-", "a"), IN[l2])

    def test_canonical_commutative_expression_is_killed_by_either_operand(self):
        # b+a is stored under the canonical key (a,+,b); that key must still be
        # invalidated when either operand is redefined in a later block.
        for var in ("a", "b"):
            src = f"a = 1\nb = 2\nt = b + a\ngoto L\nL:\n{var} = 9\nreturn t\n"
            g, IN, OUT = solve_src(src, analyses.AvailableExpressions)
            canonical = frozenset({("a", "+", "b")})
            self.assertEqual(IN[block(g, "L")], canonical, var)
            self.assertEqual(OUT[block(g, "L")], frozenset(), var)


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

    def test_use_before_redefinition_in_same_block_is_live_on_entry(self):
        # USE = {x} (read by y = x + 1 before x = 2 redefines it); DEF = {y, x}.
        # IN = USE u (OUT - DEF) = {x}. The later x = 2 must not hide the use.
        g, IN, OUT = solve_src("y = x + 1\nx = 2\nreturn y\n",
                               analyses.LiveVariables)
        b0 = g.blocks[0]
        self.assertEqual(OUT[b0], frozenset())
        self.assertEqual(IN[b0], frozenset({"x"}))

    def test_constants_and_labels_are_not_live_variables(self):
        g = cfg_mod.build_cfg(ir.parse_program(
            "t = 5\nif t < 10 goto L\nL:\nreturn 7\n"))
        lv = analyses.LiveVariables(g)
        self.assertEqual([b.name for b in g.blocks], ["B0", "L"])
        for b in g.blocks:
            self.assertEqual(lv.use[b], frozenset(), b.name)  # no '10', '7', 'L'
        self.assertEqual(lv.defs[block(g, "B0")], frozenset({"t"}))

    def _assert_satisfies_live_variable_equations(self, g, expected):
        # Checks a hand-derived solution against the equations directly,
        # without the solver:  IN[B] = USE[B] u (OUT[B] - DEF[B])  (transfer)
        # and  OUT[B] = u IN[S] over successors S (empty at exits)  (meet).
        lv = analyses.LiveVariables(g)
        self.assertEqual({b.name for b in g.blocks}, set(expected))
        for b in g.blocks:
            exp_in, exp_out = (frozenset(v) for v in expected[b.name])
            succ_in = [frozenset(expected[s.name][0]) for s in g.succs[b]]
            want_out = lv.meet(succ_in) if succ_in else lv.boundary_value()
            self.assertEqual(want_out, exp_out, f"OUT[{b.name}] equation")
            self.assertEqual(lv.transfer(b, exp_out), exp_in, f"IN[{b.name}] equation")

    def test_hand_derived_solution_satisfies_equations_on_branching(self):
        # USE/DEF: B0 {}/{x,y}; B3 {}/{z}; L_true {x,y}/{z}; L_end {z}/{w}.
        self._assert_satisfies_live_variable_equations(load("examples/branching.tac"), {
            "B0": ("", "xy"), "B3": ("", "z"),
            "L_true": ("xy", "z"), "L_end": ("z", ""),
        })

    def test_hand_derived_solution_satisfies_equations_on_looping(self):
        # USE/DEF: B0 {}/{i,s}; L_head {i}/{}; B4 {}/{}; L_body {s,i}/{s,i};
        # L_end {s}/{}. L_head <-> L_body form the cycle the fixed point closes.
        self._assert_satisfies_live_variable_equations(load("examples/looping.tac"), {
            "B0": ("", "is"), "L_head": ("is", "is"), "B4": ("s", "s"),
            "L_body": ("is", "is"), "L_end": ("s", ""),
        })


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

    def test_reassignment_overwrites_earlier_constant(self):
        # a=5; b=a -> b=5; a=6 does not change b; c = a + b = 11.
        g, IN, OUT = solve_src("a = 5\nb = a\na = 6\nc = a + b\nreturn c\n",
                               analyses.ConstantPropagation)
        self.assertEqual(OUT[g.blocks[0]], {"a": 6, "b": 5, "c": 11})

    def test_equal_constants_survive_merge(self):
        # Both branches assign x = 4, so meet(4, 4) = 4 and y = x + 1 = 5.
        src = ("c = 1\nif c < 2 goto L\nx = 4\ngoto E\nL:\nx = 4\nE:\n"
               "y = x + 1\nreturn y\n")
        g, IN, OUT = solve_src(src, analyses.ConstantPropagation)
        self.assertEqual([b.name for b in g.blocks], ["B0", "B2", "L", "E"])
        self.assertEqual(IN[block(g, "E")], {"c": 1, "x": 4})
        self.assertEqual(OUT[block(g, "E")], {"c": 1, "x": 4, "y": 5})

    def test_loop_counter_becomes_nac_but_invariant_constant_stays_constant(self):
        # i: meet(0, i+1) -> NAC after the back edge is reprocessed; k = 7 is
        # never reassigned in the loop and must stay constant everywhere.
        src = ("k = 7\ni = 0\nL:\nif i < 3 goto L_body\nreturn k\n"
               "L_body:\ni = i + 1\ngoto L\n")
        g, IN, OUT = solve_src(src, analyses.ConstantPropagation)
        self.assertEqual([b.name for b in g.blocks], ["B0", "L", "B4", "L_body"])
        self.assertEqual(OUT[block(g, "B0")], {"k": 7, "i": 0})
        for name in ("L", "B4", "L_body"):
            self.assertEqual(IN[block(g, name)], {"k": 7, "i": analyses.NAC}, name)

    def test_division_and_modulo_by_zero_are_not_constants(self):
        g, IN, OUT = solve_src(
            "a = 5\nz = 0\nq = a / z\nm = a % z\nreturn q\n",
            analyses.ConstantPropagation)
        env = OUT[g.blocks[0]]
        self.assertEqual((env["q"], env["m"]), (analyses.NAC, analyses.NAC))

    def test_unary_minus_on_constant_variable_folds(self):
        # Depends on the parser desugaring x = -y to x = 0 - y.
        g, IN, OUT = solve_src("y = 5\nx = -y\nreturn x\n",
                               analyses.ConstantPropagation)
        self.assertEqual(OUT[g.blocks[0]], {"y": 5, "x": -5})


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
