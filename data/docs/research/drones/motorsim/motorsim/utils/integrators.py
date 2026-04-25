"""Batched ODE integrators (differentiable)."""

import torch
from torch import Tensor
from typing import Callable


def euler_step(f: Callable, state: Tensor, dt: float) -> Tensor:
    return state + dt * f(state)


def rk4_step(f: Callable, state: Tensor, dt: float) -> Tensor:
    k1 = f(state)
    k2 = f(state + 0.5 * dt * k1)
    k3 = f(state + 0.5 * dt * k2)
    k4 = f(state + dt * k3)
    return state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
