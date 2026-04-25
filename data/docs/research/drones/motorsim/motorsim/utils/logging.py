"""Environment-level logging for debugging sim + RL interaction.

Tracks per-episode and per-step metrics that SB3 doesn't capture.
Writes structured CSV logs that can be loaded for post-hoc analysis.
"""

import csv
import time
from pathlib import Path
from dataclasses import dataclass, field

import torch
from torch import Tensor


@dataclass
class EpisodeStats:
    """Accumulated stats for a single episode across one env."""
    total_reward: float = 0.0
    length: int = 0
    max_z: float = 0.0
    max_vz: float = 0.0
    max_duty: float = 0.0
    max_omega: float = 0.0
    termination_reason: str = ""


class EnvLogger:
    """Logs environment state for debugging.

    Produces two CSV files:
      - episodes.csv: one row per completed episode (return, length, reason, etc.)
      - snapshots.csv: periodic state dumps (every snapshot_freq policy steps)
    """

    def __init__(self, log_dir: str | Path, num_envs: int, snapshot_freq: int = 100):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.num_envs = num_envs
        self.snapshot_freq = snapshot_freq
        self.global_step = 0
        self.start_time = time.time()

        # Per-env episode accumulators
        self.ep_stats = [EpisodeStats() for _ in range(num_envs)]

        # Episode log
        self._ep_file = open(self.log_dir / "episodes.csv", "w", newline="")
        self._ep_writer = csv.writer(self._ep_file)
        self._ep_writer.writerow([
            "wall_time", "global_step", "env_id",
            "return", "length", "max_z", "max_vz", "max_duty", "max_omega",
            "termination_reason",
        ])

        # Snapshot log (aggregate stats across envs)
        self._snap_file = open(self.log_dir / "snapshots.csv", "w", newline="")
        self._snap_writer = csv.writer(self._snap_file)
        self._snap_writer.writerow([
            "wall_time", "global_step",
            "z_mean", "z_std", "z_min", "z_max",
            "vz_mean", "vz_std",
            "duty_mean", "duty_std",
            "omega_mean", "omega_std",
            "v_bat_mean",
            "reward_mean", "reward_std",
            "thrust_mean",
            "n_on_ground", "n_flying", "n_terminated",
        ])

    def log_step(
        self,
        z: Tensor,
        vz: Tensor,
        omega: Tensor,
        v_bat: Tensor,
        duty: Tensor,
        reward: Tensor,
        thrust: Tensor,
        terminated: Tensor,
        truncated: Tensor,
    ):
        """Called every policy step with batched tensors [num_envs, 1]."""
        self.global_step += 1

        # Update per-env episode stats
        for i in range(self.num_envs):
            s = self.ep_stats[i]
            s.total_reward += reward[i].item()
            s.length += 1
            s.max_z = max(s.max_z, z[i].item())
            s.max_vz = max(s.max_vz, abs(vz[i].item()))
            s.max_duty = max(s.max_duty, duty[i].item() if duty.dim() > 1 else duty[i].item())
            s.max_omega = max(s.max_omega, omega[i].mean().item() if omega.dim() > 1 else omega[i].item())

        # Log completed episodes
        done = terminated | truncated
        wall_time = time.time() - self.start_time
        for i in range(self.num_envs):
            if done[i].item():
                s = self.ep_stats[i]
                if terminated[i].item():
                    if z[i].item() > 4.9:
                        s.termination_reason = "ceiling"
                    elif abs(vz[i].item()) > 9.9:
                        s.termination_reason = "velocity"
                    else:
                        s.termination_reason = "other"
                elif truncated[i].item():
                    s.termination_reason = "truncated"

                self._ep_writer.writerow([
                    f"{wall_time:.1f}", self.global_step, i,
                    f"{s.total_reward:.2f}", s.length,
                    f"{s.max_z:.3f}", f"{s.max_vz:.3f}",
                    f"{s.max_duty:.3f}", f"{s.max_omega:.1f}",
                    s.termination_reason,
                ])
                self.ep_stats[i] = EpisodeStats()

        # Periodic snapshot
        if self.global_step % self.snapshot_freq == 0:
            z_f = z.squeeze(-1).float()
            vz_f = vz.squeeze(-1).float()
            omega_f = omega.float()
            duty_f = duty.float()
            reward_f = reward.squeeze(-1).float() if reward.dim() > 1 else reward.float()

            on_ground = (z_f < 0.01).sum().item()
            flying = (z_f > 0.1).sum().item()
            n_term = terminated.sum().item() if terminated.dim() > 0 else 0

            self._snap_writer.writerow([
                f"{wall_time:.1f}", self.global_step,
                f"{z_f.mean():.4f}", f"{z_f.std():.4f}",
                f"{z_f.min():.4f}", f"{z_f.max():.4f}",
                f"{vz_f.mean():.4f}", f"{vz_f.std():.4f}",
                f"{duty_f.mean():.4f}", f"{duty_f.std():.4f}",
                f"{omega_f.mean():.1f}", f"{omega_f.std():.1f}",
                f"{v_bat.mean():.3f}",
                f"{reward_f.mean():.4f}", f"{reward_f.std():.4f}",
                f"{thrust.mean():.4f}" if thrust is not None else "0",
                on_ground, flying, n_term,
            ])

        # Flush periodically
        if self.global_step % 1000 == 0:
            self._ep_file.flush()
            self._snap_file.flush()

    def close(self):
        self._ep_file.close()
        self._snap_file.close()

    def summary(self, last_n: int = 100) -> str:
        """Print a text summary of recent episodes (for console output)."""
        # Read last N episodes from CSV
        episodes_path = self.log_dir / "episodes.csv"
        if not episodes_path.exists():
            return "No episodes logged yet."

        lines = episodes_path.read_text().strip().split("\n")
        if len(lines) <= 1:
            return "No episodes completed yet."

        recent = lines[-min(last_n, len(lines) - 1):]
        returns = []
        lengths = []
        max_zs = []
        reasons = {}
        for line in recent:
            parts = line.split(",")
            if len(parts) >= 10:
                try:
                    returns.append(float(parts[3]))
                    lengths.append(int(parts[4]))
                    max_zs.append(float(parts[5]))
                    reason = parts[9]
                    reasons[reason] = reasons.get(reason, 0) + 1
                except (ValueError, IndexError):
                    continue

        if not returns:
            return "No valid episodes parsed."

        import numpy as np
        returns = np.array(returns)
        lengths = np.array(lengths)
        max_zs = np.array(max_zs)

        lines = [
            f"Last {len(returns)} episodes:",
            f"  return:  {returns.mean():.1f} ± {returns.std():.1f} [{returns.min():.1f}, {returns.max():.1f}]",
            f"  length:  {lengths.mean():.0f} ± {lengths.std():.0f} [{lengths.min()}, {lengths.max()}]",
            f"  max_z:   {max_zs.mean():.2f} ± {max_zs.std():.2f} [{max_zs.min():.2f}, {max_zs.max():.2f}]",
            f"  reasons: {reasons}",
        ]
        return "\n".join(lines)
