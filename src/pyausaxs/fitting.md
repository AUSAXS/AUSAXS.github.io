---
title: Fitting SAXS data in Python - AUSAXS
description: "Fit atomic structures to SAXS data in Python with pyAUSAXS: fitted parameters, chi-square, residuals, excluded volume models, and custom objectives."
---

# Fitting SAXS data in Python

## Fitting a structure to data
```python
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
```python
fit.chi2()               # chi-square
fit.dof()                # degrees of freedom: data points minus fitted parameters
fit.chi2r()              # reduced chi-square, chi2/dof
fit.fit_parameters()     # {name: (value, lower error, upper error)}, the lower error negative

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
```python
ausaxs.settings.exv(ausaxs.ExvModel.fraser)
ausaxs.settings.fit(
    fit_hydration=True,          # cw: almost always wanted
    fit_excluded_volume=True,    # cx
    fit_solvent_density=False,   # cr: prone to overfitting
)
fit = mol.fit("2epe.dat")
```
The default `simple` excluded volume model has no excluded volume parameter, so fitting `cx` needs one of the other [excluded volume models](scattering-profiles.md#excluded-volume-models). Fitting the solvent density is discouraged, since it can absorb errors in the model, and AUSAXS warns when it is enabled. AUSAXS also warns when a parameter ends at the edge of its allowed range.

## Comparing models
Since a fit takes milliseconds, it is easy to compare several models on the same data:
```python
data = ausaxs.read_data("2epe.dat")
for model in (ausaxs.ExvModel.simple, ausaxs.ExvModel.fraser, ausaxs.ExvModel.grid):
    ausaxs.settings.exv(model)
    fit = mol.fit(data)
    print(model.name, round(fit.chi2r(), 2))
```

## Custom fits and objectives
`mol.fit` minimises the chi-square over the enabled parameters. To use your own objective, add your own parameters, or fit several datasets at once, use `ausaxs.manual_fit` instead. It evaluates the model profile for parameter values you choose, and leaves the fitting to you:
```python
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
print(best.x, best.fun)
```
`evaluate` takes one value per enabled parameter, in the order `cw`, `cx`, `cr`: with the default settings, only `cw`. It returns the profile before the scale `a` and background `b` are applied. `ausaxs.manual_fit(mol, q)` evaluates at the q values you give instead of those of a dataset, and `evaluate(params, q)` at other q values for a single call.

## Next steps
- Fit every frame of an [MD trajectory](trajectories.md).
- Refine the structure itself with [rigid-body refinement](../applications/rigid-body-refinement.md), from Python or the command line.
- See every option of the fit in the [API reference](reference/index.md).
