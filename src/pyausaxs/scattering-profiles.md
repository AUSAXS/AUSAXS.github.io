---
title: Calculating SAXS profiles in Python - AUSAXS
description: "Calculate SAXS profiles of proteins in Python with pyAUSAXS: hydration shell, excluded volume models, custom q values, distance histograms and Rg."
---

# Calculating SAXS profiles in Python

A molecule's SAXS profile is calculated from three parts: its atoms in vacuum, its hydration shell, and the excluded volume, the average solvent density throughout the modeled region, which is subtracted. The [SAXS application page](../applications/saxs.md) explains them; this page shows how to calculate them with pyAUSAXS.

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

    def plot_slice(atoms, waters, width=6):
        """Plot the atoms and waters within width/2 Å of the middle of the atoms along z, seen along z."""
        z0 = atoms[2].mean()
        for (x, y, z), label in ((atoms, "atoms"), (waters, "waters")):
            near = abs(z - z0) < width/2
            plt.scatter(x[near], y[near], s=8, label=label)
        plt.gca().set_aspect("equal")
        plt.xlabel("x [Å]")
        plt.ylabel("y [Å]")
        plt.legend()
        plt.show()
    ```

## The profile of a molecule
```python {.run}
import pyausaxs as ausaxs

mol = ausaxs.create_molecule("2epe.pdb")
mol.hydrate()
q, I = mol.debye()
plot(q, I)
```
`debye()` returns the profile on the [default q axis](first-steps.md#units-and-q-range), with atomic form factors, the hydration shell and the excluded volume. To evaluate it at other q values, such as those of a measurement, pass them in:
```python {.run .continue}
import numpy as np

q = np.linspace(0.01, 0.4, 40)
_, I = mol.debye(q)
plot(q, I, marker="o")
```

## The hydration shell
`mol.hydrate()` places water molecules around the surface of the molecule. Their positions are available as arrays, as are those of the atoms, e.g. to inspect the shell or write it to a file of your own:
```python {.run}
import pyausaxs as ausaxs

mol = ausaxs.create_molecule("2epe.pdb")
mol.hydrate()
x, y, z, weights, form_factors = mol.atoms()
wx, wy, wz, wweights = mol.waters()
plot_slice((x, y, z), (wx, wy, wz))   # a slice through the middle of the molecule
```

??? info "Waters in the structure file"

    Water molecules in the structure file are used as the hydration shell until `hydrate()` replaces them, and `mol.clear_hydration()` removes the shell again. Without a shell, the profile is that of the molecule in vacuum minus its excluded volume.

The shell is placed at random, so each call to `hydrate()` gives a slightly different profile. Here are the profiles of 50 shells, each drawn faintly, so that they add up where they overlap:
```python {.run .continue}
import numpy as np

profiles = []
for _ in range(50):
    mol.hydrate()
    q, I = mol.debye()
    profiles.append(I)
plot(q, np.transpose(profiles), color="C0", alpha=0.1)
```
For a smooth result, average the profiles of several shells, `np.mean(profiles, axis=0)`.

## Excluded volume models
The excluded volume model describes the homogeneous average solvent density throughout the modeled volume. Choose one with `ausaxs.settings.exv`, before calculating. The models give different profiles for the same structure, mostly at higher q, where the excluded volume matters most:
```python {.run}
import pyausaxs as ausaxs

mol = ausaxs.create_molecule("2epe.pdb")
mol.hydrate()
profiles = {}
for model in (ausaxs.ExvModel.simple, ausaxs.ExvModel.fraser, ausaxs.ExvModel.grid):
    ausaxs.settings.exv(model)
    q, profiles[model.name] = mol.debye()
plot(q, profiles)
```
A fit adjusts for much of the difference, as the [fitting guide](fitting.md#comparing-models) shows.

| Model | Description |
|-------|-------------|
| `ExvModel.simple` | The default. Treats all atoms as equivalent, which makes it fast and a good approximation for quick fits. It has no excluded volume parameter to fit. |
| `ExvModel.fraser` | Each atom carries its own excluded volume, a Gaussian sphere ([Fraser et al. (1978)](https://doi.org/10.1107/S0021889878014296)). This is the model of CRYSOL, FoXS and Pepsi-SAXS. |
| `ExvModel.grid` | The excluded volume is a continuous grid of dummy atoms filling the molecule. |
| `ExvModel.vacuum` | No excluded volume: the atoms with their form factors in vacuum. |

The three models are compared in [Lytje & Pedersen (2025)](https://doi.org/10.1107/S160057672500562X).

## The plain Debye sum
`mol.debye_raw()` evaluates the plain Debye equation, without atomic form factors or the excluded volume contribution. With `form_factors=True`, each atom instead carries its X-ray form factor. Unlike `debye()`, it is not limited to the default q range:
```python {.run}
import numpy as np
import pyausaxs as ausaxs

mol = ausaxs.create_molecule("2epe.pdb")
q = np.linspace(0.01, 10, 2000)
_, I = mol.debye_raw(q)
_, I_ff = mol.debye_raw(q, form_factors=True)
plot(q, {"without atomic form factors": I, "with atomic form factors": I_ff}, logx=True)
```

## Distance histograms and radius of gyration
The distance histogram is the pair-distance distribution the profile is calculated from. It is split into the distances between two atoms, between an atom and a water, and between two waters:
```python {.run}
import pyausaxs as ausaxs

mol = ausaxs.create_molecule("2epe.pdb")
mol.hydrate()
hist = mol.distance_histogram()
hist.truncate()                   # drop the empty bins at large distances
r = hist.bins()                   # distances in Å
p_aa = hist.counts_aa()           # atom-atom; hist.counts() gives all pairs together
p_aw = hist.counts_aw()           # atom-water
p_ww = hist.counts_ww()           # water-water
plot(r, {"atom-atom": p_aa, "atom-water": p_aw, "water-water": p_ww}, logy=False, xlabel="r [Å]", ylabel="p(r)")
print(f"Rg = {mol.Rg():.1f} Å")   # the radius of gyration of the atoms
```

??? info "The scale of the counts"

    The counts are weighted by the scattering power of the atoms. The water counts have an arbitrary scale; multiply them by the fitted hydration shell parameter `cw` from a [fit](fitting.md) to put them on the scale of the atoms.

## SANS profiles
For neutron scattering, switch the radiation before reading the structure. The same structure then gives a different profile, since neutrons see the hydrogens and the solvent differently than X-rays:
```python {.run}
import pyausaxs as ausaxs

q, I_xray = ausaxs.create_molecule("2epe.pdb").debye()   # X-rays, the default

ausaxs.settings.set("radiation", "neutron")
mol = ausaxs.create_molecule("2epe.pdb")
_, I_sans = mol.debye()
plot(q, {"SAXS": I_xray/I_xray[0], "SANS": I_sans/I_sans[0]}, ylabel="I(q)/I(0)")
```
The [SANS application page](../applications/sans.md) shows a complete example, including how to keep the hydrogens of the structure.

## Next steps
- [Fit the profile to data](fitting.md).
- Calculate the profile of every frame of an [MD trajectory](trajectories.md).
- See every option in the [API reference](reference/index.md).
