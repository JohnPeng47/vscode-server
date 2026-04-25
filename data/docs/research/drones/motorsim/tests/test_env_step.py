"""Smoke tests for the hover environment."""

import numpy as np
import pytest
from motorsim.envs import Hover1DEnv


@pytest.fixture(params=["first_order", "averaged_electrical"])
def env(request):
    return Hover1DEnv(
        num_envs=4,
        device="cpu",
        motor_model=request.param,
        reward_fn="hover_alive",
        dt=0.001,
        policy_freq=100.0,
    )


def test_reset_returns_correct_shape(env):
    obs, info = env.reset()
    assert obs.shape == (4, 5), f"Expected (4, 5), got {obs.shape}"


def test_step_returns_correct_shapes(env):
    obs, _ = env.reset()
    action = np.full((4, 1), 0.5, dtype=np.float32)
    obs, reward, terminated, truncated, info = env.step(action)
    assert obs.shape == (4, 5)
    assert reward.shape == (4,)
    assert terminated.shape == (4,)
    assert truncated.shape == (4,)


def test_min_action_stays_on_ground(env):
    """With minimum action (-1 → duty=0), drone should sit on ground."""
    obs, _ = env.reset()
    action = np.full((4, 1), -1.0, dtype=np.float32)
    for _ in range(50):
        obs, reward, terminated, truncated, info = env.step(action)
    assert (obs[:, 0] >= 0).all(), "Ground plane should prevent z < 0"
    assert (obs[:, 0] < 0.01).all(), "Drone should be on the ground with zero duty"


def test_episode_runs_without_error(env):
    """Run a full episode with random actions."""
    obs, _ = env.reset()
    for _ in range(100):
        action = np.random.uniform(0, 1, size=(4, 1)).astype(np.float32)
        obs, reward, terminated, truncated, info = env.step(action)
