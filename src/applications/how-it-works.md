---
title: How AUSAXS works - AUSAXS
description: How AUSAXS calculates scattering profiles with the Debye equation, by sorting all pair distances into histograms on the CPU or GPU, and why this makes fitting fast.
journey: apps
appbar: false
---

# How <span class="ausaxs-name"><span class="au">AU</span>SAXS</span> works

Every application of AUSAXS runs on the same engine. It receives a list of scatterers, each with a position and a form factor $f(q)$ describing how strongly it scatters at each $q$, and calculates their scattering profile with the Debye equation:

$$
I(q) = \sum_i \sum_j f_i(q) f_j(q) \frac{\sin(q r_{ij})}{q r_{ij}}
$$

where $r_{ij}$ is the distance between scatterers $i$ and $j$. The applications differ in what they feed into the engine. For [SAXS](saxs.md), the scatterers are atoms and water molecules with their X-ray form factors; for [SANS](sans.md), they have neutron scattering lengths instead. This page describes the engine itself. Each application page explains what it puts in.

## Counting distances instead of summing sines

The Debye equation has a term for every pair of scatterers. A protein with 10 000 atoms has 50 million pairs, and summing a sine for each of them at every $q$ would be slow.

However, the sine only depends on the distance between the two scatterers, and the form factors only on what kind of scatterers they are. AUSAXS therefore first sorts all pair distances into histograms with bins 0.25 Å wide, one histogram for each combination of scatterer types, such as carbon–oxygen or atom–water. These are the familiar pair distance distributions $p(r)$, and the intensity follows from a much shorter sum over their bins:

$$
I(q) = \sum_{A,B} f_A(q) f_B(q) \sum_k p_{AB}(r_k) \frac{\sin(q r_k)}{q r_k}
$$

where $A$ and $B$ run over the scatterer types. As there are only a few thousand bins and a dozen or so types, this sum is short however many atoms there are. The expensive part, counting the distances, is done only once.

??? info "Weighted bins for ordered structures"

    Placing every distance in the centre of its bin is accurate for disordered molecules like proteins. The distances in an ordered structure like a crystal, however, pile up at a few exact values, and rounding them to the bin centres distorts the profile at wide angles. AUSAXS detects such structures and switches to _weighted bins_, which also record the average distance of their contents and use it in place of the bin centre ([Lytje & Pedersen, 2025](https://doi.org/10.1107/S160057672500562X)).

## Making the counting fast

Counting the distances takes nearly all of the time. AUSAXS therefore spreads it over every core of your processor, and makes each core compare several pairs at once. With the optional [GPU driver](../getting-started/gpu.md) installed, the counting runs on your graphics card instead, while everything else stays the same.

??? info "The details"

    - **Compact data.** The positions and weights are first copied into four tightly packed lists of numbers: x, y, z and the weight. The calculation reads nothing else, so all the data it needs stays in the fast memory of the processor.
    - **Many pairs at once.** Modern processors can perform the same calculation on several numbers with a single instruction. AUSAXS compares each atom with 4, 8 or 16 others at once, depending on what your processor supports.
    - **Every core.** The atoms are split into chunks, each counted by its own processor core into its own copy of the histogram. The copies are added together at the end, so the cores never have to wait for each other.
    - **Shuffled atoms.** Neighbouring atoms in a structure file are usually bonded, so they have similar distances to every other atom, and land in the same bin one after another. The processor then has to finish one addition before it can start the next. For molecules of normal size, AUSAXS shuffles the atoms first to spread the additions over many bins. This changes nothing but the speed.

## Why fitting is fast

Each histogram is turned into its own partial profile, and the partial profiles are only added together at the very end. For a protein with a hydration shell, they can be grouped into the atom–atom, atom–water and water–water profiles, which you can see in the `profiles` plot written by `ausaxs saxs`.

The fitted parameters only scale these partial profiles. For example, the density of the hydration shell is set by a factor $c$ on every water molecule:

$$
I(q) = I_{aa}(q) + c\, I_{aw}(q) + c^2 I_{ww}(q)
$$

Trying a new value of $c$ therefore only adds the same three curves with new factors, without counting a single distance again. During the fit, $c$ is optimized by a minimizer, and for each value it tries, the overall scaling $a$ and background $b$ of $a I(q) + b$ are found exactly by linear least squares. A full fit thus costs little more than calculating the profile once.

??? info "From histograms to the profile"

    The values of $\sin(q r)/(q r)$ for every bin and every $q$ are calculated once and stored in a table, so transforming a histogram only multiplies and adds numbers. This step is also split over all processor cores. The profile is calculated on a fixed set of $q$ values, and then interpolated to the $q$ values of your measurement.

??? info "The `simple` approximation"

    The default excluded volume model for SAXS, `simple`, approximates the form factors to save time. All atoms are given the same form factor shape, scaled by the _effective charge_ of each atom: its electrons minus those of the buffer it displaces. A single atom–atom histogram is then enough, with each pair counted with the product of the two effective charges. See the [SAXS page](saxs.md#how-it-works) for how the displaced buffer is found.

For a deeper description of the methods, see [Lytje & Pedersen (2025)](https://doi.org/10.1107/S160057672500562X), and for the physics of solution scattering, [Lytje, Pedersen & Hub (2026)](https://doi.org/10.1088/1361-6633/aead1d). And as AUSAXS is [open source](https://github.com/AUSAXS/AUSAXS), every detail can be checked in the code.
