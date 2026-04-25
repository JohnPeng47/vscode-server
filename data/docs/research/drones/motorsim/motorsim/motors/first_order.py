"""Tier 1: First-order motor lag on angular velocity.

    dΩ/dt = (Ω_cmd - Ω) / τ
    thrust = k_f · Ω²
    torque = k_τ · Ω²
"""

import torch
from torch import Tensor

from .base import MotorModel


class FirstOrderMotor(MotorModel):
    def __init__(
        self,
        n_motors: int = 4,
        device: str = "cpu",
        tau: float = 0.025,           # motor time constant [s]
        omega_max: float = 2500.0,    # max rotor speed [rad/s]
        k_f: float = 7.5e-7,         # thrust coefficient [N·s²/rad²]
        k_tau: float = 1.2e-8,       # drag torque coefficient [N·m·s²/rad²]
    ):
        super().__init__(n_motors, device)
        self.tau = tau
        self.omega_max = omega_max
        self.k_f = k_f
        self.k_tau = k_tau

    def initial_state(self, batch_size: int) -> dict[str, Tensor]:
        return {
            "omega": torch.zeros(batch_size, self.n_motors, device=self._device),
        }

    def forward(
        self, cmd: Tensor, state: dict[str, Tensor], dt: float
    ) -> tuple[Tensor, Tensor, dict[str, Tensor]]:
        omega = state["omega"]
        omega_cmd = cmd.clamp(0, 1) * self.omega_max

        # Exact discrete first-order filter (same as Flightmare)
        c = torch.tensor((-dt / self.tau), device=omega.device).exp()
        omega_new = c * omega + (1 - c) * omega_cmd

        thrust = self.k_f * omega_new**2
        torque = self.k_tau * omega_new**2

        return thrust, torque, {"omega": omega_new}
