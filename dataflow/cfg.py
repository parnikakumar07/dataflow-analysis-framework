"""
Basic Block Builder + CFG Builder
---------------------------------
Partitions a flat instruction list into basic blocks (leader algorithm)
and connects them into a control-flow graph.

Leaders:
  - the first instruction
  - any instruction that is the target of a jump/cond_jump (i.e. a label
    that is jumped to)
  - any instruction immediately following a jump, cond_jump, or return
"""

from .ir import Instr


class Block:
    __slots__ = ("name", "instrs")

    def __init__(self, name):
        self.name = name
        self.instrs = []

    def __repr__(self):
        return f"Block({self.name}, {len(self.instrs)} instrs)"


class CFG:
    def __init__(self):
        self.blocks = []            # list[Block], in program order
        self.succs = {}             # Block -> list[Block]
        self.preds = {}             # Block -> list[Block]
        self.entry = None           # Block
        self.exits = []             # list[Block] with no successors
        self.label_to_block = {}    # str -> Block

    def successors(self, b):
        return self.succs.get(b, [])

    def predecessors(self, b):
        return self.preds.get(b, [])


def build_basic_blocks(instrs):
    if not instrs:
        return []

    label_positions = {ins.label: i for i, ins in enumerate(instrs) if ins.kind == "label"}

    leaders = {0}
    for i, ins in enumerate(instrs):
        if ins.kind in ("jump", "cond_jump"):
            if ins.label not in label_positions:
                raise ValueError(f"undefined label target: {ins.label!r}")
            leaders.add(label_positions[ins.label])
            if i + 1 < len(instrs):
                leaders.add(i + 1)
        elif ins.kind == "return" and i + 1 < len(instrs):
            leaders.add(i + 1)

    ordered = sorted(leaders)
    blocks = []
    for idx, start in enumerate(ordered):
        end = ordered[idx + 1] if idx + 1 < len(ordered) else len(instrs)
        chunk = instrs[start:end]
        name = chunk[0].label if chunk[0].kind == "label" else f"B{start}"
        b = Block(name)
        b.instrs = chunk
        blocks.append(b)
    return blocks


def build_cfg(instrs):
    blocks = build_basic_blocks(instrs)
    cfg = CFG()
    cfg.blocks = blocks

    for b in blocks:
        cfg.succs[b] = []
        cfg.preds[b] = []
        if b.instrs and b.instrs[0].kind == "label":
            cfg.label_to_block[b.instrs[0].label] = b

    def block_of(label):
        if label not in cfg.label_to_block:
            raise ValueError(f"undefined label target: {label!r}")
        return cfg.label_to_block[label]

    for idx, b in enumerate(blocks):
        last = b.instrs[-1] if b.instrs else None
        nxt = blocks[idx + 1] if idx + 1 < len(blocks) else None

        if last is None:
            if nxt is not None:
                cfg.succs[b].append(nxt)
        elif last.kind == "jump":
            cfg.succs[b].append(block_of(last.label))
        elif last.kind == "cond_jump":
            cfg.succs[b].append(block_of(last.label))
            if nxt is not None:
                cfg.succs[b].append(nxt)
        elif last.kind == "return":
            pass  # no successors -- exit point
        else:
            if nxt is not None:
                cfg.succs[b].append(nxt)

    for b in blocks:
        for s in cfg.succs[b]:
            cfg.preds[s].append(b)

    cfg.entry = blocks[0] if blocks else None
    cfg.exits = [b for b in blocks if not cfg.succs[b]]
    return cfg
