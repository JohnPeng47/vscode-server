# Training Run History (reconstructed from conversation)

## Run 1: Broken k_f (TWR < 1)
- **Config:** k_f=2.5e-7 (default), action [0,1], terminate at z<0, no ground plane
- **Task:** hover_battery_drain (battery enabled)
- **Steps:** 2M, 64 envs, ~5-8K SPS
- **Problem:** TWR=0.80 — drone physically cannot hover (max thrust 6.25N < weight 7.85N)
- **Final metrics:**
  - std: 0.993 → 0.394
  - value_loss: 7.01 → 5.58e-7
  - explained_variance: -3.49e4 → converged
- **Eval:** z=0, duty=0, reward=-0.9, V_bat=16.8 (flat lines)
- **Diagnosis:** Not a training issue — impossible physics. Policy correctly learned "do nothing."

## Run 2: Fixed YAML k_f, switched to hover_simple
- **Config:** k_f=7.5e-7 (YAML), action [0,1], terminate at z<0, no ground plane
- **Task:** hover_simple (battery drain disabled)
- **Steps:** 2M, 64 envs
- **Change:** Updated tmotor_f60.yaml to k_f=7.5e-7, switched to hover_simple config
- **Final metrics:**
  - std: 1.03 → 1.19 (INCREASING — bad sign)
  - value_loss: 3660 → 2190
  - explained_variance: 0.403 → 0.266
- **Eval:** z=0, duty=0, reward=-0.9 (identical to run 1)
- **Diagnosis:** Python defaults still had k_f=2.5e-7. Even though YAML passed 7.5e-7
  to the motor, the eval script created motors without kwargs → used old defaults.
  The training itself likely used correct params (via YAML) but the fundamental issue
  was that starting at z=0 with terminate-at-z<0 meant 1-step episodes.

## Run 3: Fixed Python defaults + ground plane + start at z=0
- **Config:** k_f=7.5e-7 (Python + YAML), action [0,1], ground plane (z≥0 clamp), start z=0
- **Task:** hover_simple
- **Steps:** 2M, 64 envs
- **Changes:** Fixed Python defaults (k_f, k_tau), added _apply_ground_plane(), removed z<0 termination
- **Final metrics:**
  - std: 1.03 → 1.11 (still increasing)
  - value_loss: 3660 → 2570
  - explained_variance: 0.403 → ~0.27
- **Eval:** z=0, duty=0, reward=-0.9
- **Diagnosis:** Ground plane works (drone sits at z=0 instead of falling through).
  But policy still converges to "do nothing." Stochastic policy tested separately
  → actually reaches z=2.73m! Problem is deterministic mean stuck at 0, not physics.
  2M steps insufficient for this exploration challenge.

## Run 4: 10M steps, ent_coef=0
- **Config:** same as Run 3 but 10M steps, ent_coef=0.0
- **Task:** hover_simple
- **Steps:** 10M, 64 envs, ~5-7K SPS, ~25min wall-clock
- **Changes:** Increased training to 10M, removed entropy bonus
- **Metrics progression:**
  - T+5min:  explained_variance=0.563, std=0.815, value_loss=7.46
  - T+10min: explained_variance=0.944, std=0.813, value_loss=233
  - T+15min: explained_variance=0.951, std=0.798, value_loss=124
  - T+20min: explained_variance=0.924, std=0.771, value_loss=157
  - Final:   std=0.772, value_loss=295
- **Eval:** z=0, duty≈0.02, reward=-0.9. V_bat briefly dipped to 15V at t=0 then
  recovered (policy tried nonzero duty for 1-2 steps then gave up).
- **Diagnosis:** Value function learned well (expl_var 0.95!) but policy mean still
  at 0. The [0,1] action space with clipped Gaussian kills gradients when mean < 0.
  Policy gets trapped at the lower bound.

## Run 5: 10M steps, EMA action smoother
- **Config:** same as Run 4 + EMA smoother (alpha=0.7 new + 0.3 prev)
- **Task:** hover_simple
- **Steps:** 10M, 64 envs
- **Changes:** Added action_t = 0.7*action_t + 0.3*prev_action before motor
- **Metrics progression:**
  - T+2min:  explained_variance=0.772, std=0.948 (much better early learning!)
  - T+12min: explained_variance=0.946, std=0.829, value_loss=472
  - T+15min: explained_variance=0.951, std=0.798, value_loss=124
  - T+22min: explained_variance=0.960, std=0.739, value_loss=71
  - Final:   std=0.709, value_loss=324
- **Eval:** z=0, duty=0, reward=-0.9 (same result despite better metrics)
- **Diagnosis:** EMA helped learning speed (expl_var reached 0.77 at T+2min vs 0.27
  without EMA at same point). But deterministic policy mean still converged to 0.
  The [0,1] clipping gradient death is the fundamental blocker, not exploration.

## Run 6: Action space [-1,1] + EMA (KILLED mid-training)
- **Config:** action space [-1,1] mapped to duty via (a+1)/2, EMA, ent_coef=0
- **Task:** hover_simple
- **Steps:** ~7M of 10M (killed by user)
- **Changes:** action_space Box[-1,1], rescale in env. Gaussian mean at 0 → duty=0.5.
- **Metrics progression:**
  - T+2min:  explained_variance=0.466, std=0.991
  - T+12min: explained_variance=0.026, std=0.903, value_loss=1990
  - T+22min: explained_variance=0.021, std=0.785, value_loss=1970
- **Eval:** Not completed (killed)
- **Diagnosis:** explained_variance collapsed from 0.47 → 0.02, value_loss stuck at ~2000.
  The drone was flying (duty=0.5 → above hover) but oscillating wildly. Value function
  couldn't fit the chaotic returns. Training direction unclear — might have eventually
  converged or might need reward shaping.
- **Surviving log:** runs/hover_simple/train.log

---

## Summary of what we learned

| Issue | Discovered in | Fix |
|-------|--------------|-----|
| k_f too low (TWR<1) | Run 1 | k_f: 2.5e-7 → 7.5e-7 |
| No ground plane | Run 1-2 | Added _apply_ground_plane() |
| Python defaults ≠ YAML | Run 2 | Updated both |
| 2M steps insufficient | Run 3 | Increased to 10M |
| [0,1] action clips gradients | Run 4-5 | Changed to [-1,1] with rescale |
| Per-step noise incoherent for motor spinup | Run 3-4 | Added EMA smoother |
| [-1,1] causes wild oscillation | Run 6 | Untested: reward shaping or curriculum |

## Untried fixes
1. Start at altitude (spawn at z=z_target, learn hover first) — what OmniDrones does
2. Reward shaping: velocity bonus toward target
3. Curriculum: start easy → gradually harder
4. Reduce action std init or use squashed Gaussian (SB3 `use_sde=True`)
