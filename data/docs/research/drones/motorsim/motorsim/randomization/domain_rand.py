"""Domain randomization for motor and vehicle parameters."""

import torch
from torch import Tensor
from dataclasses import dataclass


@dataclass
class DRConfig:
    """Ranges for domain randomization. Each is (nominal, lo, hi)."""
    mass: tuple[float, float, float] = (0.8, 0.6, 1.0)
    R: tuple[float, float, float] = (0.065, 0.045, 0.085)
    K_e: tuple[float, float, float] = (0.00374, 0.003, 0.0045)
    J: tuple[float, float, float] = (1.5e-5, 1.0e-5, 2.0e-5)
    k_f: tuple[float, float, float] = (2.5e-7, 2.0e-7, 3.0e-7)
    k_tau: tuple[float, float, float] = (5.0e-9, 3.5e-9, 6.5e-9)
    v_bat_full: tuple[float, float, float] = (16.8, 15.5, 17.0)
    capacity_ah: tuple[float, float, float] = (1.3, 1.0, 1.6)


def sample_params(
    cfg: DRConfig, batch_size: int, device: str = "cpu"
) -> dict[str, Tensor]:
    """Sample randomized parameters for a batch of environments."""
    params = {}
    for field_name in cfg.__dataclass_fields__:
        nom, lo, hi = getattr(cfg, field_name)
        params[field_name] = torch.empty(batch_size, 1, device=device).uniform_(lo, hi)
    return params
