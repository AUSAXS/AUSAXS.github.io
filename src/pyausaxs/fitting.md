---
title: Fitting SAXS data in Python - AUSAXS
description: "Fit atomic structures to SAXS data in Python with pyAUSAXS: fitted parameters, chi-square, residuals, excluded volume models, and custom objectives."
---

# Fitting SAXS data in Python

??? example "Plotting helper"

    The examples on this page draw their plots with this function, so that they show only the pyAUSAXS calls. It runs by itself before them.

    ```python {.run .setup}
    import matplotlib.pyplot as plt

    def plot(x=None, curves=None, data=None, reference=None, logy=True, xlabel="q [Å⁻¹]", ylabel="I(q)", **style):
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
        if logy:
            plt.yscale("log")
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        if plt.gca().get_legend_handles_labels()[1]:
            plt.legend()
        plt.show()
    ```

## Fitting a structure to data
```python {.run}
import pyausaxs as ausaxs
import matplotlib.pyplot as plt

mol = ausaxs.create_molecule("2epe.pdb")
mol.hydrate()
fit = mol.fit("2epe.dat")
print(f"reduced chi-square: {fit.chi2r():.2f}")
fit.plot()
plt.show()
```
`fit()` takes the path of a data file, or a dataset from `ausaxs.read_data` or `ausaxs.create_datafile`. When you fit the same data more than once, read it once and pass the dataset, so the file is not read again every time.

`plot()` draws the data with the fitted curve, and the residuals below, and returns the matplotlib figure. It needs matplotlib, which is installed with `pyausaxs[plots]`.

## Reading the result
```python {.run .continue}
chi2 = fit.chi2()               # chi-square
dof = fit.dof()                 # degrees of freedom: data points minus fitted parameters
chi2r = fit.chi2r()             # reduced chi-square, chi2/dof
print(f"chi2 = {chi2:.1f}, dof = {dof}, chi2r = {chi2r:.2f}")

params = fit.fit_parameters()   # {name: (value, lower error, upper error)}, the lower error negative
for name, (value, lower, upper) in params.items():
    print(f"{name:>2} = {value:.4g}  {lower:+.2g} / {upper:+.2g}")

q, I, Ierr = fit.data_curve()   # the data used in the fit
I_fit = fit.fitted_curve()      # the fitted model at the same q values
r = fit.residuals()             # (I - I_fit)/Ierr
```
The data is the measurement after the [q range](first-steps.md#units-and-q-range) has been applied, in Å⁻¹, so it can be shorter than the file.

The fitted parameters are:

| Name | Parameter | Fitted |
|------|-----------|--------|
| `a` | Intensity scale of the model | Always |
| `b` | Constant background | Always |
| `cw` | Scattering strength of the hydration shell | By default |
| `cx` | Scale of the excluded volume, relative to its default | With `fit_excluded_volume=True` |
| `cr` | Density of the bulk solvent, relative to its default | With `fit_solvent_density=True` |

The model compared with the data is `a·I(q) + b`, where `I(q)` is the profile for the given `cw`, `cx` and `cr`.

## What is fitted
`ausaxs.settings.fit` chooses which parameters are fitted, besides `a` and `b`:
```python {.run .continue}
ausaxs.settings.exv(ausaxs.ExvModel.fraser)
ausaxs.settings.fit(
    fit_hydration=True,          # cw: almost always wanted
    fit_excluded_volume=True,    # cx
    fit_solvent_density=False,   # cr: prone to overfitting
)
fit = mol.fit("2epe.dat")
for name, (value, lower, upper) in fit.fit_parameters().items():
    print(f"{name:>2} = {value:.4g}  {lower:+.2g} / {upper:+.2g}")
```
The default `simple` excluded volume model has no excluded volume parameter, so fitting `cx` needs one of the other [excluded volume models](scattering-profiles.md#excluded-volume-models). Fitting the solvent density is discouraged, since it can absorb errors in the model, and AUSAXS warns when it is enabled. AUSAXS also warns when a parameter ends at the edge of its allowed range.

## Comparing models
Since a fit takes milliseconds, it is easy to compare several models on the same data:
```python {.run .continue}
data = ausaxs.read_data("2epe.dat")
fits = {}
for model in (ausaxs.ExvModel.simple, ausaxs.ExvModel.fraser, ausaxs.ExvModel.grid):
    ausaxs.settings.exv(model)
    fit = mol.fit(data)
    print(f"{model.name:>6}: reduced chi-square {fit.chi2r():.2f}")
    fits[model.name] = fit.fitted_curve()
q, I, Ierr = fit.data_curve()
plot(q, fits, data=(q, I, Ierr))
```

## Custom fits and objectives
`mol.fit` minimises the chi-square over the enabled parameters. To use your own objective, add your own parameters, or fit several datasets at once, use `ausaxs.manual_fit` instead. It evaluates the model profile for parameter values you choose, and leaves the fitting to you:
```python {.run .continue}
import numpy as np
from scipy.optimize import minimize_scalar

ausaxs.settings.reset()
data = ausaxs.read_data("2epe.dat")
q, I, Ierr = data.data()
model = ausaxs.manual_fit(mol, data)     # evaluates at the q values of the data

def chi2(cw):
    I_model = model.evaluate([cw])       # the profile for this hydration shell
    # the best a and b for this profile follow from a weighted linear fit
    A = np.column_stack([I_model, np.ones_like(q)])/Ierr[:, None]
    (a, b), *_ = np.linalg.lstsq(A, I/Ierr, rcond=None)
    return np.sum(((I - a*I_model - b)/Ierr)**2)

best = minimize_scalar(chi2, bounds=(0, 5), method="bounded")
print(f"own fit:   cw = {best.x:.4f}, chi-square = {best.fun:.1f}")

fit = mol.fit(data)                      # the same fit, done by AUSAXS
print(f"mol.fit(): cw = {fit.fit_parameters()['cw'][0]:.4f}, chi-square = {fit.chi2():.1f}")
```
`evaluate` takes one value per enabled parameter, in the order `cw`, `cx`, `cr`: with the default settings, only `cw`. It returns the profile before the scale `a` and background `b` are applied. `ausaxs.manual_fit(mol, q)` evaluates at the q values you give instead of those of a dataset, and `evaluate(params, q)` at other q values for a single call.

## Next steps
- Fit every frame of an [MD trajectory](trajectories.md).
- Refine the structure itself with [rigid-body refinement](../applications/rigid-body-refinement.md), from Python or the command line.
- See every option of the fit in the [API reference](reference/index.md).
