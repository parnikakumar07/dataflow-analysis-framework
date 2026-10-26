"""
Project A34 — Generic Data-Flow Analysis Framework
Academic Streamlit Dashboard

Run:
    python -m pip install streamlit
    python -m streamlit run app.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
EXAMPLES_DIR = ROOT / "examples"

ANALYSES = {
    "All four analyses": None,
    "Reaching Definitions": "reaching",
    "Available Expressions": "available",
    "Live Variables": "live",
    "Constant Propagation": "constprop",
}

# Fallback examples are used only if no .tac files exist in examples/.
FALLBACK_EXAMPLES = {
    "Sequential example": (
        "x = 1\n"
        "y = 2\n"
        "z = x + y\n"
        "return z\n"
    ),
    "Branching example": (
        "x = 1\n"
        "if x < 2 goto L_true\n"
        "y = 10\n"
        "goto L_end\n"
        "L_true:\n"
        "y = 20\n"
        "L_end:\n"
        "z = x + y\n"
        "return z\n"
    ),
    "Looping example": (
        "k = 7\n"
        "i = 0\n"
        "L:\n"
        "if i < 3 goto L_body\n"
        "return k\n"
        "L_body:\n"
        "i = i + 1\n"
        "goto L\n"
    ),
}


def discover_examples():
    """Load the repository's real TAC examples where available."""
    examples = {}

    if EXAMPLES_DIR.is_dir():
        for path in sorted(EXAMPLES_DIR.glob("*.tac")):
            label = path.stem.replace("_", " ").replace("-", " ").title()
            examples[f"{label} example"] = path.read_text(encoding="utf-8")

    return examples or FALLBACK_EXAMPLES


def run_framework(source, analysis_alias):
    """
    Execute the existing project CLI and render its actual CFG using Graphviz.
    The framework's parser, solver and analyses are not reimplemented here.
    """
    with tempfile.TemporaryDirectory(prefix="dataflow_ui_") as tmp:
        temp_dir = Path(tmp)
        tac_path = temp_dir / "input.tac"
        dot_path = temp_dir / "cfg.dot"
        png_path = temp_dir / "cfg.png"

        tac_path.write_text(source, encoding="utf-8")

        command = [
            sys.executable,
            "-m",
            "dataflow.cli",
            str(tac_path),
        ]

        if analysis_alias:
            command.extend(["--analysis", analysis_alias])

        command.extend(["--dot", str(dot_path)])

        try:
            result = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None, None, "The analysis timed out after 30 seconds."
        except OSError as exc:
            return None, None, f"Could not start the framework CLI: {exc}"

        output = result.stdout

        if result.returncode != 0:
            error = result.stderr.strip() or output.strip() or "The CLI failed."
            return None, output, error

        if not dot_path.exists():
            return (
                None,
                output,
                "The CLI did not create a DOT file. Check the --dot option "
                "supported by your repository's CLI.",
            )

        dot_executable = "dot.exe" if os.name == "nt" else "dot"

        try:
            rendered = subprocess.run(
                [
                    dot_executable,
                    "-Tpng",
                    str(dot_path),
                    "-o",
                    str(png_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except FileNotFoundError:
            return (
                None,
                output,
                "Graphviz was not found. Confirm that `dot -V` works, "
                "then restart the terminal and Streamlit.",
            )
        except subprocess.TimeoutExpired:
            return None, output, "Graphviz took too long to render the CFG."

        if rendered.returncode != 0 or not png_path.exists():
            return (
                None,
                output,
                rendered.stderr.strip() or "Could not render the CFG.",
            )

        return png_path.read_bytes(), output, None


# -------------------------------------------------------------------
# Page setup and visual theme
# -------------------------------------------------------------------

st.set_page_config(
    page_title="Project A34 | Data-Flow Analysis",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --navy: #14243a;
        --navy-light: #203b5b;
        --blue: #2b65a0;
        --blue-light: #eaf2fb;
        --ink: #192b40;
        --muted: #64758a;
        --line: #dbe4ee;
        --canvas: #edf2f7;
        --white: #ffffff;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background: var(--canvas);
        color: var(--ink);
    }

    [data-testid="stHeader"] {
        background: rgba(237, 242, 247, 0.95);
    }

    .block-container {
        max-width: 1550px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: var(--navy);
        border-right: 1px solid #2b415b;
    }

    [data-testid="stSidebar"] * {
        color: #edf4fc;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: #20354e;
        border-color: #405874;
    }

    [data-testid="stSidebar"] [data-testid="stButton"] button {
        background: var(--blue);
        color: white;
        border: 1px solid #4b7fb5;
        border-radius: 9px;
        font-weight: 650;
    }

    /* Hero */
    .hero {
        background: linear-gradient(120deg, #14243a 0%, #234c77 100%);
        border: 1px solid #2d5782;
        border-radius: 18px;
        padding: 2rem 2.1rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 28px rgba(20, 36, 58, 0.12);
    }

    .hero-eyebrow {
        color: #b8d4f0;
        text-transform: uppercase;
        letter-spacing: 0.17em;
        font-size: 0.72rem;
        font-weight: 750;
        margin-bottom: 0.7rem;
    }

    .hero h1 {
        color: white;
        font-size: clamp(1.8rem, 3vw, 2.55rem);
        line-height: 1.2;
        font-weight: 760;
        margin: 0;
    }

    .hero p {
        color: #d9e7f6;
        font-size: 1rem;
        line-height: 1.7;
        max-width: 900px;
        margin-top: 0.8rem;
        margin-bottom: 0;
    }

    /* Section headings */
    .eyebrow {
        color: #52708e;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        font-size: 0.72rem;
        font-weight: 750;
        margin-bottom: 0.3rem;
    }

    .section-title {
        color: #172b43;
        font-size: 1.3rem;
        font-weight: 750;
        margin-bottom: 0.3rem;
    }

    .section-description {
        color: var(--muted);
        font-size: 0.9rem;
        margin-bottom: 1rem;
        line-height: 1.6;
    }

    /* Information cards */
    .info-card {
        background: var(--white);
        border: 1px solid var(--line);
        border-radius: 13px;
        padding: 1.1rem 1.2rem;
        box-shadow: 0 3px 12px rgba(20, 36, 58, 0.035);
    }

    .info-label {
        color: var(--muted);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        font-weight: 700;
    }

    .info-value {
        color: #1b3553;
        font-size: 1.1rem;
        font-weight: 750;
        margin-top: 0.45rem;
    }

    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 12px 15px;
        box-shadow: 0 3px 12px rgba(20, 36, 58, 0.035);
    }

    /* TAC editor */
    div[data-testid="stTextArea"] textarea {
        background: #101c2b;
        color: #e7f0fa;
        border: 1px solid #304862;
        border-radius: 10px;
        font-family: Consolas, "Cascadia Code", monospace;
        font-size: 0.91rem;
        line-height: 1.6;
    }

    div[data-testid="stTextArea"] label {
        color: var(--ink);
        font-weight: 650;
    }

    /* Buttons */
    div.stButton > button[kind="primary"] {
        background: var(--blue);
        color: white;
        border: 1px solid var(--blue);
        border-radius: 9px;
        min-height: 2.8rem;
        font-weight: 700;
    }

    div.stButton > button {
        border-radius: 9px;
    }

    /* Output */
    div[data-testid="stCode"] {
        border: 1px solid var(--line);
        border-radius: 10px;
    }

    .small-note {
        color: var(--muted);
        font-size: 0.84rem;
        line-height: 1.6;
    }

    .footer {
        border-top: 1px solid #d6e0eb;
        padding-top: 1rem;
        color: #6b7d91;
        font-size: 0.8rem;
        margin-top: 2.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Hero banner
# -------------------------------------------------------------------

st.markdown(
    """
    <div class="hero">
        <div class="hero-eyebrow">
            Project A34 &nbsp;·&nbsp; Static Program Analysis
        </div>
        <h1>Generic Data-Flow Analysis Framework</h1>
        <p>
            Analyse Three-Address Code, inspect the Control-Flow Graph,
            and explore the behaviour of a generic worklist solver across
            four classical data-flow analyses.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Session state
# -------------------------------------------------------------------

examples = discover_examples()

if "tac_source" not in st.session_state:
    st.session_state.tac_source = next(iter(examples.values()))

if "analysis_output" not in st.session_state:
    st.session_state.analysis_output = None

if "cfg_png" not in st.session_state:
    st.session_state.cfg_png = None

if "run_error" not in st.session_state:
    st.session_state.run_error = None

if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = "All four analyses"


# -------------------------------------------------------------------
# Sidebar configuration
# -------------------------------------------------------------------

with st.sidebar:
    st.markdown("## Analysis Workspace")
    st.caption("Configure a program and select an analysis.")

    st.markdown("### 01 · Input Program")

    selected_example = st.selectbox(
        "Example program",
        list(examples.keys()),
    )

    if st.button("Load example program", use_container_width=True):
        st.session_state.tac_source = examples[selected_example]
        st.session_state.analysis_output = None
        st.session_state.cfg_png = None
        st.session_state.run_error = None

    st.markdown("### 02 · Analysis Mode")

    selected_analysis = st.selectbox(
        "Data-flow analysis",
        list(ANALYSES.keys()),
    )

    st.markdown("---")
    st.markdown("### Available Analyses")

    st.markdown(
        """
        **Reaching Definitions**

        **Available Expressions**

        **Live Variables**

        **Constant Propagation**
        """
    )

    st.markdown("---")

    st.caption(
        "The interface delegates execution to the existing Python CLI. "
        "Analysis results are not fabricated by the frontend."
    )


# -------------------------------------------------------------------
# Main workspace
# -------------------------------------------------------------------

st.markdown(
    '<div class="eyebrow">Workspace</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Program Input & Graph Inspection</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">'
    'Edit the TAC source, execute the selected analysis, and inspect the '
    'resulting control-flow graph.'
    '</div>',
    unsafe_allow_html=True,
)

left, right = st.columns([0.95, 1.05], gap="large")


with left:
    st.markdown("### 1. Three-Address Code")

    st.caption(
        "Use the instruction syntax supported by your project parser. "
        "Place labels on separate lines."
    )

    source = st.text_area(
        "TAC source",
        key="tac_source",
        height=360,
        label_visibility="collapsed",
        help=(
            "Enter a valid TAC program. Labels, assignments, and jumps "
            "must follow the repository parser's grammar."
        ),
    )

    run_clicked = st.button(
        "▶  Run Analysis",
        type="primary",
        use_container_width=True,
    )

    st.markdown(
        '<div class="small-note">'
        'The existing parser, CFG builder, worklist solver, and analysis '
        'modules remain unchanged.'
        '</div>',
        unsafe_allow_html=True,
    )


with right:
    st.markdown("### 2. Control-Flow Graph")

    st.caption(
        "The graph is generated from the submitted TAC program."
    )

    if run_clicked:
        with st.spinner("Executing the framework and rendering the graph..."):
            png, output, error = run_framework(
                source,
                ANALYSES[selected_analysis],
            )

        st.session_state.cfg_png = png
        st.session_state.analysis_output = output
        st.session_state.run_error = error
        st.session_state.last_analysis = selected_analysis

    if st.session_state.run_error:
        st.error(st.session_state.run_error)

    elif st.session_state.cfg_png:
        st.image(
            st.session_state.cfg_png,
            use_container_width=True,
        )

        st.download_button(
            "Download CFG as PNG",
            data=st.session_state.cfg_png,
            file_name="control_flow_graph.png",
            mime="image/png",
        )

    else:
        st.markdown(
            """
            <div class="info-card">
                <div class="info-label">Awaiting execution</div>
                <div class="info-value">
                    Your control-flow graph will appear here
                </div>
                <p class="small-note">
                    Select an example or enter TAC, then click
                    <b>Run Analysis</b>.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -------------------------------------------------------------------
# Analysis output
# -------------------------------------------------------------------

st.markdown("---")

st.markdown(
    '<div class="eyebrow">Execution Report</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Analysis Output</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">'
    'Inspect the output returned by the existing framework CLI.'
    '</div>',
    unsafe_allow_html=True,
)


if st.session_state.analysis_output:
    if not st.session_state.run_error:
        st.success(
            f"CLI completed successfully · "
            f"Mode: {st.session_state.last_analysis}"
        )

    output_tab, explanation_tab = st.tabs(
        ["CLI Output", "Interpretation Guide"]
    )

    with output_tab:
        st.code(
            st.session_state.analysis_output,
            language="text",
        )

    with explanation_tab:
        st.markdown(
            """
            ### Understanding the results

            **IN facts**

            Information available when control enters a basic block.

            **OUT facts**

            Information available when control leaves a basic block.

            **Worklist solver**

            The solver processes blocks and propagates data-flow information
            according to the selected analysis. Blocks may be revisited when
            information changes, until the solver reaches a fixed point.

            **Analysis-specific meaning**

            The facts represent different properties depending on the analysis:
            definitions that may reach a block, expressions that remain
            available, variables that are live, or values that can be
            propagated as constants.
            """
        )

elif st.session_state.run_error:
    st.warning(
        "The analysis did not complete. Review the error above, correct "
        "the TAC syntax or configuration, and run it again."
    )

else:
    st.markdown(
        """
        <div class="info-card">
            <div class="info-value">No execution report yet</div>
            <p class="small-note">
                After running the framework, its actual CLI output will
                appear here.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------------
# Footer
# -------------------------------------------------------------------

st.markdown(
    """
    <div class="footer">
        Project A34 · Generic Data-Flow Analysis Framework
        <br>
        Academic demonstration interface · Powered by Python, Streamlit,
        and Graphviz
    </div>
    """,
    unsafe_allow_html=True,
)
