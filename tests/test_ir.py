import unittest
from dataflow import ir


class TestParser(unittest.TestCase):
    def test_label(self):
        i = ir.parse_line("L1:", 1)
        self.assertEqual(i.kind, "label")
        self.assertEqual(i.label, "L1")

    def test_const_assign(self):
        i = ir.parse_line("x = 5", 1)
        self.assertEqual((i.kind, i.op, i.dst, i.src1), ("assign", "const", "x", "5"))

    def test_copy_assign(self):
        i = ir.parse_line("x = y", 1)
        self.assertEqual((i.kind, i.op, i.dst, i.src1), ("assign", "copy", "x", "y"))

    def test_binop_assign(self):
        i = ir.parse_line("z = x + y", 1)
        self.assertEqual((i.kind, i.op, i.src1, i.src2), ("assign", "+", "x", "y"))
        self.assertEqual(i.uses(), {"x", "y"})
        self.assertEqual(i.defs(), {"z"})

    def test_negative_constant_not_mistaken_for_binop(self):
        i = ir.parse_line("x = -5", 1)
        self.assertEqual((i.kind, i.op, i.src1), ("assign", "const", "-5"))

    def test_cond_jump(self):
        i = ir.parse_line("if x < y goto L2", 1)
        self.assertEqual(i.kind, "cond_jump")
        self.assertEqual(i.cond, ("x", "<", "y"))
        self.assertEqual(i.label, "L2")
        self.assertEqual(i.uses(), {"x", "y"})

    def test_jump(self):
        i = ir.parse_line("goto L3", 1)
        self.assertEqual((i.kind, i.label), ("jump", "L3"))

    def test_return_with_and_without_var(self):
        self.assertEqual(ir.parse_line("return x", 1).dst, "x")
        self.assertIsNone(ir.parse_line("return", 1).dst)

    def test_comments_and_blank_lines_ignored(self):
        prog = "x = 1\n# a comment\n\ny = 2 # trailing comment\n"
        instrs = ir.parse_program(prog)
        self.assertEqual(len(instrs), 2)

    def test_bad_line_raises(self):
        with self.assertRaises(ir.ParseError):
            ir.parse_line("this is not valid tac !!", 1)


if __name__ == "__main__":
    unittest.main()
