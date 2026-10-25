# Generic Data-Flow Analysis Framework

**BCSE307 Compiler Design — Project A34 — Team 9**

A reusable, monotone data-flow analysis framework built over a Control-Flow Graph (CFG). The project combines a generic worklist solver, four pluggable data-flow analyses, a command-line interface, and a Streamlit dashboard for interactive analysis and CFG visualization.

Provide a supported Three-Address Code (TAC) program, select an analysis, and inspect the resulting IN/OUT sets for each basic block. You can use the framework directly from the terminal or through the graphical dashboard.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Dashboard](#running-the-dashboard)
- [Command-Line Usage](#command-line-usage)
- [Supported Analyses](#supported-analyses)
- [Example Walkthrough](#example-walkthrough)
- [Writing Your Own TAC Programs](#writing-your-own-tac-programs)
- [Testing](#testing)
- [Architecture](#architecture)
- [Extending the Framework](#extending-the-framework)

---

## Features

- **Generic worklist solver:** A reusable fixpoint engine that supports forward and backward data-flow analyses.
- **Four classical analyses:** Reaching Definitions, Available Expressions, Live Variables, and Constant Propagation.
- **Interactive Streamlit dashboard:** A graphical interface for selecting analyses, running the framework, and inspecting results.
- **Control-flow graph visualization:** Generate and view CFGs using Graphviz.
- **CFG export:** Export the control-flow graph in DOT format and download the generated graph image through the dashboard.
- **Command-line interface:** Run analyses on TAC files, provide input through standard input, or enter programs interactively.
- **Input validation:** Detect malformed instructions, invalid or duplicate labels, and undefined jump targets.
- **Modular architecture:** Keep parsing, CFG construction, solving, analysis logic, and visualization in separate modules.
- **Minimal core dependencies:** The analysis framework uses Python's standard library. Streamlit and Graphviz are additional requirements for the visual interface and graph rendering.

## Project Structure

```text
dataflow-analysis-framework/
├── app.py                  # Streamlit dashboard
├── dataflow/
│   ├── ir.py               # Intermediate representation and TAC parser
│   ├── cfg.py              # Basic-block and CFG construction
│   ├── solver.py           # Generic worklist fixpoint solver
│   ├── analyses.py         # Four data-flow analyses
│   ├── visualizer.py       # Analysis output and DOT generation
│   └── cli.py              # Command-line interface
├── examples/
│   ├── sequential.tac      # Straight-line program
│   ├── branching.tac       # Conditional branches
│   └── looping.tac         # Loop and back-edge
├── tests/
│   ├── test_ir.py
│   ├── test_cfg.py
│   ├── test_solver.py
│   ├── test_analyses.py
│   ├── test_integration.py
│   └── test_extended_coverage.py
└── README.md
```

The exact test filenames may vary with the current repository version. The `app.py` dashboard uses the framework's CLI to run analyses and generate graph output.

## Requirements

- Python 3.10 or a compatible version supported by your installed packages.
- Git, for cloning the repository.
- Streamlit, for the graphical dashboard.
- Graphviz, for rendering CFGs into images.
- pytest, for running the test suite.

The core CLI framework uses the Python standard library. Streamlit and Graphviz are needed for the graphical workflow.

## Installation

Clone the repository and enter the project directory:

```bash
git clone https://github.com/parnikakumar07/dataflow-analysis-framework.git
cd dataflow-analysis-framework
```

### 1. Create a virtual environment (recommended)

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If activation is blocked by your PowerShell execution policy, you can use the virtual environment's Python executable directly instead.

### 2. Install Python packages

```bash
python -m pip install streamlit graphviz pytest
```

The Python `graphviz` package provides the interface to Graphviz; it does not install the Graphviz system executable.

### 3. Install Graphviz

Install Graphviz separately using the official download page:

https://graphviz.org/download/

On Windows, ensure the Graphviz `bin` directory is available on your system PATH. Restart your terminal after changing PATH.

Verify the installation:

```bash
dot -V
```

If the command prints a Graphviz version, the executable is available to your terminal.

## Running the Dashboard

From the repository root, run:

```bash
streamlit run app.py
```

Streamlit will start a local development server and provide a URL, typically:

```text
http://localhost:8501
```

Open that address in your browser.

### Dashboard workflow

1. Launch the Streamlit application.
2. Select an available TAC example or provide supported TAC input, according to the options exposed by the dashboard.
3. Choose one of the four analyses or the option to run all analyses.
4. Run the analysis.
5. Inspect the analysis output and the generated control-flow graph.
6. Download the CFG image if needed.

The dashboard relies on the repository's CLI and Graphviz installation. If graph rendering fails, verify that `dot -V` works and that the application is being launched from the repository environment.

## Command-Line Usage

The framework can also be used without opening the dashboard.

Run all four analyses:

```bash
python -m dataflow.cli examples/branching.tac
```

Run one analysis:

```bash
python -m dataflow.cli examples/looping.tac --analysis live
```

Export the CFG as a DOT file:

```bash
python -m dataflow.cli examples/branching.tac --dot cfg.dot
```

Read a program from standard input:

```bash
python -m dataflow.cli --stdin < examples/sequential.tac
```

Enter a program interactively:

```bash
python -m dataflow.cli
```

When using interactive input, follow the CLI's instructions for terminating input.

### CLI options

| Option | Description |
|---|---|
| `tacfile` | Path to a TAC source file. |
| `--stdin` | Read TAC from standard input. |
| `--analysis` | Select the analysis to execute. |
| `--dot PATH` | Write the control-flow graph to a DOT file. |

Supported analysis flags are `reaching`, `available`, `live`, `constprop`, and `all`. The default analysis selection is `all`.

## Supported Analyses

| Analysis | CLI flag | Direction | Meet operator | Purpose |
|---|---|---|---|---|
| Reaching Definitions | `reaching` | Forward | Union (may) | Determines which variable definitions can reach a program point. |
| Available Expressions | `available` | Forward | Intersection (must) | Identifies expressions already computed and still valid at a program point. |
| Live Variables | `live` | Backward | Union (may) | Determines which variables may be used in the future before being redefined. |
| Constant Propagation | `constprop` | Forward | Constant-propagation meet | Tracks variables that can be represented by known constant values. |

## Example Walkthrough

Consider the following straight-line program:

```text
x = 1
y = 2
z = x + y
w = z
return w
```

Save it as a `.tac` file or use the supplied `examples/sequential.tac` example.

Run Constant Propagation:

```bash
python -m dataflow.cli examples/sequential.tac --analysis constprop
```

The analysis tracks the known constant values as assignments are processed. For this program, the expected final values include `x = 1`, `y = 2`, `z = 3`, and `w = 3`, assuming the implementation's constant propagation transfer functions evaluate these expressions as expected.

### Branching example

```text
x = 1
y = 2
if x < y goto L_true
z = 99
goto L_end
L_true:
z = x + y
L_end:
w = z
return w
```

Run Reaching Definitions:

```bash
python -m dataflow.cli examples/branching.tac --analysis reaching
```

At the merge point, both branch-specific definitions of `z` may reach the block. This illustrates why Reaching Definitions uses a union-based meet operator.

## Writing Your Own TAC Programs

The parser supports the following instruction forms, as documented by the project:

```text
L1:                     label
x = 5                   constant assignment
x = y                   copy assignment
x = y + z               binary operation
x = -y                  unary negation
if x < y goto L2        conditional jump
goto L3                 unconditional jump
return x                return statement
# comment
```

Supported binary operators include `+`, `-`, `*`, `/`, and `%`. Conditional comparisons include `==`, `!=`, `<`, `<=`, `>`, and `>=`.

Labels must be valid and unique, and every jump target must refer to a defined label. Use the supplied examples as templates when creating new programs.

## Testing

Install pytest if it is not already installed:

```bash
python -m pip install pytest
```

Run the complete test suite from the repository root:

```bash
python -m pytest -q
```

The tests cover the parser, CFG construction, solver behavior, individual data-flow analyses, and CLI integration. The exact number of tests and their results depend on the current repository version; use the output from your latest local test run when reporting the verified count.

## Architecture

The framework separates the analysis pipeline into independent components.

| Component | Responsibility |
|---|---|
| TAC parser (`ir.py`) | Parses source instructions into an intermediate representation. |
| Basic-block builder (`cfg.py`) | Identifies leaders and groups instructions into basic blocks. |
| CFG builder (`cfg.py`) | Constructs control-flow edges between blocks. |
| Generic solver (`solver.py`) | Iteratively applies data-flow equations until a fixpoint is reached. |
| Analysis modules (`analyses.py`) | Implement each analysis's direction, lattice operations, and transfer functions. |
| Result visualizer (`visualizer.py`) | Formats analysis results and exports CFGs in DOT format. |
| CLI (`cli.py`) | Exposes analysis execution and input/output options. |
| Dashboard (`app.py`) | Provides a browser-based interface to run analyses and inspect their output. |

The separation between the generic solver and the individual analysis implementations makes the framework extensible: the solver does not need to be rewritten for every new analysis.

## Extending the Framework

To add a new data-flow analysis:

1. Implement a new analysis class using the framework's `DataFlowAnalysis` interface in `analyses.py`.
2. Define the analysis direction.
3. Implement its boundary value, top value, meet operation, and transfer function as required by the existing interface.
4. Register the analysis in the CLI's analysis mapping.
5. Add suitable unit and integration tests.
6. Run the full test suite to check that existing behavior remains correct.

The generic solver should remain independent of analysis-specific transfer functions and lattice operations. This is the central design principle of the framework.

---

## License and Contributions

This repository was developed as part of **BCSE307 Compiler Design — Project A34 — Team 9**.

For contributions, create a feature branch, implement and test the change, and submit a pull request against `main`.

