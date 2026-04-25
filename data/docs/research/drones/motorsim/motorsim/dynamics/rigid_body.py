"""1-DOF vertical rigid body dynamics for hover task.

State: [z, vz]
    z:  altitude [m]
    vz: vertical velocity [m/s]

Physics:
    dz/dt  = vz
    dvz/dt = (sum_thrust / mass) - g
"""

import torch
from torch import Tensor


class VerticalBody:
    def __init__(
        self,
        device: str = "cpu",
        mass: float = 0.8,       # total vehicle mass [kg]
        gravity: float = 9.81,
    ):
        self.device = device
        self.mass = mass
        self.gravity = gravity

    def initial_state(self, batch_size: int) -> dict[str, Tensor]:
        return {
            "z": torch.zeros(batch_size, 1, device=self.device),
            "vz": torch.zeros(batch_size, 1, device=self.device),
        }

    def step(
        self,
        total_thrust: Tensor,
        state: dict[str, Tensor],
        dt: float,
    ) -> dict[str, Tensor]:
        """Integrate vertical dynamics.

        Args:
            total_thrust: [batch, 1] sum of all motor thrusts [N]
            state: {"z": [batch,1], "vz": [batch,1]}
            dt: timestep [s]
        """
        z = state["z"]
        vz = state["vz"]

        acc = total_thrust / self.mass - self.gravity
        vz_new = vz + dt * acc
        z_new = z + dt * vz_new

        return {"z": z_new, "vz": vz_new}
