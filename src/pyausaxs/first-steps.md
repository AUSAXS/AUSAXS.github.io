---
title: Getting started with pyAUSAXS - AUSAXS
description: "pyAUSAXS quick start: install the package, read a PDB structure and SAXS data, calculate and fit a profile, and control units, q range and settings."
---

# First steps with pyAUSAXS

## Installation
pyAUSAXS needs Python 3.10 or newer. Install it with:
```bash
python -m pip install pyausaxs
```
The core package only depends on NumPy. Install it as `pyausaxs[plots]` to also get matplotlib for `FitResult.plot()` and `ausaxs plot`, or as `pyausaxs[all]` for the [graphical interface](../documentation/cli/fit.md#graphical-user-interface) as well. Check that it works with:
```bash
python -c "import pyausaxs; print(pyausaxs.__version__)"
```
If it fails, see the [troubleshooting](../getting-started/troubleshooting.md) page.

The examples in this guide use the structure of hen egg-white lysozyme, [2epe.pdb](https://raw.githubusercontent.com/AUSAXS/AUSAXS/master/tests/files/2epe.pdb), and a SAXS measurement of it, [2epe.dat](https://raw.githubusercontent.com/AUSAXS/AUSAXS/master/tests/files/2epe.dat). Download both into the folder you run Python from.

To try the examples without installing anything, press the **Run** button below them: they run in your browser, with both files already in place. An example marked with ↳ next to its copy button builds on the examples before it, like a cell of a notebook, and running it also runs those that have not run yet. The other examples stand on their own.

??? example "Plotting helper"

    The examples on this page draw their plots with this function, so that they show only the pyAUSAXS calls. It runs by itself before them.

    ```python {.run .setup}
    import matplotlib.pyplot as plt

    def plot(x=None, curves=None, data=None, reference=None, logx=False, logy=True, xlabel="q [Å⁻¹]", ylabel="I(q)", **style):
        """Plot a curve, or a dict {label: curve} of curves, against x.
        data:      measured data (q, I, Ierr), drawn as points with error bars
        reference: a (label, curve) pair, drawn as a black dashed line, e.g. an exact result
        """
        if data is not None:
            plt.errorbar(*data, fmt=".", color="gray", label="data")
        if isinstance(curves, dict):
            for label, y in curves.items():
                plt.plot(x, y, label=label, **style)
        elif curves is not None:
            plt.plot(x, curves, **style)
        if reference is not None:
            plt.plot(x, reference[1], "k--", label=reference[0])
        if logx:
            plt.xscale("log")
        if logy:
            plt.yscale("log")
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        if plt.gca().get_legend_handles_labels()[1]:
            plt.legend()
        plt.show()
    ```

## The building blocks
Everything is imported from one module, by convention as `ausaxs`.

**Molecules.** `ausaxs.create_molecule` reads a structure from a PDB, mmCIF or XYZ file. The molecule holds the atoms with their form factors and its hydration shell, and calculates everything else: the scattering profile, the distance histogram, the radius of gyration, and fits.
```python {.run}
import pyausaxs as ausaxs

mol = ausaxs.create_molecule("2epe.pdb")
mol.hydrate()              # place a hydration shell around it
q, I = mol.debye()         # its SAXS profile
print(f"radius of gyration: {mol.Rg():.1f} Å")
plot(q, I)
```

**Datasets.** `ausaxs.read_data` reads a measured profile with columns q, I and its error. For data that is already in memory, `ausaxs.create_datafile(q, I, Ierr)` does the same from three arrays.
```python {.run .continue}
data = ausaxs.read_data("2epe.dat")
q, I, Ierr = data.data()
print(f"{len(q)} points, q from {q[0]:.3f} to {q[-1]:.3f} Å⁻¹")
plot(data=(q, I, Ierr))
```
AUSAXS prints what it reads. If it warns that the unit of q is ambiguous, see [units and q range](#units-and-q-range) below.

**Fit results.** `mol.fit(data)` fits the molecule to a dataset, and returns the goodness of fit, the fitted parameters and the fitted curve. It also accepts the path of a data file directly.
```python {.run .continue}
fit = mol.fit(data)
print(f"reduced chi-square: {fit.chi2r():.2f}")
q, I, Ierr = fit.data_curve()  # the data used in the fit
I_fit = fit.fitted_curve()     # the model at the same q values
plot(q, {"fit": I_fit}, data=(q, I, Ierr))
```
`fit.plot()` draws the same, with the residuals below; the [fitting guide](fitting.md) shows it.

**Settings.** `ausaxs.settings` holds every option of the calculations, such as the [excluded volume model](scattering-profiles.md#excluded-volume-models), which [parameters are fitted](fitting.md#what-is-fitted), and the q range. The settings apply to everything you calculate after changing them, until you change them again or call `ausaxs.settings.reset()`.
```python {.run .continue}
ausaxs.settings.exv(ausaxs.ExvModel.fraser)
ausaxs.settings.fit(fit_excluded_volume=True)
fit = mol.fit(data)
print(f"reduced chi-square: {fit.chi2r():.2f}, fitted: {', '.join(fit.fit_parameters())}")
```

## Units and q range
- **q is in Å⁻¹** everywhere: in the arrays you pass in, and in the arrays you get back. Data files in nm⁻¹ are converted when they are read. AUSAXS guesses the unit of a file from its q values; if the guess is wrong, set it with `ausaxs.settings.histogram(unit="nm")` or `unit="A"` before reading the file.
- **The default q axis** runs from 10⁻⁴ to 0.5 Å⁻¹ in 101 points; `ausaxs.settings.q_axis()` returns it. Change its range with `ausaxs.settings.histogram(qmin=..., qmax=...)`, or pass your own q values to the calculation, e.g. `mol.debye(q)`.
- **Data outside the q range** is removed when it is read, so widen the range first if your data goes beyond 0.5 Å⁻¹. The hydration shell and excluded volume models are meant for q up to about 1 Å⁻¹.

## Output messages
AUSAXS prints what it is doing, such as the number of atoms it read, and warns about anything unusual in the input. To keep it quiet:
```python {.run}
import pyausaxs as ausaxs

ausaxs.settings.general(verbose=False)                  # no progress messages
ausaxs.settings.general(verbose=False, warnings=False)  # nothing at all
```

??? info "Sending the messages elsewhere"

    To show the messages somewhere else, for instance in a log or a GUI, pass a function that receives each message. The messages are passed on as AUSAXS writes them, including the terminal colour codes and the line break.

    ```python {.run}
    import pyausaxs as ausaxs

    messages = []
    ausaxs.set_output_callback(messages.append)
    mol = ausaxs.create_molecule("2epe.pdb")
    ausaxs.reset_output_callback()
    print(f"captured {len(messages)} messages, the first: {messages[0]!r}")
    ```

Errors are raised as Python exceptions with the message from AUSAXS, e.g. for a file that does not exist:
```python {.run}
import pyausaxs as ausaxs

try:
    ausaxs.create_molecule("missing.pdb")
except RuntimeError as e:
    print("could not read the structure:", e)
```

## Saving settings
`ausaxs.settings.save("settings.txt")` writes every setting to a text file, and `ausaxs.settings.load("settings.txt")` reads it back. The file has the same format as the settings files of the [command-line tools](../documentation/cli/fit.md), so you can share a configuration between Python and the command line.
```python {.run}
import pyausaxs as ausaxs

ausaxs.settings.exv(ausaxs.ExvModel.fraser)
ausaxs.settings.save("settings.txt")
print(open("settings.txt").read())
```

## Next steps
- [Calculate SAXS profiles](scattering-profiles.md), with control over the hydration shell and excluded volume.
- [Fit structures to data](fitting.md), and read the fitted parameters.
- Look up a function or setting in the [API reference](reference/index.md).
