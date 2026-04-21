"""
10-Armed Testbed — Sutton & Barto, Figure 2.1

Reproduces the greedy vs epsilon-greedy comparison from Chapter 2.
- 2000 bandit tasks, each with 10 arms
- True action values Q*(a) ~ N(0, 1)
- Rewards ~ N(Q*(a), 1)
- 1000 plays per task
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


# ── Testbed ──────────────────────────────────────────────────

def create_testbed(n_tasks, n_arms, rng):
    """Generate true action values for all bandit tasks.

    Returns:
        q_star: (n_tasks, n_arms) — true value of each arm
        optimal_actions: (n_tasks,) — index of best arm per task
    """
    q_star = rng.standard_normal((n_tasks, n_arms))
    optimal_actions = q_star.argmax(axis=1)
    return q_star, optimal_actions


# ── Agent ────────────────────────────────────────────────────

def select_actions(Q, epsilon, rng):
    """Epsilon-greedy action selection across all tasks.

    Args:
        Q: (n_tasks, n_arms) — current value estimates
        epsilon: exploration rate (0 = pure greedy)
        rng: numpy random generator

    Returns:
        actions: (n_tasks,) — selected action per task
    """
    n_tasks, n_arms = Q.shape
    greedy_actions = Q.argmax(axis=1)

    if epsilon == 0:
        return greedy_actions

    explore_mask = rng.random(n_tasks) < epsilon
    random_actions = rng.integers(0, n_arms, size=n_tasks)
    return np.where(explore_mask, random_actions, greedy_actions)


def sample_rewards(q_star, actions, rng):
    """Draw a reward for each task given the chosen action.

    Reward = Q*(action) + noise, where noise ~ N(0, 1).
    """
    task_idx = np.arange(len(actions))
    return q_star[task_idx, actions] + rng.standard_normal(len(actions))


def update_estimates(Q, N_counts, actions, rewards):
    """Incremental sample-average update: Q += (r - Q) / n."""
    task_idx = np.arange(len(actions))
    N_counts[task_idx, actions] += 1
    n = N_counts[task_idx, actions]
    Q[task_idx, actions] += (rewards - Q[task_idx, actions]) / n


# ── Simulation ───────────────────────────────────────────────

def run_experiment(q_star, optimal_actions, epsilon, n_plays, rng):
    """Run one epsilon-greedy experiment over the full testbed.

    Returns:
        avg_rewards: (n_plays,) — mean reward per timestep
        optimal_pct: (n_plays,) — % of tasks picking the best arm
    """
    n_tasks, n_arms = q_star.shape
    Q = np.zeros((n_tasks, n_arms))
    N_counts = np.zeros((n_tasks, n_arms), dtype=int)

    avg_rewards = np.zeros(n_plays)
    optimal_pct = np.zeros(n_plays)

    for t in range(n_plays):
        actions = select_actions(Q, epsilon, rng)
        rewards = sample_rewards(q_star, actions, rng)
        update_estimates(Q, N_counts, actions, rewards)

        avg_rewards[t] = rewards.mean()
        optimal_pct[t] = (actions == optimal_actions).mean() * 100

    return avg_rewards, optimal_pct


# ── Plotting ─────────────────────────────────────────────────

def plot_results(results, save_path=None):
    """Two-panel plot matching Figure 2.1: avg reward and % optimal."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8), sharex=True)

    for label, (avg_r, opt_pct) in results.items():
        ax1.plot(avg_r, label=label, linewidth=1)
        ax2.plot(opt_pct, label=label, linewidth=1)

    ax1.set_ylabel("Average reward")
    ax1.set_ylim(0, 1.6)
    ax1.legend()

    ax2.set_ylabel("% Optimal action")
    ax2.set_xlabel("Plays")
    ax2.set_ylim(0, 100)
    ax2.legend()

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Saved to {save_path}")
    plt.show()


# ── Main ─────────────────────────────────────────────────────

def main():
    N_ARMS = 10
    N_TASKS = 2000
    N_PLAYS = 1000
    EPSILONS = [0, 0.01, 0.1]

    rng = np.random.default_rng(42)
    q_star, optimal_actions = create_testbed(N_TASKS, N_ARMS, rng)

    results = {}
    for eps in EPSILONS:
        label = "greedy" if eps == 0 else f"ε = {eps}"
        avg_rewards, optimal_pct = run_experiment(
            q_star, optimal_actions, eps, N_PLAYS, rng
        )
        results[label] = (avg_rewards, optimal_pct)
        print(f"Done: {label}")

    save_path = Path(__file__).parent / "figure_2_1_10armed_testbed.png"
    plot_results(results, save_path)


if __name__ == "__main__":
    main()
