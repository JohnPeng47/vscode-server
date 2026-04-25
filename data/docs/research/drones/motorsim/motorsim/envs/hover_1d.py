"""1-DOF hover environment with optional battery drain.

Observation: [z, vz, omega_mean, v_bat, z_target]
Action:      [duty_cycle] (single scalar, applied equally to all motors)
"""

import gymnasium as gym
import numpy as np
import torch
from torch import Tensor
from gymnasium import spaces

from ..motors import make_motor, MotorModel
from ..dynamics.battery import BatteryModel
from ..dynamics.rigid_body import VerticalBody
from ..rewards import REWARDS
from ..utils.logging import EnvLogger


class Hover1DEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        num_envs: int = 64,
        device: str = "cpu",
        motor_model: str = "averaged_electrical",
        reward_fn: str = "hover_alive",
        dt: float = 0.001,               # physics timestep [s]
        policy_freq: float = 100.0,       # policy query rate [Hz]
        max_episode_time: float = 30.0,   # seconds of simulated time
        z_target: float = 1.0,
        z_max: float = 5.0,
        vz_max: float = 10.0,
        # Vehicle params
        mass: float = 0.8,
        n_motors: int = 4,
        # Motor params (passed through to motor model)
        motor_kwargs: dict | None = None,
        # Battery params
        battery_kwargs: dict | None = None,
        enable_battery_drain: bool = True,
        # Termination penalty
        crash_penalty: float = -10.0,
    ):
        super().__init__()
        self.num_envs = num_envs
        self.device = device
        self.dt = dt
        self.substeps = max(1, int(1.0 / (policy_freq * dt)))
        self.max_steps = int(max_episode_time * policy_freq)
        self.z_target = z_target
        self.z_max = z_max
        self.vz_max = vz_max
        self.mass = mass
        self.n_motors = n_motors
        self.crash_penalty = crash_penalty
        self.enable_battery_drain = enable_battery_drain

        # Motor model
        mk = motor_kwargs or {}
        self.motor: MotorModel = make_motor(
            motor_model, n_motors=n_motors, device=device, **mk
        )

        # Battery
        bk = battery_kwargs or {}
        self.battery = BatteryModel(device=device, **bk)

        # Rigid body
        self.body = VerticalBody(device=device, mass=mass)

        # Reward function
        if reward_fn not in REWARDS:
            raise ValueError(f"Unknown reward: {reward_fn}. Available: {list(REWARDS)}")
        self.reward_fn = REWARDS[reward_fn]

        # Gymnasium spaces (per-env, used by SB3 wrappers)
        # obs: [z, vz, omega_mean, v_bat, z_target]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(5,), dtype=np.float32
        )
        # action: [-1, 1] mapped to duty cycle [0, 1] via (a+1)/2
        # Centered at 0 → duty=0.5 (above hover) so the Gaussian prior flies
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(1,), dtype=np.float32
        )

        # State tensors (initialized on first reset)
        self._body_state: dict[str, Tensor] = {}
        self._motor_state: dict[str, Tensor] = {}
        self._battery_state: dict[str, Tensor] = {}
        self._prev_action = torch.zeros(num_envs, 1, device=device)
        self._step_count = torch.zeros(num_envs, 1, device=device, dtype=torch.long)
        self._last_thrust = torch.zeros(num_envs, 1, device=device)
        self._last_duty = torch.zeros(num_envs, 1, device=device)

        # Logger (set externally via set_logger)
        self._logger: EnvLogger | None = None

    def set_logger(self, logger: EnvLogger):
        self._logger = logger

    def _nominal_voltage(self) -> float:
        return self.battery.n_cells * self.battery.v_full

    def _build_obs(self) -> Tensor:
        z = self._body_state["z"]
        vz = self._body_state["vz"]
        omega_mean = self._motor_state["omega"].mean(dim=-1, keepdim=True)
        v_bat = self._v_bat
        z_tgt = torch.full_like(z, self.z_target)
        return torch.cat([z, vz, omega_mean, v_bat, z_tgt], dim=-1)

    def _apply_ground_plane(self):
        """Ground plane: clamp z >= 0, zero out downward velocity on contact."""
        on_ground = self._body_state["z"] <= 0
        self._body_state["z"] = self._body_state["z"].clamp(min=0.0)
        # Kill downward velocity when on ground
        self._body_state["vz"] = torch.where(
            on_ground & (self._body_state["vz"] < 0),
            torch.zeros_like(self._body_state["vz"]),
            self._body_state["vz"],
        )

    def reset(
        self, *, seed=None, options=None
    ) -> tuple[np.ndarray, dict]:
        super().reset(seed=seed)

        self._body_state = self.body.initial_state(self.num_envs)
        # Start on the ground (z=0). Ground plane prevents falling through.
        # Policy must learn to spin up motors and lift off.
        self._motor_state = self.motor.initial_state(self.num_envs)
        self._battery_state = self.battery.initial_state(self.num_envs)
        self._v_bat = torch.full(
            (self.num_envs, 1), self._nominal_voltage(), device=self.device
        )
        self._prev_action = torch.zeros(self.num_envs, 1, device=self.device)
        self._step_count = torch.zeros(
            self.num_envs, 1, device=self.device, dtype=torch.long
        )

        obs = self._build_obs()
        return obs.cpu().numpy(), {}

    def _reset_envs(self, mask: Tensor):
        """Reset specific environments that terminated."""
        if not mask.any():
            return
        idx = mask.squeeze(-1)

        self._body_state["z"][idx] = 0.0
        self._body_state["vz"][idx] = 0.0
        for k in self._motor_state:
            self._motor_state[k][idx] = 0.0
        self._battery_state["soc"][idx] = 1.0
        self._v_bat[idx] = self._nominal_voltage()
        self._prev_action[idx] = 0.0
        self._step_count[idx] = 0

    def step(
        self, action: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
        action_t = torch.as_tensor(action, dtype=torch.float32, device=self.device)
        if action_t.dim() == 1:
            action_t = action_t.unsqueeze(-1)

        # EMA action smoothing — makes exploration produce sustained duty
        # cycles that give the motor time to spin up.
        action_t = 0.7 * action_t + 0.3 * self._prev_action

        # Map [-1,1] → duty cycle [0,1]
        duty = ((action_t + 1.0) / 2.0).clamp(0, 1).expand(-1, self.n_motors)

        # Physics substeps (action held constant)
        for _ in range(self.substeps):
            # Motor model step
            motor_args = (duty, self._motor_state, self.dt)
            if hasattr(self.motor, 'K_e'):
                thrust, torque, self._motor_state = self.motor(
                    *motor_args, v_bat=self._v_bat
                )
            else:
                thrust, torque, self._motor_state = self.motor(*motor_args)

            # Sum thrust across motors
            total_thrust = thrust.sum(dim=-1, keepdim=True)

            # Rigid body step
            self._body_state = self.body.step(total_thrust, self._body_state, self.dt)

            # Ground plane — prevents falling through floor
            self._apply_ground_plane()

            # Battery drain (optional)
            if self.enable_battery_drain:
                omega = self._motor_state["omega"]
                back_emf = getattr(self.motor, 'K_e', 0.0) * omega
                v_applied = duty * self._v_bat
                R = getattr(self.motor, 'R', 1.0)
                total_current = ((v_applied - back_emf) / R).clamp(min=0).sum(
                    dim=-1, keepdim=True
                )
                self._v_bat, self._battery_state = self.battery.step(
                    total_current, self._battery_state, self.dt
                )

        self._step_count += 1

        # Observations
        obs = self._build_obs()
        z = self._body_state["z"]
        vz = self._body_state["vz"]

        # Reward
        reward = self.reward_fn(
            z=z, vz=vz, action=action_t, prev_action=self._prev_action,
            z_target=self.z_target,
        )

        # Termination: flew too high or too fast (NOT for z<0, ground handles that)
        terminated = (z > self.z_max) | (vz.abs() > self.vz_max)
        if self.enable_battery_drain:
            terminated = terminated | (
                self._v_bat < self.battery.n_cells * self.battery.v_empty
            )

        # Apply crash penalty
        reward = torch.where(terminated, reward + self.crash_penalty, reward)

        # Truncation (max episode length)
        truncated = self._step_count >= self.max_steps

        done = terminated | truncated

        # Log before reset (so we capture terminal state)
        self._last_duty = ((action_t + 1.0) / 2.0).clamp(0, 1)
        self._last_thrust = total_thrust
        if self._logger is not None:
            self._logger.log_step(
                z=z, vz=vz,
                omega=self._motor_state["omega"],
                v_bat=self._v_bat,
                duty=self._last_duty,
                reward=reward,
                thrust=total_thrust,
                terminated=terminated,
                truncated=truncated,
            )

        self._prev_action = action_t.clone()

        # Auto-reset terminated envs
        self._reset_envs(done)

        return (
            obs.cpu().numpy(),
            reward.squeeze(-1).cpu().numpy(),
            terminated.squeeze(-1).cpu().numpy(),
            truncated.squeeze(-1).cpu().numpy(),
            {},
        )
