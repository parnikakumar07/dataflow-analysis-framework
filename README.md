# Generic Data-Flow Analysis Framework

A Python-based framework for performing classical data-flow analyses on Three-Address Code (TAC), developed as part of the BCSE307 Compiler Design project.

The project provides a reusable data-flow analysis engine, a command-line interface (CLI), and a Streamlit dashboard for running analyses and visualizing Control Flow Graphs (CFGs).

## Features

- **Generic data-flow solver:** Supports forward and backward analyses using a worklist algorithm.
- **Reaching Definitions:** Determines which variable definitions may reach each program point.
- **Available Expressions:** Identifies expressions that are available at each program point.
- **Live Variables:** Determines which variables may be used in the future before being reassigned.
- **Constant Propagation:** Tracks constant values through a program.
- **Streamlit dashboard:** Provides a graphical interface for selecting TAC examples and viewing analysis results.
- **Control Flow Graph visualization:** Supports CFG generation and visualization using Graphviz.
- **Command-line interface:** Run individual analyses or all supported analyses from the terminal.
- **Input validation:** Handles invalid TAC instructions through parser validation and error reporting.
- **Automated tests:** Includes unit and integration tests for verifying framework behavior.

## Project Structure

```text
dataflow-analysis-framework/
├── app.py
├── dataflow/
│   ├── ir.py
│   ├── cfg.py
│   ├── solver.py
│   ├── analyses.py
│   ├── visualizer.py
│   └── cli.py
├── examples/
│   ├── sequential.tac
│   ├── branching.tac
│   └── looping.tac
├── tests/
│   ├── test_ir.py
│   ├── test_cfg.py
│   ├── test_solver.py
│   ├── test_analyses.py
│   ├── test_integration.py
│   └── test_extended_coverage.py
├── README.md
└── WORKDONE.md
```

*This tree highlights the main project components. The exact file list may vary as the repository evolves.*

## Requirements

- Python 3
- Git
- Streamlit
- Graphviz
- pytest for running the test suite

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/parnikakumar07/dataflow-analysis-framework.git
cd dataflow-analysis-framework
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
python -m pip install streamlit graphviz pytest
```

If the repository includes a `requirements.txt` file, you can install its listed dependencies instead:

```bash
python -m pip install -r requirements.txt
```

### 4. Install Graphviz

The Python `graphviz` package provides an interface to Graphviz, but rendering CFG images also requires the Graphviz system application and its `dot` executable.

Download Graphviz from:

https://graphviz.org/download/

After installation, verify that it is available:

```bash
dot -V
```

If the command is not recognized, add Graphviz's `bin` directory to your system `PATH` and reopen your terminal.

## Running the Streamlit Dashboard

From the project root, execute:

```bash
streamlit run app.py
```

Streamlit will display a local URL, typically:

```text
http://localhost:8501
```

Open the URL in your browser to access the dashboard.

### Dashboard Workflow

1. Launch the Streamlit application.
2. Select a TAC example from the available options.
3. Choose the data-flow analysis to perform.
4. Run the analysis and inspect the results.
5. View the Control Flow Graph when available.
6. Download the generated CFG image if the corresponding option is available.

The dashboard provides a graphical way to explore the framework without relying exclusively on terminal commands.

## Running the CLI

Run CLI commands from the project root.

### Run all analyses

```bash
python -m dataflow.cli examples/branching.tac
```

### Run Live Variables Analysis

```bash
python -m dataflow.cli examples/looping.tac --analysis live
```

### Generate a CFG DOT file

```bash
python -m dataflow.cli examples/branching.tac --dot cfg.dot
```

### Read TAC from standard input

```bash
python -m dataflow.cli --stdin < examples/sequential.tac
```

### Start interactive mode

```bash
python -m dataflow.cli
```

### CLI Options

| Option | Description |
|---|---|
| `tacfile` | Path to the TAC input file |
| `--stdin` | Read TAC input from standard input |
| `--analysis` | Select the analysis to execute |
| `--dot PATH` | Write the Control Flow Graph in DOT format |

To check the analysis names and options accepted by the current CLI, run:

```bash
python -m dataflow.cli --help
```

### Render a DOT file as a PNG image

If Graphviz is installed, convert the generated DOT file into an image:

```bash
dot -Tpng cfg.dot -o cfg.png
```

## Supported Data-Flow Analyses

### 1. Reaching Definitions

- **Direction:** Forward
- **Meet operator:** Union
- **Purpose:** Determines which variable definitions may reach a program point without being overwritten along the way.

### 2. Available Expressions

- **Direction:** Forward
- **Meet operator:** Intersection
- **Purpose:** Identifies expressions that have already been computed and whose operands have not changed along the relevant paths.

### 3. Live Variables

- **Direction:** Backward
- **Meet operator:** Union
- **Purpose:** Determines whether a variable's current value may be used later before another assignment replaces it.

### 4. Constant Propagation

- **Direction:** Forward
- **Purpose:** Tracks constant values assigned to variables and propagates known constants through the program where possible.

## Three-Address Code (TAC)

The framework operates on a simplified Three-Address Code representation.

### Example

```text
x = 5
y = 10
z = x + y
if z > 10 goto L1
z = 0
L1:
return z
```

### Common Instruction Forms

| Instruction | Example | Purpose |
|---|---|---|
| Assignment | `x = 5` | Assign a constant |
| Copy | `x = y` | Copy a variable value |
| Binary operation | `x = y + z` | Compute an expression |
| Unary negation | `x = -y` | Apply unary negation |
| Conditional jump | `if x < y goto L1` | Branch based on a condition |
| Unconditional jump | `goto L1` | Transfer control to a label |
| Return | `return x` | Return a value |
| Comment | `# comment` | Document the TAC program |

The parser defines the exact supported operators and syntax. The example TAC files in the repository can be used as references for valid input.

## Running Tests

Install pytest if it is not already available:

```bash
python -m pip install pytest
```

Run the complete test suite from the project root:

```bash
python -m pytest -q
```

To run a specific test file:

```bash
python -m pytest tests/test_solver.py -v
```

The test suite covers areas including intermediate-representation parsing, CFG construction, solver behavior, data-flow analyses, and integration functionality.

**Previously reported test result: 256 tests passed.**

This result reflects an earlier reported test run, not a newly verified run of the current repository. Test counts can change as the project evolves; rerun the complete suite to confirm the latest result.

## Architecture

| Component | Responsibility |
|---|---|
| `ir.py` | Represents and processes intermediate-representation instructions |
| `cfg.py` | Constructs the Control Flow Graph |
| `solver.py` | Executes the generic data-flow solving algorithm |
| `analyses.py` | Implements the supported data-flow analyses |
| `visualizer.py` | Supports CFG visualization and DOT output |
| `cli.py` | Provides command-line execution |
| `app.py` | Provides the Streamlit dashboard |
| `tests/` | Contains automated tests |

## Extending the Framework

The framework is designed to make it easier to introduce additional data-flow analyses.

A new analysis generally needs to define:

1. **Direction:** Forward or backward.
2. **Boundary value:** The initial information at the relevant program boundary.
3. **Top or initial value:** The starting value used by the solver.
4. **Meet operator:** How information from predecessor or successor blocks is combined.
5. **Transfer function:** How the analysis state changes when processing an instruction or basic block.

Implement the new analysis using the abstractions already defined in `dataflow/analyses.py`, then register it with the CLI if required. Follow the existing classes and method signatures in the repository.

## Limitations

- The framework supports its implemented TAC representation rather than arbitrary source code.
- Analysis results depend on the implemented transfer functions and lattice definitions.
- CFG image rendering requires a working Graphviz installation.
- The dashboard and CLI require the appropriate Python dependencies.
- Supported analysis options and input syntax are determined by the current implementation.

## Contributing

Contributions and improvements are welcome.

Before submitting changes:

1. Run the existing test suite.
2. Add tests for new features and bug fixes.
3. Update documentation when behavior or commands change.
4. Ensure examples match the TAC syntax supported by the parser.

## Academic Context

- **Course:** BCSE307 – Compiler Design
- **Project:** Generic Data-Flow Analysis Framework
- **Team:** Team 9
- **Project ID:** A34

This project demonstrates classical data-flow analysis, reusable solving algorithms, Control Flow Graph construction, and analysis visualization through a command-line interface and a Streamlit dashboard.
