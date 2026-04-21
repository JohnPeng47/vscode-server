"""
Exercise 2.5 — Nonstationary 10-Armed Bandit (Sutton & Barto, 2nd ed.)

All q*(a) start at 0 and take independent random walks:
    q*(a) += N(0, 0.01) each step

Compares sample-average vs constant step-size (alpha=0.1),
both using epsilon-greedy (eps=0.1) over 10,000 steps, 2000 tasks.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


# ── Agent ────────────────────────────────────────────────────

def select_actions(Q, epsilon, rng):
    """Epsilon-greedy action selection across all tasks.

    With probability (1 - epsilon), pick the greedy action:
        A = argmax_a Q(a)

    With probability epsilon, pick a random action uniformly.
    This ensures continued exploration so that every action is
    sampled infinitely often, and all Q(a) converge to q*(a)
    in the stationary case. (Section 2.2)
    """
    n_tasks, n_arms = Q.shape
    greedy_actions = Q.argmax(axis=1)

    if epsilon == 0:
        return greedy_actions

    explore_mask = rng.random(n_tasks) < epsilon
    random_actions = rng.integers(0, n_arms, size=n_tasks)
    return np.where(explore_mask, random_actions, greedy_actions)


def sample_rewards(q_star, actions, rng):
    """Reward = Q*(action) + N(0, 1).

    The actual reward R_t is drawn from a normal distribution
    with mean q*(A_t) and variance 1. (Section 2.3)
    """
    task_idx = np.arange(len(actions))
    return q_star[task_idx, actions] + rng.standard_normal(len(actions))


# ── Update rules ─────────────────────────────────────────────
#
# Both methods follow the general incremental update form (Eq 2.4):
#
#   NewEstimate <- OldEstimate + StepSize * [Target - OldEstimate]
#
# The [Target - OldEstimate] term is the error in the estimate.
# It is reduced by taking a step toward the "Target" (the most
# recent reward). The two methods differ only in their StepSize.

def update_sample_average(Q, N_counts, actions, rewards):
    """Incremental sample-average update (Eq 2.3):

        Q_{n+1} = Q_n + (1/n) * [R_n - Q_n]

    StepSize = 1/n, where n is the number of times this action
    has been selected. This computes the exact sample mean of all
    rewards ever received for the action.

    Guaranteed to converge to q*(a) in the stationary case by the
    law of large numbers. However, as n grows large the step size
    1/n shrinks toward zero, making the estimate increasingly rigid.
    In a nonstationary environment, this means the agent becomes
    unable to adapt — old rewards from an obsolete distribution
    carry equal weight with recent ones. (Section 2.4)
    """
    task_idx = np.arange(len(actions))
    N_counts[task_idx, actions] += 1
    n = N_counts[task_idx, actions]
    Q[task_idx, actions] += (rewards - Q[task_idx, actions]) / n


def update_constant_alpha(Q, actions, rewards, alpha):
    """Constant step-size update (Eq 2.5):

        Q_{n+1} = Q_n + alpha * [R_n - Q_n]

    StepSize = alpha (constant, here 0.1). Expanding the recurrence
    yields an exponential recency-weighted average (Eq 2.6):

        Q_{n+1} = (1-alpha)^n * Q_1
                  + sum_{i=1}^{n} alpha * (1-alpha)^{n-i} * R_i

    The weight on reward R_i is alpha*(1-alpha)^{n-i}, which decays
    exponentially with the number of intervening rewards (n - i).
    Recent rewards get far more influence than old ones.

    This does NOT satisfy the convergence conditions (Eq 2.7):
      - sum alpha_n = inf   (met: constant alpha sums to inf)
      - sum alpha_n^2 < inf (NOT met: constant alpha^2 also sums to inf)

    So the estimate never fully converges — it keeps responding to
    new rewards. This is actually desirable in a nonstationary
    environment, where the true values drift over time. (Section 2.5)
    """
    task_idx = np.arange(len(actions))
    Q[task_idx, actions] += alpha * (rewards - Q[task_idx, actions])


# ── Simulation ───────────────────────────────────────────────

def run_nonstationary(n_tasks, n_arms, n_steps, epsilon, method, rng,
                      alpha=0.1, walk_std=0.01):
    """Run nonstationary bandit experiment.

    Unlike the standard 10-armed testbed where q*(a) ~ N(0,1) and
    stays fixed, here all q*(a) start at 0 and undergo independent
    random walks each step:

        q*(a) <- q*(a) + N(0, 0.01)

    This means the best action changes over time, so an agent that
    can't adapt to recent experience will fall behind. The sample-
    average method weights all past rewards equally (via 1/n), so it
    effectively averages over the entire non-stationary history and
    becomes sluggish. The constant-alpha method forgets old rewards
    exponentially, letting it track the drifting values. (Exercise 2.5)

    Args:
        method: "sample_average" or "constant_alpha"
    """
    q_star = np.zeros((n_tasks, n_arms))
    Q = np.zeros((n_tasks, n_arms))
    N_counts = np.zeros((n_tasks, n_arms), dtype=int)

    avg_rewards = np.zeros(n_steps)
    optimal_pct = np.zeros(n_steps)

    for t in range(n_steps):
        # The optimal action must be recomputed each step because
        # the random walk may have changed which arm is best
        optimal_actions = q_star.argmax(axis=1)
        actions = select_actions(Q, epsilon, rng)
        rewards = sample_rewards(q_star, actions, rng)

        if method == "sample_average":
            update_sample_average(Q, N_counts, actions, rewards)
        else:
            update_constant_alpha(Q, actions, rewards, alpha)

        avg_rewards[t] = rewards.mean()
        optimal_pct[t] = (actions == optimal_actions).mean() * 100

        # Random walk: q*(a) += N(0, walk_std) for all arms, all tasks.
        # This is what makes the problem nonstationary — the true values
        # drift continuously, so past experience becomes stale.
        q_star += rng.normal(0, walk_std, (n_tasks, n_arms))

    return avg_rewards, optimal_pct


# ── Plotting ─────────────────────────────────────────────────

def plot_results(results, save_path=None):
    """Two-panel plot: avg reward and % optimal action."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    for label, (avg_r, opt_pct) in results.items():
        ax1.plot(avg_r, label=label, linewidth=1)
        ax2.plot(opt_pct, label=label, linewidth=1)

    ax1.set_ylabel("Average reward")
    ax1.legend()

    ax2.set_ylabel("% Optimal action")
    ax2.set_xlabel("Steps")
    ax2.legend()

    plt.suptitle("Nonstationary 10-Armed Bandit (Exercise 2.5)", y=1.01)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved to {save_path}")
    plt.show()


# ── Main ─────────────────────────────────────────────────────

def main():
    N_ARMS = 10
    N_TASKS = 2000
    N_STEPS = 10_000
    EPSILON = 0.1

    rng = np.random.default_rng(42)

    results = {}

    for method, label in [("sample_average", "Sample average"),
                          ("constant_alpha", "Constant α = 0.1")]:
        avg_rewards, optimal_pct = run_nonstationary(
            N_TASKS, N_ARMS, N_STEPS, EPSILON, method, rng
        )
        results[label] = (avg_rewards, optimal_pct)
        print(f"Done: {label}")

    save_path = Path(__file__).parent / "non_stationary.png"
    plot_results(results, save_path)


if __name__ == "__main__":
    main()
