# motorsim development notes

## 2026-04-25: Initial build + debugging

### Bug 1: k_f too low (TWR < 1)
Default k_f=2.5e-7 gave TWR=0.80 — drone physically could not hover.
Fixed: k_f=7.5e-7 gives TWR=2.39. Hover at duty=0.39, omega=1617 rad/s.
Updated both Python defaults and YAML config.

### Bug 2: Ground plane missing
Original env terminated at z<0. Drone starting at z=0 immediately fell
through and terminated every episode in 1 step. Policy couldn't learn.
Fix: Added _apply_ground_plane() — clamps z>=0, zeros downward velocity.
Following QuadSwarm's pattern (floor_interaction with friction).

### Issue 3: Policy converges to "sit on ground" (2M steps)
With ground plane, policy found local optimum: duty=0, z=0, reward=-0.9/step.
Never discovered that flying gives +0.1/step at z=z_target.

Diagnosis: NOT a model bug. Stochastic policy actually reaches z=2.73m.
The deterministic mean hasn't converged because:
- Motor lag requires ~10 consistent steps of duty>0.4 to spin up
- PPO's per-step Gaussian noise gives random actions, motors never spin up coherently
- 2M steps insufficient for this delayed-reward, exploration-heavy task

Fix attempt: Increased to 10M steps, set ent_coef=0.0 (let PPO's inherent
Gaussian std handle exploration rather than forcing extra entropy).
Training in progress.

### Possible future fixes if 10M doesn't converge:
1. Add EMA action smoother (like GRaD-Nav: alpha=0.7 for thrust)
   - Smooths random exploration → motors get consistent input → can spin up
2. Reward shaping: add velocity bonus `+0.5*max(0,vz)*(z_target-z)`
   - Gives positive gradient toward flying even from z=0
3. Curriculum: start at altitude, gradually lower init height
4. Action space reparameterization: center at 0.5 instead of 0

### Physics verified correct
- duty=0.39: thrust=7.83N ≈ weight (7.85N), drone sits on ground
- duty=0.42: lifts off, reaches 5m in 3s
- duty=0.50: rockets to 22m
- Motor spinup time ~0.3s from zero to hover omega
- Ground plane: prevents z<0, zeros downward velocity
- Battery drain: voltage drops under sustained load

### Feature survey completed
Surveyed all 8 sim codebases for physics features. Key additions identified:
- OU thrust noise (from QuadSwarm)
- Observation noise (from AirGym, GRaD-Nav)
- Vertical drag (from GRaD-Nav)
- Motor asymmetry (from QuadSwarm, optimal-quad-control)
- Action history in obs (from pybullet, SimpleFlight)
These are 10-20 lines each, will add after base task converges.
