import unittest
from dataflow import ir, cfg as cfg_mod


def build(src):
    return cfg_mod.build_cfg(ir.parse_program(src))


class TestCFG(unittest.TestCase):
    def test_sequential_is_one_block(self):
        with open("examples/sequential.tac") as f:
            g = build(f.read())
        self.assertEqual(len(g.blocks), 1)
        self.assertEqual(g.exits, g.blocks)  # the only block ends in return

    def test_branching_creates_four_blocks_and_merges(self):
        with open("examples/branching.tac") as f:
            g = build(f.read())
        self.assertEqual(len(g.blocks), 4)
        names = [b.name for b in g.blocks]
        self.assertIn("L_true", names)
        self.assertIn("L_end", names)

        entry = g.entry
        self.assertEqual(len(g.succs[entry]), 2)  # cond_jump has two successors

        l_end = next(b for b in g.blocks if b.name == "L_end")
        self.assertEqual(len(g.preds[l_end]), 2)  # both branches merge here

    def test_looping_creates_back_edge(self):
        with open("examples/looping.tac") as f:
            g = build(f.read())
        l_head = next(b for b in g.blocks if b.name == "L_head")
        l_body = next(b for b in g.blocks if b.name == "L_body")
        self.assertIn(l_head, g.succs[l_body])  # L_body's goto L_head is a back-edge
        self.assertIn(l_body, g.preds[l_head])

    def test_undefined_label_raises(self):
        with self.assertRaises(ValueError):
            build("goto L_missing\n")

    def test_multiple_returns_produce_multiple_exit_blocks(self):
        # Two separate return statements on either side of a branch -- the
        # CFG must record both as exits, not just the last one.
        g = build("if x < y goto L1\nreturn x\nL1:\nreturn y\n")
        self.assertEqual(len(g.exits), 2)
        exit_names = {b.name for b in g.exits}
        self.assertEqual(exit_names, {"B1", "L1"})
        for b in g.exits:
            self.assertEqual(g.succs[b], [])

    def test_unreachable_block_has_no_predecessors_but_still_has_a_successor(self):
        # Code placed right after an unconditional goto, with no label
        # pointing back to it, is unreachable from entry -- but the leader
        # algorithm still carves it into its own block with a normal
        # fall-through edge to whatever follows it.
        g = build("goto L1\nx = 1\nL1:\ny = 2\nreturn y\n")
        unreachable = next(b for b in g.blocks if b.name == "B1")
        self.assertEqual(g.preds[unreachable], [])
        self.assertEqual(len(g.succs[unreachable]), 1)
        self.assertNotIn(unreachable, g.exits)
        self.assertNotIn(unreachable, [p for p in g.preds[g.entry]])

    def test_duplicate_labels_raise(self):
        with self.assertRaises(ValueError):
            build("L1:\nx = 1\nL1:\nreturn x\n")

if __name__ == "__main__":
    unittest.main()
