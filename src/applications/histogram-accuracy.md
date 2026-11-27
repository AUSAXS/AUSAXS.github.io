---
title: Accuracy of the distance histogram - AUSAXS
description: How large the binning error of the AUSAXS distance histogram is compared to the exact Debye sum, how it depends on q, bin width and structure, and when to choose a smaller bin width.
journey: apps
appbar: false
---

# Accuracy of the distance histogram

AUSAXS does not sum the Debye equation pair by pair. As described in [How AUSAXS works](how-it-works.md), it first sorts the pair distances into histograms, and then sums over their bins. Every distance in a bin is thereby treated as if it were the same. This page shows how large the resulting error is, and when it is worth reducing the bin width.

In short: at the default bin width of 0.25 Å, the profile of a biomolecule is within a few tenths of a percent of the exact Debye sum. This is far below the noise of any measurement, and corresponds to moving every atom by only a few hundredths of an ångström. Ordered structures such as crystals and nanoparticles need [weighted bins](#ordered-structures-and-weighted-bins), which AUSAXS switches to automatically, and often a smaller bin width at wide angles.

## How large is the error?

The figure compares the binned profile with the exact Debye sum, with every atom as a point scatterer weighted by its number of electrons. On the left is a small protein, lysozyme, at different bin widths. On the right is a small silver nanoparticle, which is discussed [below](#ordered-structures-and-weighted-bins).

![On the left, the binning error of the lysozyme profile is tiny below q = 0.2 for all bin widths. At the default width of 0.25 Å it is about 0.1 to 0.3% from q = 0.3 to 1. At 0.05 Å it stays below 0.05% up to q = 0.7 and reaches 0.2% at q = 0.9, and at 0.5 Å it grows to about 5% at q = 1. On the right, the profile of the silver nanoparticle with unweighted bins of 0.25 Å is off by several percent from q = 0.4 and by more than 100% beyond q = 0.85. With weighted bins of the same width, the error peaks at 2% near q = 0.5. With weighted bins of 0.05 Å, it stays below 0.5%.](../assets/figures/histogram-accuracy.svg#only-light){ width="100%" }
![On the left, the binning error of the lysozyme profile is tiny below q = 0.2 for all bin widths. At the default width of 0.25 Å it is about 0.1 to 0.3% from q = 0.3 to 1. At 0.05 Å it stays below 0.05% up to q = 0.7 and reaches 0.2% at q = 0.9, and at 0.5 Å it grows to about 5% at q = 1. On the right, the profile of the silver nanoparticle with unweighted bins of 0.25 Å is off by several percent from q = 0.4 and by more than 100% beyond q = 0.85. With weighted bins of the same width, the error peaks at 2% near q = 0.5. With weighted bins of 0.05 Å, it stays below 0.5%.](../assets/figures/histogram-accuracy-dark.svg#only-dark){ width="100%" }

The error vanishes at small $q$, where $\sin(qr)/(qr)$ hardly changes across a bin, and grows with $q$. For two proteins of different sizes, the root-mean-square (and largest) relative error is:

| Bin width | Lysozyme (1 000 atoms), $q \le 0.5$ | $0.5 < q \le 1$ | 85 Å protein (4 400 atoms), $q \le 0.5$ | $0.5 < q \le 1$ |
|-----------|-------------------|-------------------|-------------------|-------------------|
| 0.05 Å    | 0.009% (0.02%)    | 0.13% (0.22%)     | 0.03% (0.07%)     | 0.17% (0.24%)     |
| 0.1 Å     | 0.02% (0.04%)     | 0.43% (0.84%)     | 0.11% (0.20%)     | 0.23% (0.39%)     |
| **0.25 Å**| **0.10% (0.24%)** | **0.22% (0.41%)** | **0.12% (0.29%)** | **0.47% (0.87%)** |
| 0.5 Å     | 0.30% (0.68%)     | 2.7% (5.5%)       | 0.16% (0.31%)     | 2.8% (4.7%)       |

Beyond $q \approx 0.5\ \text{Å}^{-1}$, the error is dominated by the bonded distances. These are sharply peaked at a few values, such as 1.23 Å for C=O and 1.53 Å for C–C, and how well a bin centre represents them depends on where the peaks fall within the bins. The error therefore does not always shrink with the bin width at wide angles: for lysozyme, 0.1 Å happens to be worse than 0.25 Å.

The profile you actually fit includes form factors, the excluded volume and the hydration shell. Compared to the same profile with 0.01 Å bins, the default bin width changes it by about 0.2% (at most 0.55%) up to $q = 0.5$ for both proteins above. For comparison, the relative error of SAXS data beyond $q = 0.2$, where the binning error appears, is usually a percent or more.

??? info "Expressed as an error in the atomic coordinates"

    Another way to judge the binning error is to compare it with the effect of moving the atoms. Adding random displacements with a standard deviation of 0.03 Å to every coordinate of lysozyme changes its exact profile as much as the default binning does. For the larger protein, the equivalent displacement is about 0.08 Å, since random displacements average out over more pairs while the binning error does not.

    Both are well below the uncertainty of atomic positions in an experimental structure, and far below the thermal motion of the atoms in solution. A structure with typical B-factors of 20 Å² has atoms vibrating by 0.5 Å around their mean positions.

## Ordered structures and weighted bins

The distances in a protein are spread out, so the distances within a bin are spread out as well, and the bin centre is a good representative. In a crystal, however, the distances pile up at a few exact values, the lattice distances. A bin centre can then be up to half a bin width off from every distance in the bin, and the error does not average out. For the silver nanoparticle in the figure, unweighted bins of 0.25 Å give a profile that is off by 8% on average already below $q = 0.5$, and wrong by more than a factor of two at wide angles.

_Weighted bins_ fix this by also recording the average distance of the pairs in each bin, and using it in place of the bin centre. For the nanoparticle, this reduces the error at 0.25 Å from 85% to 0.4% on average at $0.5 < q \le 1$. By default, AUSAXS looks at the atoms of each structure and switches to weighted bins if it is ordered, so you rarely need to choose yourself. The `--weighted-bins` option of the command-line tools, or `ausaxs.settings.histogram(weighted_bins=True)` in pyAUSAXS, forces them on.

For proteins, weighted bins are no more accurate at the default width, and for lysozyme slightly less so at wide angles. At 0.05 Å and below, they are 2 to 10 times more accurate.

??? warning "Mixtures of elements"

    A weighted bin stores a single average distance for all pairs in it. In an ordered structure of several elements, the pairs of different elements can sit at slightly different distances within one bin, and are then all placed at their common average. If your structure is an ordered mixture, such as an alloy or an oxide, check the profile at a smaller bin width.

## When to reduce the bin width

For SAXS and SANS of biomolecules, the default of 0.25 Å is accurate enough. Use a smaller bin width when:

- **your structure is ordered** and you need $q$ beyond about 0.5 Å⁻¹, as for [crystals and nanoparticles](crystals.md) and [powder diffraction](powder-diffraction.md). `ausaxs debye` uses 0.05 Å by default for this reason. The same holds for [geometric shapes](../pyausaxs/shapes.md) built on a lattice.
- **you compare with an exact calculation** at wide angles, such as another program or a test of your own, and need agreement better than a few tenths of a percent.

Set the bin width with `--bin-width` for `ausaxs debye`, with `bin_width` in a [settings file](../documentation/cli/fit.md#config-group) for the other tools, or with `ausaxs.settings.histogram(bin_width=0.05)` in pyAUSAXS.

On the CPU, the bin width hardly changes the speed. For a structure of 44 000 atoms on 12 cores, calculating the profile takes 150 ms at any width from 0.5 Å down to 0.05 Å, and 190 ms at 0.01 Å. Weighted bins cost about 60% more. On the [GPU](../getting-started/gpu.md), smaller bin widths can be considerably slower for large particles.

## Checking it yourself

pyAUSAXS includes an exact Debye sum, `ausaxs.unoptimized.debye_exact`, which sums over every pair at every $q$. It is meant for testing only, as it is very slow for large structures. It treats every atom as a point scatterer, so compare it with `debye_raw()`:

```python {.run}
import numpy as np
import pyausaxs as ausaxs

mol = ausaxs.create_molecule("2epe.pdb")
q, I_exact = ausaxs.unoptimized.debye_exact(mol)
for width in (0.25, 0.05):
    ausaxs.settings.histogram(bin_width=width)
    _, I = mol.debye_raw()
    error = np.abs(I/I_exact - 1)
    print(f"bin width {width} Å: largest error {100*error.max():.2f}%")
```

The figure on this page is made by `scripts/build_bin_width_figure.py` in the [repository of this site](https://github.com/AUSAXS/AUSAXS.github.io).
