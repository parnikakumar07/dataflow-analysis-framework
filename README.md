# Generic Data-Flow Analysis Framework

**BCSE307 Compiler Design — Project A34 — Team 9**

A reusable, monotone data-flow analysis framework built over a control-flow
graph (CFG): one generic worklist solver, four pluggable analyses, zero
third-party dependencies. Point it at any supported TAC (three-address code)
program and it builds the CFG, runs the requested analysis to a fixpoint,
and prints the IN/OUT sets for every basic block.

The design mirrors the Review 1 architecture directly — every module below
maps one-to-one onto the five-layer pipeline from the Review 1 slide deck
(see [Architecture](#architecture) below).

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Supported Analyses](#supported-analyses)
- [Example Walkthrough](#example-walkthrough)
- [Writing Your Own .tac Programs](#writing-your-own-tac-programs)
- [Testing](#testing)
- [Architecture](#architecture)
- [Extending the Framework](#extending-the-framework)

---

## Features

- **One generic solver, four analyses.** `solver.py` implements a single
  worklist fixpoint algorithm that works for any forward or backward,
  may/must analysis — it never changes when a new analysis is added.
- **Four classical analyses out of the box:** Reaching Definitions,
  Available Expressions, Live Variables, and Constant Propagation.
- **Multiple input modes:** read from a file, pipe a program in via
  `--stdin`, or type one interactively at the terminal.
- **CFG export:** emit the control-flow graph as a Graphviz `.dot` file.
- **Clean failure on bad input.** Malformed lines, undefined jump targets,
  and missing files all produce a short `Error: ...` message and a
  non-zero exit code — never a raw Python traceback.
- **Zero dependencies.** Standard library only. `pytest` is needed only to
  run the test suite, not the framework itself.
- **Correct on commutative and unary expressions.** `AvailableExpressions`
  recognizes `a + b` and `b + a` as the same expression, and `x = -y`
  (unary negation of a variable) is fully supported — see
  [Writing Your Own .tac Programs](#writing-your-own-tac-programs).
- **42 automated tests** — 34 unit tests exercising the parser, CFG
  builder, solver mechanics, and each analysis's correctness, plus 8
  integration tests that run the actual CLI as a subprocess.

## Project Structure

```
dataflow/
  ir.py          IR / TAC Parser        -> parses .tac text into Instr objects
  cfg.py         Basic Block + CFG      -> leader algorithm, builds the CFG
  solver.py      Generic Solver         -> the one worklist fixpoint engine
  analyses.py    Analysis Modules       -> Reaching Defs, Available Exprs,
                                           Live Variables, Constant Propagation
  visualizer.py  Result / Visualizer    -> pretty-prints IN/OUT, emits .dot
  cli.py         Entry point            -> argument parsing, I/O, error handling
examples/
  sequential.tac   straight-line code, one basic block
  branching.tac    if/else merging back into one block
  looping.tac      a back-edge / loop
tests/
  test_ir.py            parser unit tests (34 unit tests total across these four files)
  test_cfg.py           CFG construction unit tests
  test_solver.py        solver mechanics unit tests
  test_analyses.py      hand-derived correctness per analysis
  test_integration.py   black-box CLI tests (subprocess-level, 8 tests)
WORKDONE.md      internal team progress log (not a substitute for commits)
```

## Installation

No installation step is required beyond having Python 3 installed — the
framework itself uses only the standard library.

```bash
git clone https://github.com/parnikakumar07/dataflow-analysis-framework.git
cd dataflow-analysis-framework
```

Graphviz is optional, and only needed if you want to render a `.dot` file
to an image (`dot -Tpng cfg.dot -o cfg.png`).

## Usage

```bash
# Run all four analyses on a file
python3 -m dataflow.cli examples/branching.tac

# Run just one analysis
python3 -m dataflow.cli examples/looping.tac --analysis live

# Also export the CFG as a .dot file
python3 -m dataflow.cli examples/branching.tac --dot cfg.dot

# Pipe a program in via stdin
python3 -m dataflow.cli --stdin < examples/sequential.tac

# No file given -> type a program interactively, end with a line containing END
python3 -m dataflow.cli
```

| Flag | Description |
|---|---|
| `tacfile` (positional) | Path to a `.tac` source file. Omit to type a program interactively. |
| `--stdin` | Read the program from standard input instead of a file. |
| `--analysis {reaching,available,live,constprop,all}` | Which analysis to run. Defaults to `all`. |
| `--dot PATH` | Also write the CFG to this `.dot` file. |

## Supported Analyses

| Analysis | Flag | Direction | Meet Operator | Lattice Value |
|---|---|---|---|---|
| Reaching Definitions | `reaching` | forward | union ("may") | set of `(block, index, var)` definitions |
| Available Expressions | `available` | forward | intersection ("must") | set of `(src1, op, src2)` expressions |
| Live Variables | `live` | backward | union ("may") | set of variable names |
| Constant Propagation | `constprop` | forward | meet-to-NAC | variable to constant, or NAC |

## Example Walkthrough

Given `examples/sequential.tac`:

```
# Straight-line code, no branches -- one basic block.
x = 1
y = 2
z = x + y
w = z
return w
```

Running Constant Propagation on it:

```bash
$ python3 -m dataflow.cli examples/sequential.tac --analysis constprop
Parsed 5 instructions into 1 basic blocks.
Blocks: B0

=== ConstantPropagation (forward) ===
[B0]
    x = 1
    y = 2
    z = x + y
    w = z
    return w
    IN  = {}
    OUT = {w=3, x=1, y=2, z=3}
  (converged in 1 worklist steps, 1 blocks)
```

Given a branching program (`examples/branching.tac`):

```
# Simple if/else merging back into one block.
x = 1
y = 2
if x < y goto L_true
z = 99
goto L_end
L_true:
z = x + y
L_end:
w = z
return w
```

Running Reaching Definitions on it shows the two branches' definitions of
`z` both reaching the merge point, `L_end`:

```bash
$ python3 -m dataflow.cli examples/branching.tac --analysis reaching
Parsed 10 instructions into 4 basic blocks.
Blocks: B0, B3, L_true, L_end

=== ReachingDefinitions (forward) ===
[B0]
    x = 1
    y = 2
    if x < y goto L_true
    IN  = {}
    OUT = {('B0', 0, 'x'), ('B0', 1, 'y')}
[B3]
    z = 99
    goto L_end
    IN  = {('B0', 0, 'x'), ('B0', 1, 'y')}
    OUT = {('B0', 0, 'x'), ('B0', 1, 'y'), ('B3', 0, 'z')}
[L_true]
    L_true:
    z = x + y
    IN  = {('B0', 0, 'x'), ('B0', 1, 'y')}
    OUT = {('B0', 0, 'x'), ('B0', 1, 'y'), ('L_true', 1, 'z')}
[L_end]
    L_end:
    w = z
    return w
    IN  = {('B0', 0, 'x'), ('B0', 1, 'y'), ('B3', 0, 'z'), ('L_true', 1, 'z')}
    OUT = {('B0', 0, 'x'), ('B0', 1, 'y'), ('B3', 0, 'z'), ('L_end', 1, 'w'), ('L_true', 1, 'z')}
  (converged in 4 worklist steps, 4 blocks)
```

Notice `L_end`'s `IN` set correctly contains **both** `('B3', 0, 'z')` and
`('L_true', 1, 'z')` — the definition of `z` reaches the merge point along
either branch, which is exactly what a "may" / union analysis should do.

## Writing Your Own .tac Programs

```
L1:                     label
x = 5                   constant assignment
x = y                   copy assignment
x = y + z               binary op: + - * / %
x = -y                  unary negation (desugars to x = 0 - y internally)
if x < y goto L2        conditional jump: == != < <= > >=
goto L3                 unconditional jump
return x                return (x optional)
# comment
```

## Testing

```bash
pip install pytest        # only needed for the test suite itself
python3 -m pytest tests/ -v
```

**42/42 tests passing** as delivered:

- `test_ir.py`, `test_cfg.py`, `test_solver.py`, `test_analyses.py` (34
  tests) — unit tests calling the parser, CFG builder, solver, and
  analyses directly, including edge cases added for Review 3: an empty
  program, a function with multiple `return` statements (multiple CFG
  exits), a block left unreachable by an unconditional jump, unary
  negation desugaring to the equivalent binop, and `AvailableExpressions`
  recognizing `a + b` and `b + a` as the same expression (with a
  regression test confirming `a - b` and `b - a` correctly stay distinct).
- `test_integration.py` (8 tests) — black-box tests that invoke
  `python3 -m dataflow.cli` as a real subprocess, exactly as it would be
  run at a demo: file mode, `--stdin` mode, interactive mode, `--dot`
  export, and — found via test-driven development — confirming the CLI
  fails cleanly on malformed input or an undefined label instead of
  leaking a raw Python traceback.

## Architecture

| Review 1 slide concept | Code |
|---|---|
| IR / TAC Parser module | `ir.py` |
| Basic Block Builder | `cfg.build_basic_blocks` |
| CFG Builder | `cfg.build_cfg` |
| Generic Solver | `solver.solve` |
| Analysis Modules (plug-in interface) | `analyses.DataFlowAnalysis` subclasses |
| Result / Visualizer | `visualizer.py` |
| "Validate using sequential, branching, looping test cases" | `examples/*.tac` + `tests/test_analyses.py` |
| "Evaluate correctness, convergence, basic performance" | test assertions + the `steps` counter returned by the solver |

## Extending the Framework

Adding a fifth analysis requires no changes to the solver:

1. Subclass `DataFlowAnalysis` in `analyses.py`.
2. Implement `direction`, `boundary_value()`, `top_value()`, `meet()`, and
   `transfer()`.
3. Register it in the `ANALYSES` dict in `cli.py`.

`solver.py` is untouched by this — that separation of the generic engine
from the per-analysis logic is the core design goal of the "generic
framework" problem statement.
