# WORKDONE.md — Project A34 (Generic Data-Flow Analysis Framework), Team 9

This file is **not** a substitute for individual commits — everyone still pushes
their own work under their own GitHub account. This is just a shared log so
whoever picks up the repo next knows what's already done, what it verified,
and what's still open, without having to re-read every commit diff first.

**How to use it:** add a dated entry under your own section when you finish a
chunk of work. Keep it short — what you did, what you verified, what's left.
If you touch someone else's section (e.g. you found a bug in their module),
add a note there and tag your name.

---

## Objectives (from the Review 3 guidelines)

1. Demonstrate the generic data-flow framework working end-to-end on real
   TAC input (parser → CFG → solver → analyses → results).
2. Show correctness of each of the four analyses against hand-derived
   expected results.
3. Show robustness: edge cases, convergence behavior, and clean failure on
   bad input — not just the happy path.
4. Integration and project coordination — one working CLI, one coherent
   repo, one team able to explain the whole pipeline at the demo.

## Work split (reconciled with Review 2 + GitHub history)

| Member | Primary Responsibility |
|---|---|
| Parnika | Project Lead & System Integration — CLI, test infra, repo coherence |
| Amrutha | TAC Parsing / IR / CFG Construction |
| Khushi | Generic Worklist Solver & Architecture |
| Jani | Four Analyses — Correctness & Demonstration |

---

## Parnika — Project Lead & System Integration

**2026-10-24**
- Added `tests/test_integration.py` (8 new tests) — black-box CLI tests that
  run `python3 -m dataflow.cli` as a real subprocess, not internal function
  calls. Covers: all 4 analyses on `sequential`/`branching`/`looping`
  examples with documented worklist-step counts, `--analysis` filtering,
  `--stdin` vs file-mode output parity, interactive-mode `END` sentinel,
  `--dot` export shape, and clean failure on malformed input / undefined
  labels.
- Found via TDD that `dataflow/cli.py` leaked a raw Python traceback on bad
  input instead of failing cleanly (RED: 2 of the 8 new tests failed against
  the real unmodified file). Fixed `main()` to catch
  `FileNotFoundError` / `(ir.ParseError, ValueError)` and print a one-line
  `Error: ...` to stderr with exit code 1 (GREEN: all 8 pass). Manually
  re-confirmed against three real bad inputs (malformed line, undefined
  label, missing file) outside pytest too.
- Added 2 edge-case tests to `tests/test_cfg.py` (multiple `return`
  statements → multiple CFG exits; unreachable block after an unconditional
  `goto` still gets built correctly) and 2 to `tests/test_solver.py`
  (backward boundary condition applies independently at every exit; an
  unreachable block is still solved and feeds its successor) — both sets
  confirmed the existing implementation already handles these correctly, no
  bugs found.
- Updated `README.md` test count and edge-case description to match.
- **Full suite status: 39/39 tests passing** (31 unit — parser, CFG,
  solver mechanics, per-analysis correctness — + 8 new integration tests).
- **Next:** commit these to the repo (see commands below), then start on
  the Review 3 report/demo-sequence integration work.

## Amrutha — TAC Parsing / IR / CFG Construction

_(add your entries here)_

## Khushi — Generic Worklist Solver & Architecture

_(add your entries here)_

## Jani — Four Analyses — Correctness & Demonstration

_(add your entries here)_

---

## Open items / known limitations (not bugs — documented scope)

- `AvailableExpressions` keys expressions as literal `(src1, op, src2)`
  tuples with no commutative normalization, so `a+b` and `b+a` are treated
  as distinct expressions. Worth mentioning if asked in the demo.
- The parser doesn't support unary minus on a variable (`x = -y`) — only a
  literal negative constant (`x = -5`). Deliberate scope limitation.
