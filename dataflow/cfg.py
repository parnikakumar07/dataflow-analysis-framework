
"""
Basic Block Builder + CFG Builder
---------------------------------
Partitions a flat instruction list into basic blocks (leader algorithm)
and connects them into a control-flow graph.

Leaders:
  - the first instruction
  - any instruction that is the target of a jump/cond_jump
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
        self.blocks = []
        self.succs = {}
        self.preds = {}
        self.entry = None
        self.exits = []
        self.label_to_block = {}

    def successors(self, b):
        return self.succs.get(b, [])

    def predecessors(self, b):
        return self.preds.get(b, [])


def build_basic_blocks(instrs):
    if not instrs:
        return []

    label_positions = {}

    for i, ins in enumerate(instrs):
        if ins.kind == "label":
            if ins.label in label_positions:
                raise ValueError(f"duplicate label: {ins.label!r}")
            label_positions[ins.label] = i

    leaders = {0}

    for i, ins in enumerate(instrs):
        if ins.kind in ("jump", "cond_jump"):
            if ins.label not in label_positions:
                raise ValueError(
                    f"undefined label target: {ins.label!r}"
                )

            leaders.add(label_positions[ins.label])

            if i + 1 < len(instrs):
                leaders.add(i + 1)

        elif ins.kind == "return" and i + 1 < len(instrs):
            leaders.add(i + 1)

    ordered = sorted(leaders)
    blocks = []

    for idx, start in enumerate(ordered):
        end = (
            ordered[idx + 1]
            if idx + 1 < len(ordered)
            else len(instrs)
        )

        chunk = instrs[start:end]

        name = (
            chunk[0].label
            if chunk[0].kind == "label"
            else f"B{start}"
        )

        block = Block(name)
        block.instrs = chunk
        blocks.append(block)

    return blocks


def build_cfg(instrs):
    blocks = build_basic_blocks(instrs)
    cfg = CFG()
    cfg.blocks = blocks

    for block in blocks:
        cfg.succs[block] = []
        cfg.preds[block] = []

        if block.instrs and block.instrs[0].kind == "label":
            label = block.instrs[0].label

            if label in cfg.label_to_block:
                raise ValueError(f"duplicate label: {label!r}")

            cfg.label_to_block[label] = block

    def block_of(label):
        if label not in cfg.label_to_block:
            raise ValueError(f"undefined label target: {label!r}")

        return cfg.label_to_block[label]

    for idx, block in enumerate(blocks):
        last = block.instrs[-1] if block.instrs else None
        nxt = blocks[idx + 1] if idx + 1 < len(blocks) else None

        if last is None:
            if nxt is not None:
                cfg.succs[block].append(nxt)

        elif last.kind == "jump":
            cfg.succs[block].append(block_of(last.label))

        elif last.kind == "cond_jump":
            cfg.succs[block].append(block_of(last.label))

            if nxt is not None:
                cfg.succs[block].append(nxt)

        elif last.kind == "return":
            pass

        else:
            if nxt is not None:
                cfg.succs[block].append(nxt)

    for block in blocks:
        for successor in cfg.succs[block]:
            cfg.preds[successor].append(block)

    cfg.entry = blocks[0] if blocks else None
    cfg.exits = [
        block for block in blocks
        if not cfg.succs[block]
    ]

    return cfg
