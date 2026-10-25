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
    and `steps` is the number of worklist pops.
    """
    forward = analysis.direction == "forward"

    # Keep the CFG's actual edge directions in these maps for both analysis
    # directions. Forward flow reads predecessor OUT values and schedules
    # successors; backward flow reads successor IN values and schedules
    # predecessors. Swapping these maps would reverse the equations.
    preds, succs = cfg.preds, cfg.succs

    if forward:
        boundary_blocks = {cfg.entry} if cfg.entry is not None else set()
    else:
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
                new_in = (
                    analysis.meet(incoming)
                    if incoming
                    else analysis.top_value()
                )

            IN[b] = new_in
            new_out = analysis.transfer(b, IN[b])

            if new_out != OUT[b]:
                OUT[b] = new_out

                for successor in succs.get(b, []):
                    if successor not in in_worklist:
                        worklist.append(successor)
                        in_worklist.add(successor)

        else:
            if b in boundary_blocks:
                new_out = analysis.boundary_value()
            else:
                incoming = [IN[s] for s in succs.get(b, [])]
                new_out = (
                    analysis.meet(incoming)
                    if incoming
                    else analysis.top_value()
                )

            OUT[b] = new_out
            new_in = analysis.transfer(b, OUT[b])

            if new_in != IN[b]:
                IN[b] = new_in

                for predecessor in preds.get(b, []):
                    if predecessor not in in_worklist:
                        worklist.append(predecessor)
                        in_worklist.add(predecessor)

    return IN, OUT, steps