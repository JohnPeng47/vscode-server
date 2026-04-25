"""Motor model interface."""

from abc import ABC, abstractmethod
import torch
from torch import Tensor, nn


class MotorModel(nn.Module, ABC):
    """All motor models implement this interface.

    Convention:
        cmd:   duty cycle per motor, [batch, n_motors], range [0, 1]
        state: dict of tensors, contents vary by tier
        dt:    integrator timestep in seconds
    Returns:
        thrust [batch, n_motors], torque [batch, n_motors], new_state
    """

    def __init__(self, n_motors: int, device: str):
        super().__init__()
        self.n_motors = n_motors
        self._device = device

    @abstractmethod
    def forward(
        self, cmd: Tensor, state: dict[str, Tensor], dt: float
    ) -> tuple[Tensor, Tensor, dict[str, Tensor]]:
        ...

    @abstractmethod
    def initial_state(self, batch_size: int) -> dict[str, Tensor]:
        ...
