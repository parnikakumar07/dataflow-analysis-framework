"""
Command-line entry point.

Usage:
    python -m dataflow.cli examples/branching.tac
    python -m dataflow.cli examples/branching.tac --analysis live
    python -m dataflow.cli examples/branching.tac --dot out.dot
"""

import argparse
import sys

from . import ir
from . import cfg as cfg_mod
from . import solver
from . import analyses
from . import visualizer

ANALYSES = {
    "reaching": analyses.ReachingDefinitions,
    "available": analyses.AvailableExpressions,
    "live": analyses.LiveVariables,
    "constprop": analyses.ConstantPropagation,
}


def run(tacfile, which="all", dot_path=None):
    with open(tacfile) as f:
        source = f.read()

    instrs = ir.parse_program(source)
    cfg = cfg_mod.build_cfg(instrs)

    print(f"Parsed {len(instrs)} instructions into {len(cfg.blocks)} basic blocks.")
    print("Blocks:", ", ".join(b.name for b in cfg.blocks))

    if dot_path:
        with open(dot_path, "w") as f:
            f.write(visualizer.cfg_to_dot(cfg))
        print(f"CFG written to {dot_path} (render with: dot -Tpng {dot_path} -o cfg.png)")

    names = list(ANALYSES) if which == "all" else [which]
    for name in names:
        analysis = ANALYSES[name](cfg)
        IN, OUT, steps = solver.solve(cfg, analysis)
        visualizer.print_results(cfg, analysis.__class__.__name__, IN, OUT, analysis, steps)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generic Data-Flow Analysis Framework")
    parser.add_argument("tacfile", help="path to a .tac source file")
    parser.add_argument("--analysis", choices=list(ANALYSES) + ["all"], default="all")
    parser.add_argument("--dot", help="also write the CFG to this .dot file", default=None)
    args = parser.parse_args(argv)
    run(args.tacfile, args.analysis, args.dot)


if __name__ == "__main__":
    sys.exit(main())
