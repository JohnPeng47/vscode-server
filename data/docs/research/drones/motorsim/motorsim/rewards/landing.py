"""Landing reward functions."""

import torch
from torch import Tensor
from .registry import register_reward


@register_reward("soft_landing")
def soft_landing_reward(
    z: Tensor,
    vz: Tensor,
    action: Tensor,
    prev_action: Tensor,
    vz_threshold: float = 0.1,
    alpha: float = 1.0,
    beta: float = 0.5,
    gamma: float = 0.01,
) -> Tensor:
    """Reward for descending to ground with low velocity.

    Terms:
        -alpha * z²                 get close to ground
        -beta  * vz²                penalize high descent speed
        +bonus when z < 0.05 and |vz| < threshold
    """
    alt_pen = -alpha * z**2
    vel_pen = -beta * vz**2
    smooth = -gamma * ((action - prev_action) ** 2).sum(dim=-1, keepdim=True)
    landed = ((z < 0.05) & (vz.abs() < vz_threshold)).float() * 10.0
    return alt_pen + vel_pen + smooth + landed
