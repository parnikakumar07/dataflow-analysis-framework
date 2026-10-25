
"""
IR / TAC Parser
---------------
Reads a small, explicit three-address-code (TAC) text format and produces
a flat list of Instr objects. This is intentionally minimal (no types, no
function calls, no arrays) so the CFG builder and analyses stay simple
and verifiable by hand.

Supported syntax (one instruction per line, '#' starts a comment):

    L1:                     label
    x = 5                   constant assignment
    x = y                   copy assignment
    x = y + z               binary-op assignment (+ - * / %)
    x = -y                  unary negation of a variable
    if x < y goto L2        conditional jump (== != < <= > >=)
    goto L3                 unconditional jump
    return x                return (x optional)
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import re

BIN_OPS = {"+", "-", "*", "/", "%"}
REL_OPS = {"==", "!=", "<", "<=", ">", ">="}

_COND_RE = re.compile(
    r"^if\s+(\S+)\s*(==|!=|<=|>=|<|>)\s*(\S+)\s+goto\s+(\S+)$"
)
_BINOP_RE = re.compile(r"^(\S+)\s*([+\-*/%])\s*(\S+)$")
_ASSIGN_RE = re.compile(r"^(\S+)\s*=\s*(.+)$")
_UNARY_NEG_RE = re.compile(r"^-(\S+)$")


class ParseError(ValueError):
    pass


def is_valid_operand(token: Optional[str]) -> bool:
    if token is None:
        return False
    return bool(re.fullmatch(r"[A-Za-z_]\w*|-?\d+", token))


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
    kind: str
    dst: Optional[str] = None
    op: Optional[str] = None
    src1: Optional[str] = None
    src2: Optional[str] = None
    label: Optional[str] = None
    cond: Optional[Tuple[str, str, str]] = None
    text: str = ""
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

    # Label
    if raw.endswith(":"):
        name = raw[:-1].strip()
        if not re.fullmatch(r"[A-Za-z_]\w*", name):
            raise ParseError(f"line {lineno}: invalid label: {name!r}")
        return Instr(kind="label", label=name, text=raw, lineno=lineno)

    # Conditional jump
    if raw.startswith("if "):
        m = _COND_RE.match(raw)
        if not m:
            raise ParseError(
                f"line {lineno}: malformed conditional jump: {raw!r}"
            )
        left, relop, right, target = m.groups()
        if relop not in REL_OPS:
            raise ParseError(
                f"line {lineno}: unknown relational operator {relop!r}"
            )
        if not is_valid_operand(left) or not is_valid_operand(right):
            raise ParseError(
                f"line {lineno}: invalid conditional operands: {raw!r}"
            )
        if not re.fullmatch(r"[A-Za-z_]\w*", target):
            raise ParseError(
                f"line {lineno}: invalid jump target: {target!r}"
            )
        return Instr(
            kind="cond_jump",
            cond=(left, relop, right),
            label=target,
            text=raw,
            lineno=lineno,
        )

    # Unconditional jump
    if raw.startswith("goto "):
        target = raw.split(None, 1)[1].strip()
        if not re.fullmatch(r"[A-Za-z_]\w*", target):
            raise ParseError(
                f"line {lineno}: invalid jump target: {target!r}"
            )
        return Instr(kind="jump", label=target, text=raw, lineno=lineno)

    # Return
    if raw == "return" or raw.startswith("return "):
        parts = raw.split(None, 1)
        dst = parts[1].strip() if len(parts) > 1 else None
        if dst is not None and not is_valid_operand(dst):
            raise ParseError(f"line {lineno}: invalid return operand: {dst!r}")
        return Instr(kind="return", dst=dst, text=raw, lineno=lineno)

    # Assignment
    m = _ASSIGN_RE.match(raw)
    if not m:
        raise ParseError(f"line {lineno}: cannot parse instruction: {raw!r}")

    dst, rhs = m.groups()
    rhs = rhs.strip()

    if not re.fullmatch(r"[A-Za-z_]\w*", dst):
        raise ParseError(f"line {lineno}: invalid assignment target: {dst!r}")

    # Binary operation
    m2 = _BINOP_RE.fullmatch(rhs)
    if m2:
        src1, op, src2 = m2.groups()
        if not is_valid_operand(src1) or not is_valid_operand(src2):
            raise ParseError(
                f"line {lineno}: invalid binary operands: {rhs!r}"
            )
        return Instr(
            kind="assign",
            dst=dst,
            op=op,
            src1=src1,
            src2=src2,
            text=raw,
            lineno=lineno,
        )

    # Constant assignment, including negative integer constants
    if is_const(rhs):
        return Instr(
            kind="assign",
            dst=dst,
            op="const",
            src1=rhs,
            src2=None,
            text=raw,
            lineno=lineno,
        )

    # Unary negation: x = -y becomes x = 0 - y
    m3 = _UNARY_NEG_RE.fullmatch(rhs)
    if m3:
        operand = m3.group(1)
        if not re.fullmatch(r"[A-Za-z_]\w*", operand):
            raise ParseError(
                f"line {lineno}: invalid unary negation operand: {operand!r}"
            )
        return Instr(
            kind="assign",
            dst=dst,
            op="-",
            src1="0",
            src2=operand,
            text=raw,
            lineno=lineno,
        )

    # Copy assignment
    if is_valid_operand(rhs) and not is_const(rhs):
        return Instr(
            kind="assign",
            dst=dst,
            op="copy",
            src1=rhs,
            src2=None,
            text=raw,
            lineno=lineno,
        )

    raise ParseError(f"line {lineno}: cannot parse right-hand side: {rhs!r}")


def parse_program(source: str):
    instrs = []
    for i, line in enumerate(source.splitlines(), start=1):
        ins = parse_line(line, i)
        if ins is not None:
            instrs.append(ins)
    return instrs
