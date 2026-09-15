"""
Analysis Modules
----------------
The four classical analyses from the Review 1 scope. Each one only
defines: direction, boundary/top values, meet, and transfer. None of
them touch the worklist loop -- that's solver.py's job. This is the
"plug in by implementing a standard interface without modifying the
solver" architecture from the Review 1 slide deck.
"""

from .ir import BIN_OPS

UNDEF = "UNDEF"   # top of the constant-propagation lattice (no info yet)
NAC = "NAC"       # bottom of the lattice (provably not a single constant)


class DataFlowAnalysis:
    direction = None  # 'forward' or 'backward'

    def __init__(self, cfg):
        self.cfg = cfg

    def boundary_value(self):
        raise NotImplementedError

    def top_value(self):
        raise NotImplementedError

    def meet(self, values):
        raise NotImplementedError

    def transfer(self, block, value):
        raise NotImplementedError

    def format_value(self, value):
        if not value:
            return "{}"
        return "{" + ", ".join(str(x) for x in sorted(value, key=str)) + "}"


# ---------------------------------------------------------------------------
# Reaching Definitions -- forward, may, union
# ---------------------------------------------------------------------------
class ReachingDefinitions(DataFlowAnalysis):
    direction = "forward"

    def __init__(self, cfg):
        super().__init__(cfg)
        all_defs = {}  # var -> set of def-ids across the whole program
        for b in cfg.blocks:
            for idx, ins in enumerate(b.instrs):
                if ins.kind == "assign":
                    all_defs.setdefault(ins.dst, set()).add((b.name, idx, ins.dst))

        self.gen = {}
        self.kill = {}
        for b in cfg.blocks:
            last_def_in_block = {}
            for idx, ins in enumerate(b.instrs):
                if ins.kind == "assign":
                    last_def_in_block[ins.dst] = (b.name, idx, ins.dst)
            gen_b = set(last_def_in_block.values())
            kill_b = set()
            for var, def_id in last_def_in_block.items():
                kill_b |= all_defs[var] - {def_id}
            self.gen[b] = gen_b
            self.kill[b] = kill_b

    def boundary_value(self):
        return frozenset()

    def top_value(self):
        return frozenset()

    def meet(self, values):
        result = set()
        for v in values:
            result |= v
        return frozenset(result)

    def transfer(self, block, value):
        return frozenset(self.gen[block] | (value - self.kill[block]))


# ---------------------------------------------------------------------------
# Available Expressions -- forward, must, intersection
# ---------------------------------------------------------------------------
class AvailableExpressions(DataFlowAnalysis):
    direction = "forward"

    def __init__(self, cfg):
        super().__init__(cfg)
        universe = set()
        for b in cfg.blocks:
            for ins in b.instrs:
                if ins.kind == "assign" and ins.op in BIN_OPS:
                    universe.add((ins.src1, ins.op, ins.src2))
        self.universe = frozenset(universe)

        self.gen = {}
        self.kill = {}
        for b in cfg.blocks:
            gen_b = set()
            defined_vars = set()
            for ins in b.instrs:
                if ins.kind == "assign":
                    if ins.op in BIN_OPS:
                        gen_b.add((ins.src1, ins.op, ins.src2))
                    var = ins.dst
                    defined_vars.add(var)
                    gen_b = {e for e in gen_b if var not in (e[0], e[2])}
            kill_b = {e for e in self.universe if e[0] in defined_vars or e[2] in defined_vars}
            kill_b -= gen_b
            self.gen[b] = frozenset(gen_b)
            self.kill[b] = frozenset(kill_b)

    def boundary_value(self):
        return frozenset()

    def top_value(self):
        return self.universe

    def meet(self, values):
        if not values:
            return self.universe
        result = set(values[0])
        for v in values[1:]:
            result &= v
        return frozenset(result)

    def transfer(self, block, value):
        return frozenset(self.gen[block] | (value - self.kill[block]))

    def format_value(self, value):
        if not value:
            return "{}"
        return "{" + ", ".join(f"{a}{op}{b}" for (a, op, b) in sorted(value)) + "}"


# ---------------------------------------------------------------------------
# Live Variables -- backward, may, union
# ---------------------------------------------------------------------------
class LiveVariables(DataFlowAnalysis):
    direction = "backward"

    def __init__(self, cfg):
        super().__init__(cfg)
        self.use = {}
        self.defs = {}
        for b in cfg.blocks:
            used, defined = set(), set()
            for ins in b.instrs:
                for v in ins.uses():
                    if v not in defined:
                        used.add(v)
                defined |= ins.defs()
            self.use[b] = frozenset(used)
            self.defs[b] = frozenset(defined)

    def boundary_value(self):
        return frozenset()

    def top_value(self):
        return frozenset()

    def meet(self, values):
        result = set()
        for v in values:
            result |= v
        return frozenset(result)

    def transfer(self, block, value):
        # backward: input to transfer is OUT[block], output is IN[block]
        return frozenset(self.use[block] | (value - self.defs[block]))


# ---------------------------------------------------------------------------
# Constant Propagation -- forward, 3-level lattice per variable
#   UNDEF (top) -> concrete int constant -> NAC (bottom)
# ---------------------------------------------------------------------------
def _meet_value(v1, v2):
    if v1 == UNDEF:
        return v2
    if v2 == UNDEF:
        return v1
    if v1 == NAC or v2 == NAC:
        return NAC
    return v1 if v1 == v2 else NAC


def _apply(op, v1, v2):
    try:
        if op == "+":
            return v1 + v2
        if op == "-":
            return v1 - v2
        if op == "*":
            return v1 * v2
        if op == "/":
            return v1 // v2 if v2 != 0 else NAC
        if op == "%":
            return v1 % v2 if v2 != 0 else NAC
    except (ZeroDivisionError, ValueError, TypeError):
        return NAC
    return NAC


class ConstantPropagation(DataFlowAnalysis):
    direction = "forward"

    def boundary_value(self):
        return {}

    def top_value(self):
        return {}

    def _lookup(self, operand, env):
        if operand is None:
            return UNDEF
        try:
            return int(operand)
        except ValueError:
            return env.get(operand, UNDEF)

    def meet(self, values):
        result = {}
        for env in values:
            for var, val in env.items():
                result[var] = _meet_value(result.get(var, UNDEF), val)
        return result

    def transfer(self, block, value):
        env = dict(value)
        for ins in block.instrs:
            if ins.kind != "assign":
                continue
            if ins.op == "const":
                env[ins.dst] = int(ins.src1)
            elif ins.op == "copy":
                env[ins.dst] = self._lookup(ins.src1, env)
            elif ins.op in BIN_OPS:
                v1 = self._lookup(ins.src1, env)
                v2 = self._lookup(ins.src2, env)
                if v1 == NAC or v2 == NAC:
                    env[ins.dst] = NAC
                elif v1 == UNDEF or v2 == UNDEF:
                    env[ins.dst] = UNDEF
                else:
                    env[ins.dst] = _apply(ins.op, v1, v2)
        return env

    def format_value(self, value):
        if not value:
            return "{}"
        items = sorted(value.items())
        return "{" + ", ".join(f"{k}={v}" for k, v in items) + "}"
