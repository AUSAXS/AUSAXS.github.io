---
title: Differentiable Debye scattering in Python - AUSAXS
description: "Gradients of the Debye equation with respect to atomic coordinates in pyAUSAXS, for SAXS-driven refinement and machine learning with PyTorch."
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

The gradient is that of the [plain Debye sum](scattering-profiles.md#the-plain-debye-sum), `mol.debye_raw()`: every atom is a point scatterer with its weight, without form factors, hydration shell or excluded volume, so use a molecule without a hydration shell.

??? info "Exact sum or histogram?"

    The gradient is the derivative of the exact sum over all pairs of atoms, while `debye_raw()` calculates the profile from a histogram of the distances. For this example, the difference between the two amounts to an error of about 0.01 Å in every atomic coordinate, far less than the uncertainty in the atom positions of any real structure, so use `debye_raw()` and its gradient together as they are.

??? example "Plotting helper"

    The figures on this page are drawn with this function, so that the examples show only the pyAUSAXS calls. It runs by itself before them.

    ```python {.run .setup}
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.animation import FuncAnimation

    def show(path, x, curves, target, reference, titles=None, label="current", xlabel="q [Å⁻¹]", ylabel="I(q)"):
        """Show points in 3D, and beside them their curve against x. Frame i shows the points path[i], an (n, 3)
        array, and the curve curves[i]; the target points, an (n, 3) array, and their curve, reference, are drawn
        in black in every frame. With one frame, this is a still figure; with more, an animation.
        """
        fig = plt.figure(figsize=(8, 3.6))
        left = fig.add_axes((0, 0, 0.5, 1), projection="3d")
        right = fig.add_axes((0.6, 0.16, 0.37, 0.72))
        lim = np.abs(np.concatenate([*path, target])).max()
        left.plot(*target.T, "o", color="black", alpha=0.25, markersize=3)
        points, = left.plot(*path[0].T, "o", markersize=3)
        left.set(xlim=(-lim, lim), ylim=(-lim, lim), zlim=(-lim, lim), xticklabels=[], yticklabels=[], zticklabels=[])
        right.plot(x, reference, "k--", label="target")
        curve, = right.plot(x, curves[0], label=label)
        right.set(yscale="log", xlabel=xlabel, ylabel=ylabel)
        right.legend(loc="upper right")

        def update(i):
            points.set_data_3d(*path[i].T)
            left.view_init(elev=20, azim=-60 + i)  # turn slowly, which shows the depth
            curve.set_ydata(curves[i])
            if titles:
                right.set_title(titles[i])

        update(0)
        if len(path) == 1:
            plt.show()
            return None
        animation = FuncAnimation(fig, update, frames=len(path), interval=80)
        plt.show()
        return animation
    ```

## Following the gradient
This example moves 60 point scatterers until their profile matches that of a target arrangement. The target is a random cloud of points, drawn in black, and the start is a compact blob:
```python {.run}
import numpy as np
import pyausaxs as ausaxs

rng = np.random.default_rng(1)
q = np.linspace(0.01, 0.5, 50)
weights = np.ones(60)

target = rng.normal(scale=10, size=(60, 3))
_, I_target = ausaxs.create_molecule(*target.T, weights).debye_raw(q)

start = rng.normal(scale=4, size=(60, 3))
mol = ausaxs.create_molecule(*start.T, weights)
_, I_start = mol.debye_raw(q)

show([start], q, [I_start], target, I_target, label="start")
```
The loss compares the two profiles, and the gradient says how to move the points to lower it:
```python {.run .continue}
def loss_and_gradient(x):
    mol.set_coordinates(x.reshape(-1, 3))
    _, I = mol.debye_raw(q)
    r = (I - I_target)/I_target
    v = 2*r/I_target                     # dL/dI for L = sum(r²)
    return np.sum(r**2), mol.debye_raw_vjp(q, v).ravel()

print(f"loss at the start: {loss_and_gradient(start.ravel())[0]:.3g}")
```
Then take small steps downhill along the gradient, and record where the points are and what their profile looks like:
```python {.run .continue}
x = start.ravel().copy()
path, profiles, titles = [], [], []
for step in range(180):
    loss, g = loss_and_gradient(x)
    if step % 6 == 0:                    # one frame every 6 steps
        path.append(x.reshape(-1, 3).copy())
        profiles.append(mol.debye_raw(q)[1])
        titles.append(f"step {step}, loss {loss:.2g}")
    move = 3*g.reshape(-1, 3)
    # no point moves more than 0.2 Å per step, as the gradient is large at the start
    x -= (move*np.minimum(1, 0.2/np.linalg.norm(move, axis=1, keepdims=True))).ravel()

show(path, q, profiles, target, I_target, titles=titles)
```
The points end up with the target's profile, but not in the arrangement of the black points: points that can each move anywhere have far more freedom than a profile can pin down. In practice, the SAXS loss is therefore added as an extra term to a model that already knows what a structure looks like, such as a pretrained structure prediction model like OpenFold; [the PyTorch section](#using-it-in-pytorch) shows how to connect them. The problem is then still underdetermined, but the model moves the atoms in ways that keep the structure reasonable, instead of moving each point on its own.

??? info "How much does a profile determine?"

    Part of the degeneracy cannot be avoided: a profile determines a structure only up to rotations, translations and mirror images. Most of it comes from the freedom of the points. In this example, 50 measured intensity points must pin down 180 coordinates, so many arrangements match the profile equally well.

    Measuring more points does not solve this, as nearby intensity points are strongly correlated. A rough indicator of how much information a profile holds is the number of Shannon channels, $q_\text{max} D_\text{max}/\pi$, which does not grow with finer sampling. For the target here, with $q_\text{max} = 0.5$ Å⁻¹ and $D_\text{max} \approx 56$ Å, it is about 9. It is only a rough indicator, not an exact count of the parameters a profile can determine; noise in the data, for one, lowers it further.

This is not a physical trajectory: the points have no mass or temperature, and nothing but the profile moves them. Gradient descent with small steps just makes the path easy to follow. To refine a structure, pass `loss_and_gradient` to an optimizer such as SciPy's L-BFGS instead, `scipy.optimize.minimize(loss_and_gradient, start.ravel(), jac=True, method="L-BFGS-B")`, which needs far fewer steps.

## Using it in PyTorch
To use the profile in a PyTorch model, for example as an extra loss term when fine-tuning a structure prediction model, wrap it in an `autograd.Function`, with the vector-Jacobian product as its backward pass:
```python
import torch

class DebyeProfile(torch.autograd.Function):
    @staticmethod
    def forward(ctx, coords, mol, q):
        mol.set_coordinates(coords.detach().numpy())
        ctx.mol, ctx.q = mol, q
        _, I = mol.debye_raw(q)
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
