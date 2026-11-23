---
title: "pyAUSAXS: SAXS and SANS calculations in Python - AUSAXS"
description: "pyAUSAXS is the Python package of AUSAXS: calculate SAXS and SANS profiles of atomic structures and fit them to data from Python, with NumPy arrays."
---

# pyAUSAXS

pyAUSAXS is the Python interface to <span class="ausaxs-name"><span class="au">AU</span>SAXS</span>. It runs the same C++ engine as the command-line tools, and returns every result as a NumPy array. Read a structure, add a hydration shell, calculate its SAXS profile and fit it to data, all in a few lines of Python:

```python
import pyausaxs as ausaxs

mol = ausaxs.create_molecule("2epe.pdb")
mol.hydrate()
q, I = mol.debye()                 # the SAXS profile, as two numpy arrays
fit = mol.fit("2epe.dat")          # fit it to a measurement
print(fit.chi2r(), fit.fit_parameters())
```

It installs with `pip`, and comes with prebuilt libraries for Linux, macOS and Windows:
```bash
python -m pip install pyausaxs
```

## Why use AUSAXS from Python?
- **A straightforward Python workflow.** With just a bit of Python you can read a structure, calculate its profile, and fit it to data, without learning a new command-line interface or its arguments. Results come back as NumPy arrays, ready to inspect, plot, or use in the rest of your script.
- **Fits into your own analysis.** For more advanced integration, pass structures, coordinates, or measured data in from your own code and use the resulting profiles in whatever analysis tool you need: from PyTorch model training with [the gradient of the Debye equation](gradients.md) to [analysis of MD trajectories](trajectories.md).
- **High performance when it matters.** pyAUSAXS delegates the numerical work to the compiled AUSAXS C++ backend, so large parameter scans do not require giving up Python. A hydrated lysozyme profile takes milliseconds, making high-throughput calculations practical for an [MD trajectory](trajectories.md), an ensemble or your own optimizer.
- **One installation, several ways to work.** `pip install pyausaxs` provides the Python API and prebuilt libraries for Linux, macOS and Windows. Optional extras add plotting and the graphical interface, while the same package also provides the `ausaxs` command-line tools, including `ausaxs plot`. Move between scripts, notebooks, the terminal and the [GUI](../documentation/cli/fit.md#graphical-user-interface) without maintaining separate installations.

## Guides

<div class="grid cards" markdown>

-   :material-rocket-launch-outline:{ .lg .middle } **[First steps](first-steps.md)**

    ---

    Install pyAUSAXS, and learn its building blocks: molecules, datasets, fit results and settings.

-   :ausaxs-xray:{ .lg .middle } **[SAXS profiles](scattering-profiles.md)**

    ---

    Calculate the scattering profile of a structure, with or without hydration shell and excluded volume.

-   :material-chart-bell-curve-cumulative:{ .lg .middle } **[Fitting data](fitting.md)**

    ---

    Fit a structure to SAXS data, compare excluded volume models, or plug AUSAXS into your own fit.

-   :material-movie-open-outline:{ .lg .middle } **[MD trajectories](trajectories.md)**

    ---

    Calculate the SAXS profile of every frame of a molecular dynamics trajectory, or of an ensemble.

-   :material-function-variant:{ .lg .middle } **[Gradients](gradients.md)**

    ---

    Differentiate the Debye equation with respect to the atomic coordinates, for refinement and machine learning.

-   :material-shape-outline:{ .lg .middle } **[Geometric shapes](shapes.md)**

    ---

    Calculate the scattering of spheres, cylinders and any other homogeneous body you can describe.

</div>

The [applications](../applications/index.md) pages show pyAUSAXS next to the command line for [SAXS](../applications/saxs.md), [SANS](../applications/sans.md), [rigid-body refinement](../applications/rigid-body-refinement.md), [crystals and nanoparticles](../applications/crystals.md) and [powder diffraction](../applications/powder-diffraction.md). Every function and setting is listed in the [API reference](reference/index.md).

## Examples
The [pyAUSAXS examples](https://github.com/AUSAXS/pyAUSAXS/tree/master/examples) are complete, runnable scripts, from a basic Debye calculation to model fitting, distance histograms, crystal scattering and homogeneous shapes. The structure and data files they use are in the [test files](https://github.com/AUSAXS/pyAUSAXS/tree/master/tests/files) of the repository.

## Citing pyAUSAXS
If you use pyAUSAXS in published work, cite the AUSAXS paper, as described in [Citing AUSAXS](../documentation/citing.md).
