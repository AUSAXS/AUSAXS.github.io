---
title: Differentiable Debye scattering in Python - AUSAXS
description: "Gradients of the Debye equation with respect to atomic coordinates in pyAUSAXS, for SAXS-driven refinement with SciPy and machine learning with PyTorch."
---

# Gradients of the Debye equation

To refine a structure against SAXS data, or to train a model whose loss includes a scattering profile, you need to know how the profile changes when the atoms move. pyAUSAXS calculates this gradient directly, as a vector-Jacobian product: given how your loss $L$ depends on the intensity, $v(q) = \partial L/\partial I(q)$, it returns how the loss depends on the coordinates,
$$
\frac{\partial L}{\partial \mathbf{r}_i} = \sum_q v(q) \, \frac{\partial I(q)}{\partial \mathbf{r}_i},
$$
in one call, without forming the full Jacobian.

```python
g = mol.debye_raw_vjp(q, v)    # (n_atoms, 3) array, in the order of mol.atoms()
```

The gradient is that of the [plain Debye sum](scattering-profiles.md#the-plain-debye-sum), `mol.debye_raw()`: every atom is a point scatterer with its weight, without form factors, hydration shell or excluded volume. It is the derivative of the exact sum over all pairs of atoms, not of the histogram approximation that `debye_raw()` uses to calculate the profile itself. The two profiles agree closely, but for a consistent pair, calculate the profile with `ausaxs.unoptimized.debye_exact(mol, q)`, which is slower. Use a molecule without a hydration shell.

## Refining coordinates with SciPy
This example moves 60 point scatterers until their profile matches a target, with the gradient passed to SciPy's L-BFGS optimizer:
```python
import numpy as np
import pyausaxs as ausaxs
from scipy.optimize import minimize

rng = np.random.default_rng(1)
q = np.linspace(0.01, 0.5, 50)
weights = np.ones(60)

# the target: the profile of a random arrangement of 60 points
target = rng.normal(scale=10, size=(60, 3))
_, I_target = ausaxs.unoptimized.debye_exact(ausaxs.create_molecule(*target.T, weights), q)

# start from a distorted copy, and move it back
start = target + rng.normal(scale=3, size=target.shape)
mol = ausaxs.create_molecule(*start.T, weights)

def loss_and_gradient(x):
    mol.set_coordinates(x.reshape(-1, 3))
    _, I = ausaxs.unoptimized.debye_exact(mol, q)
    r = (I - I_target)/I_target
    v = 2*r/I_target                     # dL/dI for L = sum(r²)
    return np.sum(r**2), mol.debye_raw_vjp(q, v).ravel()

result = minimize(loss_and_gradient, start.ravel(), jac=True, method="L-BFGS-B")
print(f"loss: {loss_and_gradient(start.ravel())[0]:.3g} -> {result.fun:.3g}")
```
A profile determines a structure only up to rotations, translations and mirror images, so the refined points match the target's profile, not necessarily its coordinates.

## Using it in PyTorch
To use the profile in a PyTorch model, wrap it in an `autograd.Function`, with the vector-Jacobian product as its backward pass:
```python
import torch

class DebyeProfile(torch.autograd.Function):
    @staticmethod
    def forward(ctx, coords, mol, q):
        mol.set_coordinates(coords.detach().numpy())
        ctx.mol, ctx.q = mol, q
        _, I = ausaxs.unoptimized.debye_exact(mol, q)
        return torch.from_numpy(I)

    @staticmethod
    def backward(ctx, grad_I):
        g = ctx.mol.debye_raw_vjp(ctx.q, grad_I.numpy())
        return torch.from_numpy(g), None, None

coords = torch.tensor(start, requires_grad=True)
I = DebyeProfile.apply(coords, mol, q)
loss = torch.sum(((I - torch.from_numpy(I_target))/torch.from_numpy(I_target))**2)
loss.backward()                          # coords.grad now holds dL/dr
```
The calculation runs on the CPU in double precision, so move tensors from the GPU with `.cpu()` and convert them with `.double()` first.

## Next steps
- Calculate the [full SAXS profile](scattering-profiles.md), with hydration shell and excluded volume, of the refined structure.
- For refinement of whole domains against data, see [rigid-body refinement](../applications/rigid-body-refinement.md).
