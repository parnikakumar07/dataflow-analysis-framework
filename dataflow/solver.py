"""
Generic Solver
--------------
The single reusable fixpoint engine for the monotone data-flow framework
(Kildall 1973 / Kam & Ullman 1977 formulation). Every analysis module
plugs in by implementing the DataFlowAnalysis interface (see analyses.py);
this file never changes when a new analysis is added -- that separation
is the whole point of the "generic framework" problem statement.
"""


def solve(cfg, analysis, max_iterations=10000):
    """
    Runs the iterative worklist algorithm for `analysis` over `cfg`.

    Returns (IN, OUT, steps) where IN/OUT map Block -> analysis value,
    and `steps` is the number of worklist pops (a simple convergence /
    performance metric, per the Review 1 "evaluate ... performance"
    objective).
    """
    forward = analysis.direction == "forward"

    if forward:
        preds, succs = cfg.preds, cfg.succs
        boundary_blocks = {cfg.entry} if cfg.entry is not None else set()
    else:
        # Walking the CFG backward simply swaps the roles of preds/succs.
        preds, succs = cfg.succs, cfg.preds
        boundary_blocks = set(cfg.exits) if cfg.exits else (
            {cfg.blocks[-1]} if cfg.blocks else set()
        )

    IN = {b: analysis.top_value() for b in cfg.blocks}
    OUT = {b: analysis.top_value() for b in cfg.blocks}
    for b in boundary_blocks:
        if forward:
            IN[b] = analysis.boundary_value()
        else:
            OUT[b] = analysis.boundary_value()

    worklist = list(cfg.blocks)
    in_worklist = set(worklist)
    steps = 0

    while worklist:
        steps += 1
        if steps > max_iterations:
            raise RuntimeError(
                "solver did not converge within max_iterations -- "
                "check that the analysis's transfer/meet functions are monotone"
            )
        b = worklist.pop(0)
        in_worklist.discard(b)

        if forward:
            if b in boundary_blocks:
                new_in = analysis.boundary_value()
            else:
                incoming = [OUT[p] for p in preds.get(b, [])]
                new_in = analysis.meet(incoming) if incoming else analysis.top_value()
            IN[b] = new_in
            new_out = analysis.transfer(b, IN[b])
            if new_out != OUT[b]:
                OUT[b] = new_out
                for s in succs.get(b, []):
                    if s not in in_worklist:
                        worklist.append(s)
                        in_worklist.add(s)
        else:
            if b in boundary_blocks:
                new_out = analysis.boundary_value()
            else:
                incoming = [IN[s] for s in succs.get(b, [])]
                new_out = analysis.meet(incoming) if incoming else analysis.top_value()
            OUT[b] = new_out
            new_in = analysis.transfer(b, OUT[b])
            if new_in != IN[b]:
                IN[b] = new_in
                for p in preds.get(b, []):
                    if p not in in_worklist:
                        worklist.append(p)
                        in_worklist.add(p)

    return IN, OUT, steps
