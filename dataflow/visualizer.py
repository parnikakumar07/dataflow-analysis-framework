"""
Result / Visualizer
--------------------
Turns IN/OUT maps into a readable report, and can emit the CFG as a
Graphviz .dot file (rendered with `dot -Tpng` if Graphviz is installed
locally -- no Python dependency required either way).
"""


def print_results(cfg, title, IN, OUT, analysis, steps=None):
    print(f"\n=== {title} ({analysis.direction}) ===")
    for b in cfg.blocks:
        print(f"[{b.name}]")
        for ins in b.instrs:
            print(f"    {ins.text}")
        print(f"    IN  = {analysis.format_value(IN[b])}")
        print(f"    OUT = {analysis.format_value(OUT[b])}")
    if steps is not None:
        print(f"  (converged in {steps} worklist steps, {len(cfg.blocks)} blocks)")


def cfg_to_dot(cfg):
    lines = ["digraph CFG {", '  node [shape=box, fontname="Courier", fontsize=10];']
    for b in cfg.blocks:
        has_own_label = bool(b.instrs) and b.instrs[0].kind == "label"
        header = [] if has_own_label else [b.name + ":"]
        body_lines = header + [ins.text for ins in b.instrs]
        label = "\\l".join(line.replace('"', '\\"') for line in body_lines) + "\\l"
        lines.append(f'  "{b.name}" [label="{label}"];')
    for b in cfg.blocks:
        for s in cfg.succs.get(b, []):
            lines.append(f'  "{b.name}" -> "{s.name}";')
    lines.append("}")
    return "\n".join(lines)
