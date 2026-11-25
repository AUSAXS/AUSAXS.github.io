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

os.environ["MPLBACKEND"] = "Agg"  # figures are rendered to PNG, and animations to GIF, and shown below the block, so plt.show() is a no-op
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


def _animations(values):
    """The matplotlib animations among values, by the id of their figure."""
    animation = sys.modules.get("matplotlib.animation")
    if animation is None:
        return {}
    return {id(value._fig): value for value in values if isinstance(value, animation.Animation)}


def _gif(anim):
    """An animation as an animated GIF, which rests on its last frame for a moment before it starts over."""
    from matplotlib.animation import AbstractMovieWriter
    from PIL import Image

    class Writer(AbstractMovieWriter):
        def setup(self, fig, outfile, dpi=None):
            super().setup(fig, outfile, dpi)
            self.frames = []

        def grab_frame(self, **savefig_kwargs):
            buffer = io.BytesIO()
            self.fig.savefig(buffer, **{**savefig_kwargs, "format": "rgba", "dpi": self.dpi})
            self.frames.append(Image.frombuffer("RGBA", self.frame_size, buffer.getbuffer(), "raw", "RGBA", 0, 1))

        def finish(self):
            durations = [round(1000/self.fps)]*(len(self.frames) - 1) + [1500]
            self.frames[0].save(self.outfile, save_all=True, append_images=self.frames[1:], duration=durations, loop=0)

    interval = getattr(anim.event_source, "interval", 100)
    path = "/tmp/animation.gif"
    anim.save(path, writer=Writer(fps=1000/interval), dpi=96)
    with open(path, "rb") as file:
        data = file.read()
    os.remove(path)
    return data


def _figures(values):
    """The open matplotlib figures as data: URLs, which are then closed: an animation among values, such as the final
    expression or a variable, as an animated GIF, and other figures as PNGs."""
    plt = sys.modules.get("matplotlib.pyplot")
    if plt is None:
        return []
    animations = _animations(values)
    images = []
    for number in plt.get_fignums():
        figure = plt.figure(number)
        if id(figure) in animations:
            images.append("data:image/gif;base64," + base64.b64encode(_gif(animations[id(figure)])).decode())
            continue
        buffer = io.BytesIO()
        figure.savefig(buffer, format="png", dpi=96, bbox_inches="tight")
        images.append("data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode())
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
    error = result = None
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
    try:
        figures = _figures([result, *namespace.values()])
    except BaseException as e:
        error, figures = error or _format_error(e), []
    return {"error": error, "figures": figures}
