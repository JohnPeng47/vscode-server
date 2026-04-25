"""Reward function registry."""

from torch import Tensor
from typing import Callable

RewardFn = Callable[..., Tensor]
REWARDS: dict[str, RewardFn] = {}


def register_reward(name: str):
    def decorator(fn: RewardFn) -> RewardFn:
        REWARDS[name] = fn
        return fn
    return decorator
