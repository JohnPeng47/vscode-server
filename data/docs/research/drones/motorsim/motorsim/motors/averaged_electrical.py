"""Tier 2-avg: Averaged electrical motor model with CCM/DCM transition.

    J · dΩ/dt = Kₜ · ī(d, Ω, V_bat) - k_τ · Ω²
    ī = averaged current (piecewise: CCM vs DCM)

    In CCM (continuous conduction):
        ī = (d · V_bat - Kₑ · Ω) / R

    In DCM (discontinuous conduction), current decays to zero during
    off-period. The average current is reduced:
        ī = (d · V_bat - Kₑ · Ω)² / (2 · L · f_pwm · (V_bat - Kₑ · Ω))
        (when d·V_bat > Kₑ·Ω, otherwise ī = 0 — motor is in regeneration)

    The CCM/DCM boundary occurs when the minimum current during a PWM
    cycle reaches zero: d_crit = 1 - (Kₑ·Ω) / V_bat + (L·f_pwm·R) / V_bat²
    Simplified: we check if the CCM current would be positive and above
    a threshold set by the ripple current.

    V_applied = d · V_bat   (duty cycle entry point)
"""

import torch
from torch import Tensor

from .base import MotorModel


class AveragedElectricalMotor(MotorModel):
    def __init__(
        self,
        n_motors: int = 4,
        device: str = "cpu",
        # Electrical parameters
        R: float = 0.065,             # winding resistance [Ω]
        L: float = 10e-6,            # winding inductance [H]
        K_e: float = 0.00374,        # back-EMF constant [V·s/rad]
        K_t: float = 0.00374,        # torque constant [N·m/A] (= K_e for ideal)
        # Mechanical parameters
        J: float = 1.5e-5,           # rotor + prop inertia [kg·m²]
        k_tau: float = 1.2e-8,       # prop aero drag torque [N·m·s²/rad²]
        omega_max: float = 2500.0,    # max rotor speed [rad/s]
        # ESC parameters
        f_pwm: float = 24000.0,      # PWM frequency [Hz]
        # Prop parameters
        k_f: float = 7.5e-7,         # thrust coefficient [N·s²/rad²]
    ):
        super().__init__(n_motors, device)
        self.R = R
        self.L = L
        self.K_e = K_e
        self.K_t = K_t
        self.J = J
        self.k_tau = k_tau
        self.omega_max = omega_max
        self.f_pwm = f_pwm
        self.k_f = k_f

    def initial_state(self, batch_size: int) -> dict[str, Tensor]:
        return {
            "omega": torch.zeros(batch_size, self.n_motors, device=self._device),
        }

    def _averaged_current(
        self, duty: Tensor, omega: Tensor, v_bat: Tensor
    ) -> Tensor:
        """Compute averaged motor current with CCM/DCM piecewise model.

        Args:
            duty:  [batch, n_motors] duty cycle in [0, 1]
            omega: [batch, n_motors] rotor angular velocity [rad/s]
            v_bat: [batch, 1] battery voltage [V]
        Returns:
            i_avg: [batch, n_motors] averaged current [A]
        """
        back_emf = self.K_e * omega
        v_applied = duty * v_bat

        # CCM current: (d·V - Kₑ·Ω) / R
        i_ccm = (v_applied - back_emf) / self.R

        # DCM current: reduced due to current going to zero each cycle
        # i_dcm = (v_applied - back_emf)² / (2·L·f_pwm·R·v_bat)
        # Guard against division by zero when v_bat is very small
        v_safe = v_bat.clamp(min=0.1)
        numerator = (v_applied - back_emf).clamp(min=0.0) ** 2
        i_dcm = numerator / (2.0 * self.L * self.f_pwm * self.R)

        # CCM/DCM boundary: CCM when i_ccm > ripple_half
        # Ripple current amplitude: ΔI = (V_bat - Kₑ·Ω) · d / (L · f_pwm)
        ripple_half = ((v_bat - back_emf).clamp(min=0.0) * duty) / (
            2.0 * self.L * self.f_pwm
        )

        # Select regime: CCM if average current exceeds half the ripple
        # (i.e., current never reaches zero during off-period)
        in_ccm = i_ccm > ripple_half
        i_avg = torch.where(in_ccm, i_ccm, i_dcm)

        # Current can't be negative (no regenerative braking in this model)
        return i_avg.clamp(min=0.0)

    def forward(
        self, cmd: Tensor, state: dict[str, Tensor], dt: float, v_bat: Tensor | None = None
    ) -> tuple[Tensor, Tensor, dict[str, Tensor]]:
        """
        Args:
            cmd:   duty cycle [batch, n_motors] in [0, 1]
            state: {"omega": [batch, n_motors]}
            dt:    timestep [s]
            v_bat: battery voltage [batch, 1]. If None, uses nominal 14.8V.
        """
        omega = state["omega"]
        duty = cmd.clamp(0, 1)

        if v_bat is None:
            v_bat = torch.full(
                (omega.shape[0], 1), 14.8, device=omega.device
            )

        # Averaged current from piecewise CCM/DCM model
        i_avg = self._averaged_current(duty, omega, v_bat)

        # Motor torque - prop drag torque
        tau_motor = self.K_t * i_avg
        tau_drag = self.k_tau * omega**2
        tau_net = tau_motor - tau_drag

        # Integrate: J · dΩ/dt = τ_net
        omega_new = (omega + (dt / self.J) * tau_net).clamp(min=0.0, max=self.omega_max)

        thrust = self.k_f * omega_new**2
        torque = self.k_tau * omega_new**2

        return thrust, torque, {"omega": omega_new}
