"""SB3 VecEnv wrapper for our internally-batched environment."""

import numpy as np
from stable_baselines3.common.vec_env import VecEnv
from gymnasium import spaces


class BatchedVecEnv(VecEnv):
    """Wraps a batched Hover1DEnv as an SB3 VecEnv.

    Our env already handles N parallel envs internally via tensor ops.
    This wrapper just implements the VecEnv interface that SB3 expects.
    """

    def __init__(self, env):
        self.env = env
        super().__init__(
            num_envs=env.num_envs,
            observation_space=env.observation_space,
            action_space=env.action_space,
        )
        self._actions: np.ndarray | None = None

    def reset(self):
        obs, info = self.env.reset()
        return obs

    def step_async(self, actions: np.ndarray):
        self._actions = actions

    def step_wait(self):
        obs, rewards, terminated, truncated, info = self.env.step(self._actions)
        # SB3 VecEnv uses a single `dones` array
        dones = terminated | truncated
        # SB3 expects a list of info dicts, one per env
        infos = [{} for _ in range(self.num_envs)]
        for i in range(self.num_envs):
            if dones[i]:
                # SB3 expects terminal_observation in info when auto-resetting
                infos[i]["terminal_observation"] = obs[i].copy()
                infos[i]["TimeLimit.truncated"] = bool(truncated[i])
        return obs, rewards, dones, infos

    def close(self):
        pass

    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False] * self.num_envs

    def env_method(self, method_name, *method_args, indices=None, **method_kwargs):
        return [getattr(self.env, method_name)(*method_args, **method_kwargs)]

    def get_attr(self, attr_name, indices=None):
        return [getattr(self.env, attr_name)]

    def set_attr(self, attr_name, value, indices=None):
        setattr(self.env, attr_name, value)

    def seed(self, seed=None):
        return [seed] * self.num_envs
