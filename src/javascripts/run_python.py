"""Runs the code blocks of the Python examples in Pyodide, for run-python-worker.js.

A standalone block (```python {.run}) runs in a fresh namespace, every time it runs, and the continuing blocks after
it (```python {.run .continue}) share that namespace, like the cells of a notebook: together they form a chain. A
page can have several chains, and a new page starts over. A fresh namespace first runs the page's setup blocks
(```python {.run .setup}), such as the plotting helpers the examples call. The AUSAXS backend is shared by all of them, and its settings are global, so every block starts with the default
settings: otherwise a block would depend on which blocks ran before it, and a re-run of an earlier block would quietly
use the settings of a later one. The blocks are written so that each sets the settings it needs.
"""

import base64
import io
import os
import sys
import traceback
import warnings

from pyodide.code import eval_code_async

os.environ["MPLBACKEND"] = "Agg"  # figures are rendered to PNG and shown below the block, so plt.show() is a no-op
warnings.filterwarnings("ignore", "FigureCanvasAgg is non-interactive")
# FitResult.plot() in pyAUSAXS 1.3.8 calls tight_layout on a grid with its own spacing, which warns although the figure
# is fine (BL-354 in AUSAXS-agent-notes). Remove this once a release without the warning is out.
warnings.filterwarnings("ignore", "This figure includes Axes that are not compatible with tight_layout")

FILENAME, SETUP = "<example>", "<setup>"
HOME = os.getcwd()
_namespaces = {}  # chain -> its namespace, for the chains of the current page
_page = None


def _namespace(page, chain, fresh):
    global _page
    if page != _page:
        _page = page
        _namespaces.clear()
    if fresh or chain not in _namespaces:
        _namespaces[chain] = {"__name__": "__main__"}
        os.chdir(HOME)
    return _namespaces[chain]


def _reset_backend():
    """Fresh settings, and AUSAXS's output back on stdout, in case a block failed while it was redirected."""
    ausaxs = sys.modules.get("pyausaxs")
    if ausaxs is not None:
        ausaxs.settings.reset()
        ausaxs.reset_output_callback()
    if "matplotlib.pyplot" in sys.modules:
        sys.modules["matplotlib.pyplot"].close("all")


def _figures():
    """The open matplotlib figures as base64 PNGs, which are then closed."""
    plt = sys.modules.get("matplotlib.pyplot")
    if plt is None:
        return []
    images = []
    for number in plt.get_fignums():
        buffer = io.BytesIO()
        plt.figure(number).savefig(buffer, format="png", dpi=96, bbox_inches="tight")
        images.append(base64.b64encode(buffer.getvalue()).decode())
    plt.close("all")
    return images


def _format_error(e):
    # skip the frames of Pyodide's own code, so the traceback starts at the example
    tb = e.__traceback__
    while tb is not None and tb.tb_frame.f_code.co_filename not in (FILENAME, SETUP):
        tb = tb.tb_next
    return "".join(traceback.format_exception(type(e), e, tb))


def _is_plot(value):
    """Whether a value is a matplotlib object, such as the figure of fit.plot(), or a list of them, as plt.plot gives.
    The figure is shown below the block anyway, so its repr is left out, as in a notebook."""
    items = value if isinstance(value, (list, tuple)) else [value]
    return bool(items) and all(type(item).__module__.startswith("matplotlib.") for item in items)


async def run(code, page, chain, fresh, setup):
    """Run one block in the namespace of chain `chain` of page `page`, which is new if `fresh`, as for a standalone
    block; a new namespace first runs the code `setup`. Like a notebook, the value of a final expression is printed,
    unless it is a plot."""
    namespace = _namespace(page, chain, fresh)
    _reset_backend()
    error = None
    try:
        if fresh and setup:
            await eval_code_async(setup, namespace, filename=SETUP)
        result = await eval_code_async(code, namespace, filename=FILENAME)
        if result is not None and not _is_plot(result):
            print(repr(result))
    except BaseException as e:
        error = _format_error(e)
    sys.stdout.flush()
    sys.stderr.flush()
    return {"error": error, "figures": _figures()}
