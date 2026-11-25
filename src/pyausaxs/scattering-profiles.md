---
title: Calculating SAXS profiles in Python - AUSAXS
description: "Calculate SAXS profiles of proteins in Python with pyAUSAXS: hydration shell, excluded volume models, custom q values, distance histograms and Rg."
---

# Calculating SAXS profiles in Python

A molecule's SAXS profile is the scattering of its atoms in vacuum, plus that of its hydration shell, minus that of the solvent it displaces, its excluded volume. The [SAXS application page](../applications/saxs.md) explains the three parts; this page shows how to calculate them with pyAUSAXS.

## The profile of a molecule
```python {.run}
import pyausaxs as ausaxs

mol = ausaxs.create_molecule("2epe.pdb")
mol.hydrate()
q, I = mol.debye()
```
`debye()` returns the profile on the [default q axis](first-steps.md#units-and-q-range), with atomic form factors, the hydration shell and the excluded volume. To evaluate it at other q values, such as those of a measurement, pass them in:
```python {.run}
import numpy as np

q = np.linspace(0.01, 0.4, 200)
_, I = mol.debye(q)
```

## The hydration shell
`mol.hydrate()` places water molecules around the surface of the molecule. Without it, the profile is that of the molecule in vacuum minus its excluded volume. Water molecules in the structure file are used as the hydration shell until `hydrate()` replaces them; `mol.clear_hydration()` removes the shell again.

The hydration shell is placed at random, so each call to `hydrate()` gives a slightly different profile, mostly at high q. For a smooth result, average over several shells:
```python {.run}
profiles = []
for _ in range(20):
    mol.hydrate()
    q, I = mol.debye()
    profiles.append(I)
I_mean = np.mean(profiles, axis=0)
```

The positions of the atoms and waters are available as arrays, e.g. to inspect the shell or write it to a file of your own:
```python {.run}
x, y, z, weights, form_factors = mol.atoms()
wx, wy, wz, wweights = mol.waters()
```

## Excluded volume models
The excluded volume model describes the solvent displaced by the molecule. Choose one with `ausaxs.settings.exv`, before calculating:
```python {.run}
ausaxs.settings.exv(ausaxs.ExvModel.fraser)
q, I = mol.debye()
```

| Model | Description |
|-------|-------------|
| `ExvModel.simple` | The default. Treats all atoms as equivalent, which makes it fast and a good approximation for quick fits. It has no excluded volume parameter to fit. |
| `ExvModel.fraser` | Each atom carries its own excluded volume, a Gaussian sphere ([Fraser et al. 1978](https://doi.org/10.1107/S0021889878014296)). This is the model of CRYSOL, FoXS and Pepsi-SAXS. |
| `ExvModel.grid` | The excluded volume is a continuous grid of dummy atoms filling the molecule. |
| `ExvModel.vacuum` | No excluded volume: the atoms with their form factors in vacuum. |

The three solvent models are compared in the [AUSAXS paper](https://doi.org/10.1107/S160057672500562X). The volume assigned to each atom comes from a table, chosen with `ausaxs.settings.molecule(exv_table=...)`; the default is suited to structures without explicit hydrogens.

## The plain Debye sum
`mol.debye_raw()` evaluates the plain Debye equation, with every atom and water as a point scatterer weighted by its scattering power (for X-rays, its number of electrons), and no excluded volume. With `form_factors=True`, each atom instead carries its X-ray form factor. This is the calculation for [crystals and nanoparticles](../applications/crystals.md), where there is no solvent, and it accepts q values beyond 1 Å⁻¹:
```python {.run}
q = np.linspace(0.01, 10, 2000)
_, I = mol.debye_raw(q, form_factors=True)
```

AUSAXS calculates the profile from a histogram of the distances between atoms, which is much faster than summing over every pair of atoms at every q. For highly ordered structures such as crystals, use a smaller bin width than the default 0.25 Å, e.g. `ausaxs.settings.histogram(bin_width=0.05)`. To check the result against the exact sum over all pairs, use `ausaxs.unoptimized.debye_exact(mol, q)`; it is far slower, and only meant for testing.

## Distance histograms and radius of gyration
The distance histogram is the pair-distance distribution the profile is calculated from. It is split into the distances between two atoms, between an atom and a water, and between two waters:
```python {.run}
hist = mol.distance_histogram()
hist.truncate()                   # drop the empty bins at large distances
r = hist.bins()                   # distances in Å
p_total = hist.counts()           # all pairs
p_aa = hist.counts_aa()           # atom-atom
p_aw = hist.counts_aw()           # atom-water
p_ww = hist.counts_ww()           # water-water
```
The counts are weighted by the scattering power of the atoms. The water counts have an arbitrary scale; multiply them by the fitted hydration shell parameter `cw` from a [fit](fitting.md) to put them on the scale of the atoms.

`mol.Rg()` returns the radius of gyration of the atoms in Å.

## SANS profiles
For neutron scattering, switch the radiation before reading the structure:
```python {.run}
ausaxs.settings.set("radiation", "neutron")
mol = ausaxs.create_molecule("2epe.pdb")
```
The [SANS application page](../applications/sans.md) shows a complete example, including how to keep the hydrogens of the structure.

## Next steps
- [Fit the profile to data](fitting.md).
- Calculate the profile of every frame of an [MD trajectory](trajectories.md).
- See every option in the [API reference](reference/index.md).
