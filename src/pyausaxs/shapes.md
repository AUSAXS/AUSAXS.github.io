---
title: Scattering from geometric shapes in Python - AUSAXS
description: "Calculate the small-angle scattering of spheres, cylinders, ellipsoids and any homogeneous shape in Python with pyAUSAXS, by filling the shape with a lattice."
---

# Scattering from geometric shapes

pyAUSAXS calculates the scattering of any homogeneous body you can describe with a function. The body is filled with the cells of a cubic lattice, each with a Gaussian form factor, the same representation as the grid excluded volume model. This works for shapes without an analytical form factor, and for combinations of shapes.

## A sphere
Describe the shape by a function of the coordinates in Å that is true inside it, and give the half-width of the box to search:
```python
import numpy as np
import pyausaxs as ausaxs

R = 30
sphere = ausaxs.shape.lattice(lambda x, y, z: x**2 + y**2 + z**2 <= R**2, extent=R, spacing=1)
q, I = sphere.debye()
print(len(sphere), sphere.volume)    # number of cells, and their total volume in Å³
```
The function is called once on whole arrays of coordinates, so write it with NumPy operations. `debye()` uses the [default q axis](first-steps.md#units-and-q-range), or takes q values of your own. The intensity is on an absolute scale, with unit density: at q = 0 it equals the volume squared. For a sphere, it agrees with the exact form factor:
```python
x = q*R
I_exact = (4*np.pi*R**3*(np.sin(x) - x*np.cos(x))/x**3)**2
```

## Other shapes
Any condition that NumPy can evaluate describes a shape. The box is searched from `-extent` to `extent` along each axis; give one extent per axis for elongated shapes:
```python
# a cylinder of radius 20 Å and length 100 Å along z
cylinder = ausaxs.shape.lattice(lambda x, y, z: (x**2 + y**2 <= 20**2) & (np.abs(z) <= 50), extent=(20, 20, 50))

# an ellipsoid with semi-axes 20, 30 and 50 Å
ellipsoid = ausaxs.shape.lattice(lambda x, y, z: (x/20)**2 + (y/30)**2 + (z/50)**2 <= 1, extent=(20, 30, 50))

# a hollow sphere: a shell between 25 and 30 Å
shell = ausaxs.shape.lattice(lambda x, y, z: (x**2 + y**2 + z**2 <= 30**2) & (x**2 + y**2 + z**2 >= 25**2), extent=30)
```

## Choosing the lattice spacing
A smaller spacing follows the surface of the body more closely, and gives a better profile at high q, at the cost of more cells. The distances between the cells are counted with a fast Fourier transform, so even millions of cells are fast: a sphere of radius 30 Å at a spacing of 0.25 Å has about 7 million cells, and takes a few seconds. As a rule, keep the spacing well below the smallest feature of the shape, and check that halving it does not change the profile in the q range you need.

For your own lattices, e.g. cells read from a voxel map, create the body directly from the cell centres, which must lie on one lattice with the given spacing:
```python
cells = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
body = ausaxs.shape.Lattice(cells, spacing=1)
q, I = body.debye()
```

## Next steps
- For atomic structures instead of homogeneous bodies, see [SAXS profiles](scattering-profiles.md).
- The [homogeneous shapes example](https://github.com/AUSAXS/pyAUSAXS/blob/master/examples/8_homogeneous_shapes.py) compares lattices of different spacings with the exact sphere.
