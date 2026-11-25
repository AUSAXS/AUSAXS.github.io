---
title: About AUSAXS - AUSAXS
description: "Why AUSAXS was created, who develops it, and who funds it: an open-source SAXS and SANS engine from Aarhus University and Saarland University."
hide:
  - navigation
---

# About <span class="ausaxs-name"><span class="au">AU</span>SAXS</span>

## Why AUSAXS was created

Almost every structural use of small-angle scattering relies on a *forward model*: a calculation of the profile an atomic model would produce, which can then be compared with the measurement. Validating a single structure, selecting conformations from a molecular dynamics ensemble, rigid-body refinement and integrative modelling all evaluate it thousands to millions of times, so its speed decides what is feasible.

The established programs were built as end-user applications. Each couples the scattering calculation to its own solvent model and fitting procedure, and several are closed source. Developers who need the forward model as one part of a larger method, such as a refinement loop, a shape-modelling tool or a machine-learned structure predictor, therefore often had to write and validate their own.

AUSAXS was written to fill that gap. It is an open-source library that works both as a stand-alone program and as the scattering engine inside other software: [SasView](https://www.sasview.org/) and [Shape2SAS](https://github.com/andreashlarsen/Shape2SAS) already use it to calculate Debye scattering. It started as a tool to [validate electron-microscopy maps](applications/em.md) against SAXS data, and has since grown to cover [SAXS](applications/saxs.md), [SANS](applications/sans.md), [rigid-body refinement](applications/rigid-body-refinement.md), [gradients](pyausaxs/gradients.md) for differentiable refinement, and the wide-angle scattering of [crystals and nanoparticles](applications/crystals.md). See [Why AUSAXS?](why-ausaxs.md) for the principles that shape it.

## Who is behind it

AUSAXS is developed by **Kristian Lytje**, in collaboration with

- **Jan Skov Pedersen**, Department of Chemistry and Interdisciplinary Nanoscience Center (iNANO), Aarhus University, Denmark, and
- **Jochen S. Hub**, Theoretical Physics and Center for Biophysics, Saarland University, Germany.

Bug reports, questions and contributions are welcome on [GitHub](https://github.com/AUSAXS/AUSAXS/issues). The scientific background is described in [our papers](documentation/citing.md).

## Institutions

AUSAXS was started at Aarhus University and is developed today at Saarland University.

<div class="ausaxs-sponsors ausaxs-sponsors--page">
  <a href="https://international.au.dk/" title="Aarhus University">
    <img src="../assets/sponsors/aarhus-university.svg" alt="Aarhus University" style="--logo-scale: 0.68">
  </a>
  <a href="https://www.uni-saarland.de/en/" title="Saarland University">
    <img src="../assets/sponsors/saarland-university.svg" alt="Saarland University">
  </a>
</div>

## Funding

The development of AUSAXS has been funded by

- the [Independent Research Fund Denmark](https://dff.dk/en) (Danmarks Frie Forskningsfond, DFF), grant 1026-00209B, and
- the [Deutsche Forschungsgemeinschaft](https://www.dfg.de/) (DFG, German Research Foundation), grant HU 1971/3-2.
