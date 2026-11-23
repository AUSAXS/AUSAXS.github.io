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
q, I = mol.debye()                 # the SAXS profile, as two NumPy arrays
fit = mol.fit("2epe.dat")          # fit it to a measurement
print(fit.chi2r(), fit.fit_parameters())
```

It installs with `pip`, and comes with prebuilt libraries for Linux, macOS and Windows:
```bash
python -m pip install pyausaxs
```

## Why use AUSAXS from Python?
- **No files in between.** The command-line tools read files and write files. From Python, you pass structures and data in as files or arrays, and get the profile, the fit, the distance histogram or the atomic coordinates back as arrays, ready for NumPy, SciPy and matplotlib.
- **Fast enough to call in a loop.** Hydrating lysozyme and calculating its profile takes milliseconds, so you can compute thousands of profiles: one per frame of an [MD trajectory](trajectories.md), per member of an ensemble, or per step of your own optimizer.
- **The same engine as the command line.** pyAUSAXS calls the same library as `ausaxs fit`, with the same hydration shell, excluded volume models and fitting. With the same settings, Python and the command line give the same result, up to the random placement of the hydration shell.
- **Fits into your own analysis.** Use AUSAXS as one step of a larger pipeline: evaluate the model for [parameters of your choice](fitting.md#custom-fits-and-objectives) inside your own fit, or use [the gradient of the Debye equation](gradients.md) to refine coordinates or train a model with PyTorch.
- **Command line and graphical interface included.** Installing pyAUSAXS also installs the `ausaxs` command and its [graphical interface](../documentation/cli/fit.md#graphical-user-interface), so there is nothing else to set up.

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
