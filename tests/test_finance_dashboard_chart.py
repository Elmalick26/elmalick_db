"""Q3 — finance_dashboard chart must not leak figures via pyplot.

The dashboard previously built its chart with plt.subplots(), which registers
the figure in pyplot's global manager (never garbage-collected → leak on every
rebuild). It now uses the object-oriented Figure owned by the canvas.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import finance_dashboard


def test_module_does_not_import_pyplot():
    # pyplot is the leak source: a module that never imports it cannot register
    # figures in pyplot's global manager, so it cannot leak them.
    assert not hasattr(finance_dashboard, "plt")
    assert hasattr(finance_dashboard, "Figure")


def test_source_uses_oo_figure_not_pyplot():
    # Source-based guard (immune to module-mock pollution from other tests):
    # the chart must be built with the OO Figure, never plt.subplots/pyplot.
    import inspect

    src = inspect.getsource(finance_dashboard)
    assert "import matplotlib.pyplot" not in src
    assert "plt.subplots" not in src
    assert "Figure(" in src


def test_oo_figure_constructs_with_axes():
    # finance_dashboard.Figure must be the real object-oriented matplotlib
    # Figure — not a MagicMock leaked from test_analytics_dashboard. Build one
    # directly and confirm the axes it creates are owned by the figure (the
    # canvas-owned, pyplot-free construction the dashboard relies on).
    fig = finance_dashboard.Figure(figsize=(4, 3))
    ax = fig.add_subplot(111)
    assert ax.figure is fig
