"""
Generic Data-Flow Analysis Framework
BCSE307 Compiler Design | Project A34 | Team 9

A reusable monotone data-flow framework over a control-flow graph (CFG),
separating the generic iterative solving engine from analysis-specific
gen/kill and meet/transfer logic.

Modules (mirrors the Review 1 architecture slide):
    ir.py          -> IR / TAC Parser
    cfg.py         -> Basic Block Builder + CFG Builder
    solver.py      -> Generic Solver (worklist fixpoint engine)
    analyses.py    -> Analysis Modules (Reaching Defs, Available Exprs,
                       Live Variables, Constant Propagation)
    visualizer.py  -> Result / Visualizer
"""

__version__ = "0.1.0"
