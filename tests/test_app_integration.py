"""
Streamlit dashboard <-> CLI integration
----------------------------------------
app.py does not reimplement the parser/solver/analyses -- it shells out to
the real `python -m dataflow.cli ... --analysis <alias>` (see
run_framework() in app.py). That means the analysis aliases the dashboard
sends on the command line must actually be choices the CLI's argparse
accepts, or picking that option in the UI does nothing but show an
argparse usage error instead of running the analysis.

This is skipped (not failed) when streamlit isn't installed, since the
project's framework itself has zero third-party dependencies and
streamlit is only needed for the optional dashboard -- see README
"Requirements".
"""

import importlib
import unittest

try:
    import streamlit  # noqa: F401
    HAVE_STREAMLIT = True
except ImportError:
    HAVE_STREAMLIT = False

from dataflow import cli


@unittest.skipUnless(
    HAVE_STREAMLIT,
    "streamlit not installed -- optional dashboard dependency, see README",
)
class TestDashboardAnalysisAliases(unittest.TestCase):
    def test_every_dashboard_alias_is_a_cli_accepted_analysis_choice(self):
        # dataflow.cli.ANALYSES is the ground truth for what --analysis
        # accepts (reaching/available/live/constprop); the dashboard must
        # send exactly one of these, or that key, per app.run_framework(),
        # the subprocess call fails with an argparse "invalid choice" error
        # and the selected analysis never runs.
        app = importlib.import_module("app")
        valid_choices = set(cli.ANALYSES)

        for label, alias in app.ANALYSES.items():
            if alias is None:  # "All four analyses" -> no --analysis flag
                continue
            self.assertIn(
                alias,
                valid_choices,
                f"dashboard option {label!r} sends --analysis {alias!r}, "
                f"which is not one of the CLI's accepted choices "
                f"{sorted(valid_choices)} -- selecting it in the UI will "
                f"fail with an argparse error instead of running.",
            )


if __name__ == "__main__":
    unittest.main()
