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
- Investigated the two items originally listed below under "known
limitations" by actually running the code instead of trusting the
description, and fixed both — see "Resolved during testing" below for
what each one actually was and what changed. Added 3 new tests covering
them (`test_ir.py`, `test_analyses.py`).
- **Full suite status: 42/42 tests passing** (34 unit — parser, CFG,
solver mechanics, per-analysis correctness — + 8 integration tests).
- **Next:** Review 3 report/demo-sequence integration work.

**2026-10-26**
- Reviewed and verified the changes Amrutha, Khushi, and Jani merged into
`main` via PRs #1–#6 on 2026-10-25: Amrutha's duplicate-label detection
and stricter parser/CFG validation; Khushi's backward-solver fix plus 187
parameterized regression tests and the new Streamlit dashboard
(`app.py`); Jani's hand-derived analysis-correctness tests. Confirmed
live (not just from commit messages) that the backward-solver fix
changes real output: Live Variables on `branching.tac`/`looping.tac` now
converges in 7/11 steps.
- Found and fixed one real bug via TDD in the Streamlit dashboard:
`app.py`'s `ANALYSES` dict sent `--analysis rd` / `--analysis ae` to the
CLI, but `dataflow/cli.py` only accepts `reaching`/`available`/`live`/
`constprop`/`all` — so picking "Reaching Definitions" or "Available
Expressions" in the dashboard failed with an argparse error instead of
running. Added `tests/test_app_integration.py` (RED: failed against the
unmodified `app.py`, skips cleanly if `streamlit` isn't installed since
it's an optional dependency), fixed the two alias strings (GREEN), reran
the full suite to confirm nothing else broke.
- **Full suite status: 257/257 tests passing.**
- Logged Jani's 2026-10-25 entry below on her behalf — she's unwell and
asked me to record it for her.
- **Next:** performance evaluation on larger synthetic CFGs (Khushi,
still open) and a full-team live-demo rehearsal (all members, still
open) — see the objective-compliance / Review 2 closure document.


## Amrutha — TAC Parsing / IR / CFG Construction

**2026-10-25**
- Improved TAC parser validation to reject malformed labels and invalid or chained binary expressions.
- Updated CFG basic-block construction to detect duplicate labels while preserving undefined jump-target validation.
- Added regression tests in `tests/test_ir.py` and `tests/test_cfg.py`.
- Verified the parser, CFG construction, and full test suite.
- Updated the README to document parser validation, CFG validation, usage, and test coverage.
- Changes pushed to branch `amrutha-parser-cfg-tests` (commit `c94f83a`).

**Integration verification**
- Ran the sequential, branching, and looping TAC examples through the CLI.
- Ran the complete automated test suite and recorded the resulting test count.




## Khushi — Generic Worklist Solver & Architecture

**2026-10-25 — Extended Solver Coverage and Backward-Flow Fix**

- Fixed backward data-flow solver edge handling so backward analyses use the CFG's actual predecessor and successor relationships correctly.
- Added `tests/test_extended_coverage.py` with parameterized regression coverage for TAC parsing, instruction uses/definitions, constant propagation, available expressions, reaching definitions, live variables, CFG edges, and solver fixed-point equations.
- Updated `tests/test_integration.py` to verify expected worklist-step counts for the analyses on sequential, branching, and looping examples.
- Verified the complete test suite: **256 tests passed**.
- Committed as `0956651` on branch `khushi-extend-coverage`; pull request created and merged into `main`.
- Synced local `main` with the merged changes and reran the test suite successfully.

**Status:** Generic worklist solver and extended regression coverage completed. No further solver changes are currently required unless new issues are identified during integration or review.

## Jani — Four Analyses — Correctness & Demonstration

**2026-10-25** 
- Added 15 hand-derived correctness tests across all four analyses in
`tests/test_analyses.py` (commit `2098a38`): same-block redefinition
killing an earlier reaching definition; definitions from different
predecessors both reaching a merge block; a definition killed on only
one path while surviving on the other; loop back-edge definitions
reaching the loop header; `AvailableExpressions` invalidated by either
operand being redefined (including through the canonical commutative
key added earlier this week); a loop-invariant expression staying
available around a loop; `LiveVariables` checked directly against the
USE/DEF equations (not just against the solver's own output) on both
`branching.tac` and `looping.tac`; and `ConstantPropagation`
reassignment and equal-value-merge cases.
- Verified against `examples/branching.tac` / `examples/looping.tac`
plus hand-traced inline TAC snippets with the expected GEN/KILL/USE/DEF
sets worked out in comments.
- **Next:** prepare the 3 demonstration examples with expected results
(per the Review 3 work-split plan).

---

## Resolved during testing (previously listed as limitations)

Both items below were originally filed as "documented scope decisions, not
bugs." Re-checking by actually running the code (not just re-reading the
description) found the second one was worse than described, so both got
fixed rather than left as limitations:

- **Commutative expression normalization.** `AvailableExpressions` was
  keying expressions as literal `(src1, op, src2)` tuples, so `a+b` and
  `b+a` were tracked as two different expressions even though they compute
  the same value — a real missed optimization opportunity across branches.
  Fixed with a canonical key (`analyses.expr_key`) that sorts the operands
  for commutative ops (`+`, `*`) only, leaving non-commutative ops (`-`,
  `/`, `%`) untouched. Covered by two new tests in `test_analyses.py`.
- **Unary minus on a variable (`x = -y`).** This was NOT just unsupported
  as previously stated — running it showed the parser silently parsed it
  as a copy from a phantom variable literally named `-y`, which never
  crashes but quietly produces a wrong, confusing result if anyone tried
  it live during the demo. Fixed by desugaring `x = -y` to the equivalent
  `x = 0 - y` at parse time, so it reuses all the existing binop handling
  (uses/defs, every analysis, constant folding) with no changes needed
  outside `ir.py`. Covered by a new test in `test_ir.py`, plus manual
  end-to-end verification that `y = 5; x = -y` correctly folds to `x = -5`.
