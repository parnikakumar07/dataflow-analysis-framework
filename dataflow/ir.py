"""
IR / TAC Parser
---------------
Reads a small, explicit three-address-code (TAC) text format and produces
a flat list of Instr objects. This is intentionally minimal (no types, no
function calls, no arrays) so the CFG builder and analyses stay simple and
verifiable by hand -- exactly the "controlled IR/TAC subset" scope from the
Review 1 feasibility slide.

Supported syntax (one instruction per line, '#' starts a comment):

    L1:                     label
    x = 5                   constant assignment
    x = y                   copy assignment
    x = y + z               binary-op assignment (+ - * / %)
    if x < y goto L2        conditional jump (== != < <= > >=)
    goto L3                 unconditional jump
    return x                return (x optional)
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple
import re

BIN_OPS = {"+", "-", "*", "/", "%"}
REL_OPS = {"==", "!=", "<", "<=", ">", ">="}

_COND_RE = re.compile(
    r"^if\s+(\S+)\s*(==|!=|<=|>=|<|>)\s*(\S+)\s+goto\s+(\S+)$"
)
_BINOP_RE = re.compile(r"^(\S+)\s*([+\-*/%])\s*(\S+)$")
_ASSIGN_RE = re.compile(r"^(\S+)\s*=\s*(.+)$")


class ParseError(ValueError):
    pass


def is_const(token: Optional[str]) -> bool:
    if token is None:
        return False
    try:
        int(token)
        return True
    except ValueError:
        return False


@dataclass
class Instr:
    kind: str                              # label | assign | cond_jump | jump | return
    dst: Optional[str] = None
    op: Optional[str] = None               # 'const' | 'copy' | one of BIN_OPS
    src1: Optional[str] = None
    src2: Optional[str] = None
    label: Optional[str] = None            # label name (for 'label') or jump target
    cond: Optional[Tuple[str, str, str]] = None  # (left, relop, right) for cond_jump
    text: str = ""                         # original source line, kept for printing
    lineno: int = 0

    def defs(self):
        if self.kind == "assign":
            return {self.dst}
        return set()

    def uses(self):
        u = set()
        if self.kind == "assign":
            for v in (self.src1, self.src2):
                if v is not None and not is_const(v):
                    u.add(v)
        elif self.kind == "cond_jump":
            left, _, right = self.cond
            if not is_const(left):
                u.add(left)
            if not is_const(right):
                u.add(right)
        elif self.kind == "return" and self.dst is not None:
            if not is_const(self.dst):
                u.add(self.dst)
        return u

    def __repr__(self):
        return f"<{self.kind}: {self.text}>"


def parse_line(line: str, lineno: int) -> Optional[Instr]:
    raw = line.split("#", 1)[0].strip()
    if not raw:
        return None

    if raw.endswith(":"):
        return Instr(kind="label", label=raw[:-1].strip(), text=raw, lineno=lineno)

    if raw.startswith("if "):
        m = _COND_RE.match(raw)
        if not m:
            raise ParseError(f"line {lineno}: malformed conditional jump: {raw!r}")
        left, relop, right, target = m.groups()
        if relop not in REL_OPS:
            raise ParseError(f"line {lineno}: unknown relational operator {relop!r}")
        return Instr(kind="cond_jump", cond=(left, relop, right), label=target,
                     text=raw, lineno=lineno)

    if raw.startswith("goto "):
        target = raw.split(None, 1)[1].strip()
        return Instr(kind="jump", label=target, text=raw, lineno=lineno)

    if raw == "return" or raw.startswith("return "):
        parts = raw.split(None, 1)
        dst = parts[1].strip() if len(parts) > 1 else None
        return Instr(kind="return", dst=dst, text=raw, lineno=lineno)

    m = _ASSIGN_RE.match(raw)
    if not m:
        raise ParseError(f"line {lineno}: cannot parse instruction: {raw!r}")
    dst, rhs = m.groups()
    rhs = rhs.strip()

    m2 = _BINOP_RE.match(rhs)
    if m2:
        src1, op, src2 = m2.groups()
        if op not in BIN_OPS:
            raise ParseError(f"line {lineno}: unknown operator {op!r}")
        return Instr(kind="assign", dst=dst, op=op, src1=src1, src2=src2,
                     text=raw, lineno=lineno)

    if is_const(rhs):
        return Instr(kind="assign", dst=dst, op="const", src1=rhs, src2=None,
                     text=raw, lineno=lineno)

    if re.match(r"^\S+$", rhs):
        return Instr(kind="assign", dst=dst, op="copy", src1=rhs, src2=None,
                     text=raw, lineno=lineno)

    raise ParseError(f"line {lineno}: cannot parse right-hand side: {rhs!r}")


def parse_program(source: str):
    instrs = []
    for i, line in enumerate(source.splitlines(), start=1):
        ins = parse_line(line, i)
        if ins is not None:
            instrs.append(ins)
    return instrs
