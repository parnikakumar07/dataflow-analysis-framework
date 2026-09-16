"""
Command-line entry point.

Usage:
    python -m dataflow.cli examples/branching.tac
    python -m dataflow.cli examples/branching.tac --analysis live
    python -m dataflow.cli examples/branching.tac --dot out.dot
    python -m dataflow.cli                          # no file -> type a program interactively
    python -m dataflow.cli --stdin < my_program.tac  # or pipe one in
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


def read_source_interactively():
    """Prompts the user to type a TAC program directly into the terminal."""
    print("No file given -- type your TAC program below.")
    print("Finish with a line containing only END, or press Ctrl+D.")
    lines = []
    try:
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines)


def run_source(source, which="all", dot_path=None):
    """Runs the framework on TAC source text, regardless of where it came from."""
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


def run(tacfile, which="all", dot_path=None):
    """Runs the framework on a TAC file on disk. Kept for backward compatibility."""
    with open(tacfile) as f:
        source = f.read()
    run_source(source, which, dot_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generic Data-Flow Analysis Framework")
    parser.add_argument("tacfile", nargs="?", default=None,
                         help="path to a .tac source file (omit to type a program interactively)")
    parser.add_argument("--stdin", action="store_true",
                         help="read the TAC program from standard input (e.g. piped in)")
    parser.add_argument("--analysis", choices=list(ANALYSES) + ["all"], default="all")
    parser.add_argument("--dot", help="also write the CFG to this .dot file", default=None)
    args = parser.parse_args(argv)

    if args.tacfile:
        with open(args.tacfile) as f:
            source = f.read()
    elif args.stdin:
        source = sys.stdin.read()
    else:
        source = read_source_interactively()

    run_source(source, args.analysis, args.dot)


if __name__ == "__main__":
    sys.exit(main())
