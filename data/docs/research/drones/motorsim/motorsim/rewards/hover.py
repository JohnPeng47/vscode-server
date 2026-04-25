"""Hover reward functions."""

import torch
from torch import Tensor
from .registry import register_reward


@register_reward("hover")
def hover_reward(
    z: Tensor,
    vz: Tensor,
    action: Tensor,
    prev_action: Tensor,
    z_target: float = 1.0,
    alpha: float = 1.0,
    beta: float = 0.1,
    gamma: float = 0.01,
) -> Tensor:
    """Reward for maintaining target altitude.

    Terms:
        -alpha * (z - z_target)²    altitude error
        -beta  * vz²                velocity penalty (stability)
        -gamma * (a - a_prev)²      action smoothness
    """
    alt_err = -alpha * (z - z_target) ** 2
    vel_pen = -beta * vz**2
    smooth = -gamma * ((action - prev_action) ** 2).sum(dim=-1, keepdim=True)
    return alt_err + vel_pen + smooth


@register_reward("hover_alive")
def hover_alive_reward(
    z: Tensor,
    vz: Tensor,
    action: Tensor,
    prev_action: Tensor,
    z_target: float = 1.0,
    alpha: float = 1.0,
    beta: float = 0.1,
    gamma: float = 0.01,
    alive_bonus: float = 0.1,
) -> Tensor:
    """Hover reward with a per-step alive bonus to encourage survival."""
    return hover_reward(z, vz, action, prev_action, z_target, alpha, beta, gamma) + alive_bonus
