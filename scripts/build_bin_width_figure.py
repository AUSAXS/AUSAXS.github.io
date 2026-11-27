#!/usr/bin/env python3
"""Build the figure of the histogram-accuracy page: the binning error of the Debye sum against the exact sum.

Every atom is a point scatterer weighted by its electrons. The binned profile is debye() with the 'none' excluded volume
model on the default q nodes, whose exp(-q²) is divided out; the reference is ausaxs.unoptimized.debye_exact on the same
nodes. Writes histogram-accuracy.svg and histogram-accuracy-dark.svg to src/assets/figures/; use them as a pair:

    ![alt](../assets/figures/histogram-accuracy.svg#only-light)
    ![alt](../assets/figures/histogram-accuracy-dark.svg#only-dark)

Needs pyausaxs and matplotlib. Usage: python scripts/build_bin_width_figure.py
"""
import io
import sys

import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
import numpy as np
import pyausaxs as ausaxs

from build_debye_figures import style
from build_figures import OUTPUT
from build_fit_figure import DATA, DOCS, THEMES


def binning_error(path: str, bins: list[tuple[float, bool]]) -> tuple[np.ndarray, dict]:
    """The relative error |I_binned/I_exact - 1| in percent for each (bin width, weighted) pair."""
    ausaxs.settings.general(verbose=False, warnings=False)
    ausaxs.settings.histogram(qmin=0.005, qmax=1)
    ausaxs.settings.exv(ausaxs.ExvModel.none)
    x, y, z, w = ausaxs.create_molecule(path).atoms()[:4]
    q, exact = ausaxs.unoptimized.debye_exact(ausaxs.create_molecule(x, y, z, w))
    errors = {}
    for width, weighted in bins:
        ausaxs.settings.histogram(bin_width=width, weighted_bins=weighted)
        _, I = ausaxs.create_molecule(x, y, z, w).debye()
        errors[(width, weighted)] = 100*np.abs(I*np.exp(q*q)/exact - 1)
    return q, errors


def calculate() -> dict:
    protein = binning_error(str(DATA / "2epe.pdb"), [(0.05, False), (0.1, False), (0.25, False), (0.5, False)])
    crystal = binning_error(str(DATA / "Ag_crystal.cif"), [(0.25, False), (0.25, True), (0.05, True)])
    return {"protein": protein, "crystal": crystal}


def draw(result: dict, colours: dict):
    style(colours)
    fig, axs = plt.subplots(1, 2, figsize=(7, 3.2), sharey=True)
    fig.subplots_adjust(left=0.1, right=0.98, top=0.9, bottom=0.16, wspace=0.08)
    fig.patch.set_alpha(0)
    lines = {
        "protein": {
            (0.05, False): ("0.05 Å", colours["data"], "-", 1.0),
            (0.1, False):  ("0.1 Å", colours["data"], "--", 1.0),
            (0.25, False): ("0.25 Å (default)", colours["fit"], "-", 1.8),
            (0.5, False):  ("0.5 Å", colours["muted"], ":", 1.2),
        },
        "crystal": {
            (0.25, False): ("0.25 Å, unweighted", colours["muted"], ":", 1.2),
            (0.25, True):  ("0.25 Å, weighted", colours["fit"], "-", 1.8),
            (0.05, True):  ("0.05 Å, weighted", colours["data"], "--", 1.0),
        },
    }
    titles = {"protein": "Protein (2epe), unweighted bins", "crystal": "Silver nanoparticle (201 atoms)"}
    for ax, name in zip(axs, ["protein", "crystal"]):
        q, errors = result[name]
        for key, (label, colour, ls, lw) in lines[name].items():
            ax.plot(q, errors[key], color=colour, ls=ls, lw=lw, label=label)
        ax.set_yscale("log")
        ax.set_ylim(1e-4, 300)
        ax.set_xlim(0, 1)
        ax.set_title(titles[name], fontsize=10, color=colours["ink"])
        ax.set_xlabel(r"$q$ (Å$^{-1}$)")
        ax.spines[["top", "right"]].set_visible(False)
        ax.patch.set_alpha(0)
        ax.grid(True, color=colours["line"], lw=0.6)
        ax.set_axisbelow(True)
        ax.legend(frameon=False, fontsize=8, loc="upper left")
    axs[0].set_ylabel("binning error (%)")
    return fig


def main() -> int:
    result = calculate()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for scheme, colours in THEMES.items():
        fig = draw(result, colours)
        buffer = io.StringIO()
        fig.savefig(buffer, format="svg", metadata={"Date": None})
        plt.close(fig)
        out = OUTPUT / ("histogram-accuracy.svg" if scheme == "light" else "histogram-accuracy-dark.svg")
        out.write_text(buffer.getvalue(), encoding="utf-8")
        print(f"-> {out.relative_to(DOCS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
