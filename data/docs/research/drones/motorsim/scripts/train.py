"""Train a policy on the hover environment.

Each run gets a timestamped directory with:
  - config snapshots (task, motor, train YAML)
  - SB3 training log (stdout)
  - episodes.csv (per-episode stats)
  - snapshots.csv (periodic env state dumps)
  - checkpoints/ (policy snapshots)
  - hover_policy.zip (final policy)
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path

import yaml
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback

from motorsim.envs import Hover1DEnv
from motorsim.envs.vec_wrapper import BatchedVecEnv
from motorsim.utils.logging import EnvLogger


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def make_env(task_cfg: dict, motor_cfg: dict, device: str, num_envs: int):
    battery_kwargs = task_cfg.get("battery", {})
    return Hover1DEnv(
        num_envs=num_envs,
        device=device,
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
        battery_kwargs=battery_kwargs,
        enable_battery_drain=task_cfg.get("enable_battery_drain", True),
        crash_penalty=task_cfg.get("crash_penalty", -10.0),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=str, default="configs/task/hover_simple.yaml")
    parser.add_argument("--motor", type=str, default="configs/motor/tmotor_f60.yaml")
    parser.add_argument("--train", type=str, default="configs/train/ppo.yaml")
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--num-envs", type=int, default=64)
    parser.add_argument("--run-name", type=str, default=None,
                        help="Name for this run (default: auto-timestamp)")
    parser.add_argument("--resume", type=str, default=None,
                        help="Path to a checkpoint .zip to resume from")
    parser.add_argument("--checkpoint-freq", type=int, default=100_000)
    parser.add_argument("--snapshot-freq", type=int, default=100,
                        help="Env state snapshot every N policy steps")
    args = parser.parse_args()

    task_cfg = load_config(args.task)
    motor_cfg = load_config(args.motor)
    train_cfg = load_config(args.train)

    # Create versioned run directory
    if args.run_name:
        run_name = args.run_name
    else:
        run_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path("runs") / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    # Snapshot configs into run dir
    config_dir = run_dir / "configs"
    config_dir.mkdir(exist_ok=True)
    for name, path in [("task", args.task), ("motor", args.motor), ("train", args.train)]:
        shutil.copy2(path, config_dir / f"{name}.yaml")

    # Save run metadata
    meta = {
        "run_name": run_name,
        "device": args.device,
        "num_envs": args.num_envs,
        "resume": args.resume,
        "task_config": args.task,
        "motor_config": args.motor,
        "train_config": args.train,
    }
    with open(run_dir / "meta.yaml", "w") as f:
        yaml.dump(meta, f)

    # Create env + logger
    env = make_env(task_cfg, motor_cfg, args.device, args.num_envs)
    logger = EnvLogger(run_dir / "logs", args.num_envs, snapshot_freq=args.snapshot_freq)
    env.set_logger(logger)
    vec_env = BatchedVecEnv(env)

    # Create or resume model
    if args.resume:
        print(f"Resuming from {args.resume}")
        model = PPO.load(args.resume, env=vec_env, device=args.device)
    else:
        model = PPO(
            "MlpPolicy",
            vec_env,
            learning_rate=train_cfg["learning_rate"],
            n_steps=train_cfg["n_steps"],
            batch_size=train_cfg["batch_size"],
            n_epochs=train_cfg["n_epochs"],
            gamma=train_cfg["gamma"],
            gae_lambda=train_cfg["gae_lambda"],
            clip_range=train_cfg["clip_range"],
            ent_coef=train_cfg["ent_coef"],
            vf_coef=train_cfg["vf_coef"],
            max_grad_norm=train_cfg["max_grad_norm"],
            verbose=1,
            device=args.device,
        )

    checkpoint_cb = CheckpointCallback(
        save_freq=args.checkpoint_freq,
        save_path=str(run_dir / "checkpoints"),
        name_prefix="hover",
    )

    print(f"Run directory: {run_dir}")
    print(f"Logging to: {run_dir / 'logs'}")

    try:
        model.learn(
            total_timesteps=train_cfg["total_timesteps"],
            callback=checkpoint_cb,
        )
    except KeyboardInterrupt:
        print("\nTraining interrupted by user.")
    finally:
        # Always save final policy and close logger
        final_path = run_dir / "hover_policy"
        model.save(final_path)
        print(f"Policy saved to {final_path}")

        # Print episode summary
        print("\n" + logger.summary())
        logger.close()


if __name__ == "__main__":
    main()
