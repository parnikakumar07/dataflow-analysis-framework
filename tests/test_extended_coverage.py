
"""Parameterized regression coverage for parser, CFG, analyses, and solver.

Each parameter represents a distinct input/operator/graph behavior, keeping
coverage broad without duplicating one test function per nearly identical case.
"""

import pytest

from dataflow import analyses, cfg as cfg_mod, ir, solver


def build_cfg(source):
    return cfg_mod.build_cfg(ir.parse_program(source))


def solve_source(source, analysis_cls):
    graph = build_cfg(source)
    in_map, out_map, steps = solver.solve(graph, analysis_cls(graph))
    return graph, in_map, out_map, steps


# Parser: legal forms across operand names, integer forms, and operators.
@pytest.mark.parametrize(
    "source, expected_op, expected_src1, expected_src2",
    [
        ("v = 0", "const", "0", None),
        ("v = 1", "const", "1", None),
        ("v = -1", "const", "-1", None),
        ("v = 2147483647", "const", "2147483647", None),
        ("_v = value", "copy", "value", None),
        ("value2 = _v", "copy", "_v", None),
        ("v = left + right", "+", "left", "right"),
        ("v = left - right", "-", "left", "right"),
        ("v = left * right", "*", "left", "right"),
        ("v = left / right", "/", "left", "right"),
        ("v = left % right", "%", "left", "right"),
        ("v = left + 7", "+", "left", "7"),
        ("v = 7 + right", "+", "7", "right"),
        ("v = left - 7", "-", "left", "7"),
        ("v = 7 - right", "-", "7", "right"),
        ("v = left * 2", "*", "left", "2"),
        ("v = 8 / right", "/", "8", "right"),
        ("v = left % 3", "%", "left", "3"),
        ("v = -left", "-", "0", "left"),
        ("v = -_temporary", "-", "0", "_temporary"),
    ],
)
def test_parser_accepts_assignment_forms(
    source, expected_op, expected_src1, expected_src2
):
    instruction = ir.parse_line(source, 1)
    assert instruction.kind == "assign"
    assert instruction.op == expected_op
    assert instruction.src1 == expected_src1
    assert instruction.src2 == expected_src2


@pytest.mark.parametrize(
    "source",
    [
        "x", "x =", "= 1", "1x = 2", "x-y = 2", "x = a + b + c",
        "x = a * b / c", "x = (a)", "x = a +", "x = + a", "x = a ** b",
        "x = a // b", "x = a & b", "if x < y goto", "if x <> y goto L1",
        "if x < y L1", "if 1.5 < x goto L1", "goto", "goto L-1",
        "return x y", "L 1:", "1L:", "x = @", "x = --y",
    ],
)
def test_parser_rejects_malformed_or_unsupported_lines(source):
    with pytest.raises(ir.ParseError):
        ir.parse_line(source, 1)


@pytest.mark.parametrize(
    "source, expected_uses, expected_defs",
    [
        ("x = 1", set(), {"x"}),
        ("x = -1", set(), {"x"}),
        ("x = y", {"y"}, {"x"}),
        ("x = _y", {"_y"}, {"x"}),
        ("x = y + z", {"y", "z"}, {"x"}),
        ("x = y - z", {"y", "z"}, {"x"}),
        ("x = y * z", {"y", "z"}, {"x"}),
        ("x = y / z", {"y", "z"}, {"x"}),
        ("x = y % z", {"y", "z"}, {"x"}),
        ("x = y + 1", {"y"}, {"x"}),
        ("x = 1 + y", {"y"}, {"x"}),
        ("x = -y", {"y"}, {"x"}),
        ("if x == y goto L", {"x", "y"}, set()),
        ("if x != 3 goto L", {"x"}, set()),
        ("if 4 <= y goto L", {"y"}, set()),
        ("if x > y goto L", {"x", "y"}, set()),
        ("if x >= 0 goto L", {"x"}, set()),
        ("return x", {"x"}, set()),
        ("return -12", set(), set()),
        ("return", set(), set()),
    ],
)
def test_instruction_uses_and_definitions(
    source, expected_uses, expected_defs
):
    instruction = ir.parse_line(source, 1)
    assert instruction.uses() == expected_uses
    assert instruction.defs() == expected_defs


@pytest.mark.parametrize(
    "operator, left, right, expected",
    [
        ("+", 0, 0, 0), ("+", 2, 3, 5), ("+", -2, 3, 1),
        ("-", 0, 0, 0), ("-", 8, 3, 5), ("-", 2, 5, -3),
        ("*", 0, 7, 0), ("*", 3, 4, 12), ("*", -3, 4, -12),
        ("/", 8, 2, 4), ("/", 7, 2, 3), ("/", -7, 2, -4),
        ("%", 8, 3, 2), ("%", 9, 3, 0), ("%", -7, 3, 2),
    ],
)
def test_constant_propagation_arithmetic(operator, left, right, expected):
    source = f"a = {left}\nb = {right}\nc = a {operator} b\nreturn c\n"
    graph, _, out_map, _ = solve_source(
        source, analyses.ConstantPropagation
    )
    assert out_map[graph.blocks[0]]["c"] == expected


@pytest.mark.parametrize(
    "first, second, expected",
    [
        (analyses.UNDEF, analyses.UNDEF, analyses.UNDEF),
        (analyses.UNDEF, 0, 0), (0, analyses.UNDEF, 0),
        (analyses.UNDEF, -3, -3), (-3, analyses.UNDEF, -3),
        (analyses.NAC, analyses.UNDEF, analyses.NAC),
        (analyses.UNDEF, analyses.NAC, analyses.NAC),
        (analyses.NAC, 4, analyses.NAC), (4, analyses.NAC, analyses.NAC),
        (1, 1, 1), (0, 0, 0), (-2, -2, -2),
        (1, 2, analyses.NAC), (0, -1, analyses.NAC),
        (-5, 5, analyses.NAC),
    ],
)
def test_constant_lattice_meet(first, second, expected):
    assert analyses._meet_value(first, second) == expected


@pytest.mark.parametrize(
    "left, operator, right, expected",
    [
        (1, "+", 2, 3), (0, "+", 0, 0), (-1, "+", 4, 3),
        (4, "-", 9, -5), (0, "-", 7, -7), (-3, "-", -2, -1),
        (3, "*", 5, 15), (0, "*", 9, 0), (-3, "*", 4, -12),
        (9, "/", 2, 4), (1, "/", 2, 0), (-9, "/", 2, -5),
        (9, "%", 4, 1), (8, "%", 4, 0), (-8, "%", 3, 1),
    ],
)
def test_constant_apply_arithmetic(left, operator, right, expected):
    assert analyses._apply(operator, left, right) == expected


@pytest.mark.parametrize("operator", ["+", "*"])
def test_commutative_expression_keys_are_order_independent(operator):
    assert analyses.expr_key(
        "a", operator, "b"
    ) == analyses.expr_key("b", operator, "a")


@pytest.mark.parametrize("operator", ["-", "/", "%"])
def test_noncommutative_expression_keys_preserve_operand_order(operator):
    assert analyses.expr_key(
        "a", operator, "b"
    ) != analyses.expr_key("b", operator, "a")


@pytest.mark.parametrize("operator", ["+", "-", "*", "/", "%"])
def test_available_expression_is_generated_for_each_binary_operator(operator):
    source = f"a = 8\nb = 2\nt = a {operator} b\nreturn t\n"
    graph, _, out_map, _ = solve_source(
        source, analyses.AvailableExpressions
    )
    assert ("a", operator, "b") in out_map[graph.blocks[0]]


@pytest.mark.parametrize("redefined", ["a", "b"])
@pytest.mark.parametrize("operator", ["+", "-", "*", "/", "%"])
def test_available_expression_is_killed_when_either_operand_is_redefined(
    redefined, operator
):
    source = (
        f"a = 8\nb = 2\nt = a {operator} b\n"
        f"goto L\nL:\n{redefined} = 10\nreturn t\n"
    )
    graph, _, out_map, _ = solve_source(
        source, analyses.AvailableExpressions
    )
    label = next(block for block in graph.blocks if block.name == "L")
    assert ("a", operator, "b") not in out_map[label]


@pytest.mark.parametrize("relop", ["==", "!=", "<", "<=", ">", ">="])
def test_conditional_jump_builds_target_and_fallthrough_edges(relop):
    graph = build_cfg(
        f"if x {relop} y goto L\nreturn x\nL:\nreturn y\n"
    )
    branch = graph.entry
    assert len(graph.successors(branch)) == 2
    assert all(
        branch in graph.predecessors(successor)
        for successor in graph.successors(branch)
    )
    assert len(graph.exits) == 2


@pytest.mark.parametrize(
    "value", [0, 1, 2, 7, 11, 99, -1, -9, 1024, -1024]
)
def test_single_block_constant_program_has_one_exit_and_propagates_value(value):
    graph, in_map, out_map, steps = solve_source(
        f"result = {value}\nreturn result\n",
        analyses.ConstantPropagation,
    )
    assert len(graph.blocks) == 1
    assert graph.exits == graph.blocks
    assert out_map[graph.entry]["result"] == value
    assert in_map[graph.entry] == {}
    assert steps >= 1


@pytest.mark.parametrize(
    "initial, final",
    [
        (0, 1), (1, 2), (2, 3), (5, 6), (-1, 0),
        (-8, -7), (10, 20), (99, 100), (7, 7), (3, -3),
    ],
)
def test_reaching_definitions_keeps_last_definition_in_single_block(
    initial, final
):
    graph, _, out_map, _ = solve_source(
        f"x = {initial}\nx = {final}\nreturn x\n",
        analyses.ReachingDefinitions,
    )
    definitions = {
        definition
        for definition in out_map[graph.entry]
        if definition[2] == "x"
    }
    assert definitions == frozenset({("B0", 1, "x")})


@pytest.mark.parametrize(
    "variable",
    ["a", "b", "c", "count", "index", "total", "_tmp", "value2",
     "left", "right"],
)
def test_live_variable_flows_back_across_predecessor_edge(variable):
    graph, in_map, _, _ = solve_source(
        f"goto L\nL:\nreturn {variable}\n",
        analyses.LiveVariables,
    )
    label_block = next(
        block for block in graph.blocks if block.name == "L"
    )
    assert variable in in_map[label_block]
    assert variable in in_map[graph.entry]


@pytest.mark.parametrize(
    "variable",
    ["a", "b", "c", "count", "index", "total", "_tmp", "value2",
     "left", "right"],
)
def test_live_variable_is_not_live_before_its_definition(variable):
    graph, in_map, _, _ = solve_source(
        f"{variable} = 5\nreturn {variable}\n",
        analyses.LiveVariables,
    )
    assert variable not in in_map[graph.entry]


@pytest.mark.parametrize("example", ["sequential", "branching", "looping"])
@pytest.mark.parametrize(
    "analysis_cls",
    [
        analyses.ReachingDefinitions,
        analyses.AvailableExpressions,
        analyses.LiveVariables,
        analyses.ConstantPropagation,
    ],
)
def test_solver_results_satisfy_analysis_equations_on_examples(
    example, analysis_cls
):
    with open(f"examples/{example}.tac", encoding="utf-8") as handle:
        graph = build_cfg(handle.read())

    analysis = analysis_cls(graph)
    in_map, out_map, steps = solver.solve(graph, analysis)

    assert steps >= len(graph.blocks)
    assert set(in_map) == set(graph.blocks)
    assert set(out_map) == set(graph.blocks)

    if analysis.direction == "forward":
        for block in graph.blocks:
            if block is graph.entry:
                expected_in = analysis.boundary_value()
            else:
                predecessors = graph.predecessors(block)
                expected_in = (
                    analysis.meet([out_map[p] for p in predecessors])
                    if predecessors
                    else analysis.top_value()
                )

            assert in_map[block] == expected_in, f"IN[{block.name}]"
            assert out_map[block] == analysis.transfer(
                block, in_map[block]
            ), f"OUT[{block.name}]"

    else:
        for block in graph.blocks:
            if block in graph.exits:
                expected_out = analysis.boundary_value()
            else:
                successors = graph.successors(block)
                expected_out = (
                    analysis.meet([in_map[s] for s in successors])
                    if successors
                    else analysis.top_value()
                )

            assert out_map[block] == expected_out, f"OUT[{block.name}]"
            assert in_map[block] == analysis.transfer(
                block, out_map[block]
            ), f"IN[{block.name}]"
