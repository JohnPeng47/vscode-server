"""Battery voltage model.

Supports linear decay or a simple LiPo discharge curve.
Voltage drops based on cumulative current draw (coulomb counting).
"""

import torch
from torch import Tensor


class BatteryModel:
    def __init__(
        self,
        device: str = "cpu",
        n_cells: int = 4,
        capacity_ah: float = 1.3,       # battery capacity [Ah]
        internal_r: float = 0.02,       # internal resistance per cell [Ω]
        v_full: float = 4.2,            # per-cell voltage when full [V]
        v_empty: float = 3.3,           # per-cell voltage at cutoff [V]
    ):
        self.device = device
        self.n_cells = n_cells
        self.capacity_ah = capacity_ah
        self.internal_r = internal_r
        self.v_full = v_full
        self.v_empty = v_empty
        self.capacity_as = capacity_ah * 3600.0  # convert to amp-seconds

    def initial_state(self, batch_size: int) -> dict[str, Tensor]:
        return {
            "soc": torch.ones(batch_size, 1, device=self.device),  # state of charge [0,1]
        }

    def step(
        self,
        total_current: Tensor,
        state: dict[str, Tensor],
        dt: float,
    ) -> tuple[Tensor, dict[str, Tensor]]:
        """Update battery voltage based on current draw.

        Args:
            total_current: [batch, 1] sum of all motor currents [A]
            state: {"soc": [batch, 1]}
            dt: timestep [s]
        Returns:
            v_bat [batch, 1], new_state
        """
        soc = state["soc"]

        # Coulomb counting: dSOC = -I·dt / capacity
        soc_new = (soc - total_current * dt / self.capacity_as).clamp(0, 1)

        # Open-circuit voltage: linear interpolation between full and empty
        v_oc = self.n_cells * (self.v_empty + soc_new * (self.v_full - self.v_empty))

        # Voltage sag under load: V = V_oc - I·R_internal
        v_bat = (v_oc - total_current * self.internal_r * self.n_cells).clamp(min=0.0)

        return v_bat, {"soc": soc_new}
