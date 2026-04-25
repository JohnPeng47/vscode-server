"""Tests for battery model."""

import torch
from motorsim.dynamics.battery import BatteryModel


def test_initial_voltage():
    bat = BatteryModel(n_cells=4, v_full=4.2)
    state = bat.initial_state(8)
    v, _ = bat.step(torch.zeros(8, 1), state, dt=0.01)
    expected = 4 * 4.2
    assert abs(v[0].item() - expected) < 0.01


def test_voltage_drops_under_load():
    bat = BatteryModel(n_cells=4, capacity_ah=1.3, v_full=4.2, v_empty=3.3)
    state = bat.initial_state(1)
    current = torch.tensor([[20.0]])  # 20A draw

    voltages = []
    for _ in range(1000):
        v, state = bat.step(current, state, dt=0.01)
        voltages.append(v.item())

    assert voltages[-1] < voltages[0], "Voltage should drop under sustained load"


def test_no_load_voltage_stable():
    bat = BatteryModel()
    state = bat.initial_state(1)
    v0, _ = bat.step(torch.zeros(1, 1), state, dt=0.01)
    for _ in range(100):
        v, state = bat.step(torch.zeros(1, 1), state, dt=0.01)
    assert abs(v.item() - v0.item()) < 0.001
