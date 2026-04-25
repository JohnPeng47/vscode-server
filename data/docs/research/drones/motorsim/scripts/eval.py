"""Evaluate a trained policy and produce diagnostic plots."""

import argparse
from pathlib import Path

import yaml
import torch
import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3 import PPO

from motorsim.envs import Hover1DEnv


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=str, required=True)
    parser.add_argument("--task", type=str, default="configs/task/hover_battery_drain.yaml")
    parser.add_argument("--motor", type=str, default="configs/motor/tmotor_f60.yaml")
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--output", type=str, default="eval_plots.png")
    args = parser.parse_args()

    task_cfg = load_config(args.task)
    motor_cfg = load_config(args.motor)

    env = Hover1DEnv(
        num_envs=1,
        device=args.device,
        motor_model=task_cfg["motor_model"],
        reward_fn=task_cfg["reward_fn"],
        dt=task_cfg["dt"],
        policy_freq=task_cfg["policy_freq"],
        max_episode_time=task_cfg["max_episode_time"],
        z_target=task_cfg["z_target"],
        z_max=task_cfg["z_max"],
        vz_max=task_cfg["vz_max"],
        mass=task_cfg["mass"],
        n_motors=task_cfg["n_motors"],
        motor_kwargs=motor_cfg,
        battery_kwargs=task_cfg.get("battery", {}),
    )

    model = PPO.load(args.policy, device=args.device)

    # Collect trajectory
    history = {"t": [], "z": [], "vz": [], "duty": [], "v_bat": [], "omega": [], "reward": []}
    obs, _ = env.reset()
    dt_policy = 1.0 / task_cfg["policy_freq"]

    for step in range(int(task_cfg["max_episode_time"] * task_cfg["policy_freq"])):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)

        history["t"].append(step * dt_policy)
        history["z"].append(obs[0, 0])
        history["vz"].append(obs[0, 1])
        history["omega"].append(obs[0, 2])
        history["v_bat"].append(obs[0, 3])
        history["duty"].append(action[0, 0])
        history["reward"].append(reward[0])

        if terminated[0] or truncated[0]:
            break

    # Plot
    fig, axes = plt.subplots(4, 1, figsize=(10, 12), sharex=True)
    t = history["t"]

    axes[0].plot(t, history["z"], label="altitude")
    axes[0].axhline(y=task_cfg["z_target"], color="r", linestyle="--", label="target")
    axes[0].set_ylabel("z [m]")
    axes[0].legend()
    axes[0].set_title("1D Hover with Battery Drain")

    axes[1].plot(t, history["duty"], color="orange")
    axes[1].set_ylabel("duty cycle")
    axes[1].set_ylim(-0.05, 1.05)

    axes[2].plot(t, history["v_bat"], color="green")
    axes[2].set_ylabel("V_bat [V]")

    axes[3].plot(t, history["reward"], color="purple")
    axes[3].set_ylabel("reward")
    axes[3].set_xlabel("time [s]")

    plt.tight_layout()
    plt.savefig(args.output, dpi=150)
    print(f"Plots saved to {args.output}")


if __name__ == "__main__":
    main()
