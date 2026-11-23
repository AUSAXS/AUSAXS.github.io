---
title: SAXS profiles from MD trajectories - AUSAXS
description: "Calculate SAXS profiles from molecular dynamics trajectories and structural ensembles in Python with pyAUSAXS and MDAnalysis, frame by frame."
---

# SAXS profiles from MD trajectories and ensembles

A molecular dynamics simulation gives thousands of conformations of a molecule, and the measured SAXS profile is their average. With pyAUSAXS, you read the structure once and update its coordinates for every frame, so each frame only costs the calculation itself.

## Frame by frame
`mol.set_coordinates` replaces the coordinates of the atoms, and keeps their form factors. After moving the atoms, call `hydrate()` again, so the hydration shell follows the new conformation:
```python
import numpy as np
import pyausaxs as ausaxs
import MDAnalysis as mda

u = mda.Universe("topology.pdb", "trajectory.xtc")
protein = u.select_atoms("protein and not name H*")
protein.write("frame0.pdb")                 # the atoms AUSAXS reads, in the same order

mol = ausaxs.create_molecule("frame0.pdb")
assert len(mol.atoms()[0]) == protein.n_atoms

profiles = []
for ts in u.trajectory:
    mol.set_coordinates(protein.positions)  # an (n_atoms, 3) array in Å
    mol.hydrate()
    q, I = mol.debye()
    profiles.append(I)
I_mean = np.mean(profiles, axis=0)
```
The average profile can then be [fitted to data](fitting.md) like that of a single structure, e.g. through `ausaxs.create_datafile` and `ausaxs.manual_fit`, or by comparing `I_mean` with the data yourself.

The example uses [MDAnalysis](https://www.mdanalysis.org/), but any library that gives the coordinates as an array works. MDAnalysis uses Å, like AUSAXS; [MDTraj](https://www.mdtraj.org/) uses nm, so multiply its coordinates by 10.

## Matching the atoms
`set_coordinates` expects one row per atom of the molecule, in the order of `mol.atoms()`. That is the order of the structure file, except that AUSAXS leaves out:
- **water molecules**, which are used as the [hydration shell](scattering-profiles.md#the-hydration-shell) instead, and
- **explicit hydrogens**, since AUSAXS adds their scattering to the heavy atoms they are bound to. To use the hydrogens of the file instead, set `ausaxs.settings.set("keep_hydrogens", "true")` before reading it.

The simplest way to get the order right is to write the first frame of your selection to a PDB file, and read the molecule from it, as in the example above. The `assert` then catches any mismatch.

## Ensembles of structures
For an ensemble stored as separate files, e.g. from a structure prediction or a set of NMR models, read each file as its own molecule:
```python
from pathlib import Path

profiles = []
for path in sorted(Path("ensemble").glob("*.pdb")):
    mol = ausaxs.create_molecule(str(path))
    mol.hydrate()
    q, I = mol.debye()
    profiles.append(I)
```
All profiles share the same [q axis](first-steps.md#units-and-q-range), so they can be averaged directly, or weighted to fit the data.

## Coordinates without a structure file
`ausaxs.create_molecule(x, y, z, weights)` creates a molecule directly from arrays: the coordinates in Å, and the scattering power of each point. Such a molecule has no atom types, and so no form factors; calculate its profile with the [plain Debye sum](scattering-profiles.md#the-plain-debye-sum), `mol.debye_raw()`. This suits coarse-grained models, where each point stands for a residue or a bead.

## Next steps
- Fit the averaged profile with a [custom objective](fitting.md#custom-fits-and-objectives).
- Use the [gradient of the Debye equation](gradients.md) to steer a structure towards the data.
