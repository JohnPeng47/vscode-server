"""Unit tests for motor models."""

import torch
import pytest
from motorsim.motors import make_motor


@pytest.fixture(params=["first_order", "averaged_electrical"])
def motor(request):
    return make_motor(request.param, n_motors=4, device="cpu")


def test_initial_state_shape(motor):
    state = motor.initial_state(batch_size=8)
    assert state["omega"].shape == (8, 4)


def test_zero_command_produces_zero_thrust(motor):
    state = motor.initial_state(32)
    cmd = torch.zeros(32, 4)
    thrust, torque, new_state = motor(cmd, state, dt=0.001)
    assert thrust.shape == (32, 4)
    assert (thrust >= 0).all()
    # With zero command and zero omega, thrust should be zero
    assert thrust.max() < 1e-6


def test_full_command_produces_thrust(motor):
    state = motor.initial_state(32)
    cmd = torch.ones(32, 4)
    # Step many times to let motor spin up
    for _ in range(1000):
        thrust, torque, state = motor(cmd, state, dt=0.001)
    assert thrust.min() > 0, "Full duty cycle should produce positive thrust"


def test_thrust_increases_with_command():
    motor = make_motor("averaged_electrical", n_motors=4, device="cpu")
    state = motor.initial_state(2)
    cmd_lo = torch.full((2, 4), 0.3)
    cmd_hi = torch.full((2, 4), 0.8)
    for _ in range(500):
        t_lo, _, state_lo = motor(cmd_lo, state, dt=0.001)
        t_hi, _, state_hi = motor(cmd_hi, state, dt=0.001)
        state = state  # keep same initial state for fair comparison
    # After convergence, higher command = higher thrust
    # (re-run from spun-up state)
    state_lo = motor.initial_state(1)
    state_hi = motor.initial_state(1)
    for _ in range(2000):
        t_lo, _, state_lo = motor(cmd_lo[:1], state_lo, dt=0.001)
        t_hi, _, state_hi = motor(cmd_hi[:1], state_hi, dt=0.001)
    assert t_hi.mean() > t_lo.mean()


def test_voltage_affects_thrust():
    """Tier 2-avg: lower voltage should produce less thrust at same duty cycle."""
    motor = make_motor("averaged_electrical", n_motors=4, device="cpu")
    cmd = torch.full((2, 4), 0.5)

    state_hi = motor.initial_state(1)
    state_lo = motor.initial_state(1)
    v_hi = torch.tensor([[16.8]])
    v_lo = torch.tensor([[13.2]])

    for _ in range(2000):
        t_hi, _, state_hi = motor(cmd[:1], state_hi, dt=0.001, v_bat=v_hi)
        t_lo, _, state_lo = motor(cmd[:1], state_lo, dt=0.001, v_bat=v_lo)

    assert t_hi.mean() > t_lo.mean(), "Higher voltage should produce more thrust"
