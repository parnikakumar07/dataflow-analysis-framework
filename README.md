# Generic Data-Flow Analysis Framework

BCSE307 Compiler Design | Project A34 | Team 9

A reusable monotone data-flow framework over a CFG: one generic iterative
solver, four pluggable analyses. Matches the Review 1 architecture —
the `dataflow/` modules below map 1:1 onto the five-layer diagram from
the Review 1 slide deck.

## Layout

```
dataflow/
  ir.py          IR / TAC Parser        -> parses .tac text into Instr objects
  cfg.py         Basic Block + CFG      -> leader algorithm, builds the CFG
  solver.py      Generic Solver         -> the ONE worklist fixpoint engine
  analyses.py    Analysis Modules       -> Reaching Defs, Available Exprs,
                                           Live Variables, Constant Propagation
  visualizer.py  Result / Visualizer    -> pretty-prints IN/OUT, emits .dot
  cli.py         entry point
examples/        sequential.tac, branching.tac, looping.tac
tests/           27 unit tests (parser, CFG construction, solver mechanics,
                 and hand-derived correctness checks per analysis)
```

No third-party dependencies — standard library only (matches the Review 1
feasibility slide). Graphviz is optional and only used if you want to
render the `.dot` output to an image.

## Run it

```bash
# run all four analyses on an example
python3 -m dataflow.cli examples/branching.tac

# just one analysis
python3 -m dataflow.cli examples/looping.tac --analysis live

# also export the CFG as a .dot file
python3 -m dataflow.cli examples/branching.tac --dot cfg.dot
dot -Tpng cfg.dot -o cfg.png   # only if Graphviz is installed
```

Analysis names: `reaching`, `available`, `live`, `constprop`, or `all`.

## Test it

```bash
pip install pytest        # only needed for the test suite itself
python3 -m pytest tests/ -v
```

27/27 tests pass as delivered — covering the parser, CFG construction
(including the branching-merge and looping-back-edge cases), solver
boundary conditions, and hand-derived expected results for each analysis
on the sequential / branching / looping test corpus (per the Review 1
feasibility slide's stated test strategy).

## Writing your own .tac programs

```
L1:                     label
x = 5                   constant assignment
x = y                   copy assignment
x = y + z               binary op: + - * / %
if x < y goto L2        conditional jump: == != < <= > >=
goto L3                 unconditional jump
return x                return (x optional)
# comment
```

## Adding a fifth analysis

Subclass `DataFlowAnalysis` in `analyses.py` and implement `direction`,
`boundary_value()`, `top_value()`, `meet()`, and `transfer()`. Register it
in the `ANALYSES` dict in `cli.py`. `solver.py` never changes — that
separation is the whole point of the "generic framework" problem
statement.

## Where this maps onto your Review 1 deck

| Slide concept | Code |
|---|---|
| IR / TAC Parser module | `ir.py` |
| Basic Block Builder | `cfg.build_basic_blocks` |
| CFG Builder | `cfg.build_cfg` |
| Generic Solver | `solver.solve` |
| Analysis Modules (plug-in interface) | `analyses.DataFlowAnalysis` subclasses |
| Result / Visualizer | `visualizer.py` |
| "Validate using sequential, branching, looping test cases" | `examples/*.tac` + `tests/test_analyses.py` |
| "Evaluate correctness, convergence, basic performance" | test assertions + `steps` counter returned by the solver |
