"""Compare Tier 1 vs Tier 2-avg motor models on the same task.

Trains both, then evaluates both with battery drain to show
that only the Tier 2-avg policy adapts to voltage changes.
"""

import argparse
from pathlib import Path

import yaml
import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from motorsim.envs import Hover1DEnv


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def train_and_eval(motor_model: str, task_cfg: dict, motor_cfg: dict, train_cfg: dict, device: str):
    """Train a policy with given motor model, evaluate with battery drain."""
    env = Hover1DEnv(
        num_envs=64,
        device=device,
        motor_model=motor_model,
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

    vec_env = DummyVecEnv([lambda: env])
    model = PPO("MlpPolicy", vec_env, verbose=0, device=device,
                learning_rate=train_cfg["learning_rate"],
                n_steps=train_cfg["n_steps"],
                batch_size=train_cfg["batch_size"],
                n_epochs=train_cfg["n_epochs"],
                gamma=train_cfg["gamma"],
                total_timesteps=train_cfg["total_timesteps"])

    print(f"Training {motor_model}...")
    model.learn(total_timesteps=train_cfg["total_timesteps"])

    # Evaluate on single env
    eval_env = Hover1DEnv(
        num_envs=1, device=device, motor_model=motor_model,
        reward_fn=task_cfg["reward_fn"], dt=task_cfg["dt"],
        policy_freq=task_cfg["policy_freq"],
        max_episode_time=task_cfg["max_episode_time"],
        z_target=task_cfg["z_target"], z_max=task_cfg["z_max"],
        vz_max=task_cfg["vz_max"], mass=task_cfg["mass"],
        n_motors=task_cfg["n_motors"], motor_kwargs=motor_cfg,
        battery_kwargs=task_cfg.get("battery", {}),
    )

    obs, _ = eval_env.reset()
    dt_policy = 1.0 / task_cfg["policy_freq"]
    history = {"t": [], "z": [], "duty": [], "v_bat": []}

    for step in range(int(task_cfg["max_episode_time"] * task_cfg["policy_freq"])):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = eval_env.step(action)
        history["t"].append(step * dt_policy)
        history["z"].append(obs[0, 0])
        history["duty"].append(action[0, 0])
        history["v_bat"].append(obs[0, 3])
        if terminated[0] or truncated[0]:
            break

    return history


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default="configs/task/hover_battery_drain.yaml")
    parser.add_argument("--motor", default="configs/motor/tmotor_f60.yaml")
    parser.add_argument("--train", default="configs/train/ppo.yaml")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", default="tier_comparison.png")
    args = parser.parse_args()

    task_cfg = load_config(args.task)
    motor_cfg = load_config(args.motor)
    train_cfg = load_config(args.train)

    tier1 = train_and_eval("first_order", task_cfg, motor_cfg, train_cfg, args.device)
    tier2 = train_and_eval("averaged_electrical", task_cfg, motor_cfg, train_cfg, args.device)

    # Plot comparison
    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)

    axes[0].plot(tier1["t"], tier1["z"], label="Tier 1 (first-order lag)", alpha=0.8)
    axes[0].plot(tier2["t"], tier2["z"], label="Tier 2-avg (electrical)", alpha=0.8)
    axes[0].axhline(y=task_cfg["z_target"], color="r", linestyle="--", label="target", alpha=0.5)
    axes[0].set_ylabel("altitude [m]")
    axes[0].legend()
    axes[0].set_title("Tier 1 vs Tier 2-avg: Hover with Battery Drain")

    axes[1].plot(tier1["t"], tier1["duty"], label="Tier 1", alpha=0.8)
    axes[1].plot(tier2["t"], tier2["duty"], label="Tier 2-avg", alpha=0.8)
    axes[1].set_ylabel("duty cycle")
    axes[1].legend()

    axes[2].plot(tier2["t"], tier2["v_bat"], color="green")
    axes[2].set_ylabel("V_bat [V]")
    axes[2].set_xlabel("time [s]")

    plt.tight_layout()
    plt.savefig(args.output, dpi=150)
    print(f"Comparison plot saved to {args.output}")


if __name__ == "__main__":
    main()
