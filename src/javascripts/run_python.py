"""Runs the code blocks of the Python examples in Pyodide, for run-python-worker.js.

The runnable blocks of one page share a namespace, like the cells of a notebook, and a new page starts a fresh one.
The AUSAXS backend is shared by all of them, and its settings are global, so every block starts with the default
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

FILENAME = "<example>"
HOME = os.getcwd()
_namespace = {}
_page = None


def _start_page(page):
    global _namespace, _page
    _page = page
    _namespace = {"__name__": "__main__"}
    os.chdir(HOME)


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
    while tb is not None and tb.tb_frame.f_code.co_filename != FILENAME:
        tb = tb.tb_next
    return "".join(traceback.format_exception(type(e), e, tb))


async def run(code, page):
    """Run one block in the namespace of `page`. Like a notebook, the value of a final expression is printed."""
    if page != _page:
        _start_page(page)
    _reset_backend()
    error = None
    try:
        result = await eval_code_async(code, _namespace, filename=FILENAME)
        if result is not None:
            print(repr(result))
    except BaseException as e:
        error = _format_error(e)
    sys.stdout.flush()
    sys.stderr.flush()
    return {"error": error, "figures": _figures()}
