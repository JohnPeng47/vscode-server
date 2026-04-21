# Inter-Drone Comms for Distributed MoE

> What does the communication layer need to look like for MoE routing across a drone swarm, and what's the upper bound on mesh network range?

## The Core Comms Problem

In the MoE-on-drones architecture (see [moe/chats.md](../moe/chats.md)), each drone hosts a shared backbone CNN + router + one expert head. When the router selects a remote expert, the drone must transmit a compact feature vector to the expert-hosting drone and receive the result back. The comms layer is the binding constraint — not compute.

**Per-routing-event payload:**
- Forward: 128-dim feature vector @ 8-bit = **128 bytes**
- Return: expert output (e.g., class logits) = **8-32 bytes**
- Round-trip per event: **~160 bytes**

**Per-drone throughput demand at 10 Hz inference:**
- If every frame routes remotely (worst case): 160 B x 10 Hz = **1.6 KB/s per drone**
- 5-drone swarm, all routing remotely: **8 KB/s aggregate**
- With overhead (headers, retransmits, MAC): ~2-3x = **~20 KB/s aggregate**

This is low. The bottleneck is latency, not bandwidth.

## Latency Budget

The flight control inner loop runs at 250-500 Hz on the STM32 and doesn't depend on the MoE. The MoE perception loop runs at ~10 Hz. That gives a **100ms per-frame budget**. Subtract ~50-60ms for backbone CNN inference on GAP8, leaving **~40-50ms for the routing round-trip** (transmit, remote expert inference, return).

| Component              | Budget   |
|------------------------|----------|
| Backbone CNN (GAP8)    | 50-60 ms |
| TX feature vector      | 2-10 ms  |
| Remote expert inference | 10-20 ms |
| RX result              | 2-10 ms  |
| Margin                 | 10-20 ms |
| **Total**              | **~100 ms** |

This is tight but feasible if single-hop radio latency stays under ~10ms.

## Radio Options on Crazyflie-class Hardware

| Radio               | Band     | Range (indoor) | Range (outdoor LOS) | Data Rate    | Latency  | Power   | Notes                                          |
|----------------------|----------|----------------|----------------------|-------------|----------|---------|------------------------------------------------|
| nRF51 (ESB)          | 2.4 GHz  | 10-30m         | ~50-100m             | 1 Mbps      | 2-5 ms   | ~15 mW  | Stock Crazyflie radio. Point-to-point only.    |
| ESP32 (Wi-Fi)        | 2.4 GHz  | 20-50m         | ~100-200m            | 1-10 Mbps   | 5-20 ms  | ~200 mW | On AI-deck. ESP-NOW for low-latency P2P.       |
| DW1000 (UWB)         | 3.5-6.5 GHz | 10-20m      | ~50-100m             | 850 Kbps-6.8 Mbps | 1-5 ms | ~50 mW  | Loco Positioning deck. Ranging + data.         |
| nRF52840 (BLE Mesh)  | 2.4 GHz  | 10-30m         | ~50-100m             | 2 Mbps      | 5-15 ms  | ~10 mW  | Would need custom deck. Native mesh support.   |
| LoRa (SX1276)        | 868/915 MHz | 100-500m   | **2-15 km**          | 0.3-50 Kbps | 50-500 ms | ~30 mW | Long range but too slow for real-time routing. |

**Best fit for MoE routing:** UWB (DW1000) or ESP-NOW.
- UWB gives you ranging + data in one radio — you get relative positioning (needed for swarm coordination) and feature-vector transport simultaneously.
- ESP-NOW (ESP32 peer-to-peer mode) is already on the AI-deck, needs no extra hardware, and has adequate bandwidth. Latency is higher than UWB.

## Mesh Network Range: Upper Bound Estimate

### Single-Hop Range

For a Crazyflie-class nano-drone operating outdoors with line-of-sight:

**2.4 GHz (ESB / ESP-NOW / BLE):**
- TX power: 0-4 dBm (typical for these radios)
- Receiver sensitivity: -90 to -96 dBm
- Link budget: ~94-100 dB
- Free-space path loss at 2.4 GHz: `FSPL(dB) = 20*log10(d) + 20*log10(f) + 20*log10(4pi/c)`
- At 100m: FSPL = 80 dB (well within budget)
- At 300m: FSPL = 90 dB (marginal)
- At 500m: FSPL = 94 dB (at limit)
- **Practical single-hop max (outdoor LOS): ~100-200m**
- **Practical single-hop max (indoor): ~20-50m**

**UWB (DW1000, channel 5, 6.5 GHz):**
- TX power: -14 dBm (regulatory limit)
- Receiver sensitivity: -105 dBm (at 850 Kbps)
- Link budget: ~91 dB
- FSPL at 6.5 GHz is ~8.6 dB higher than at 2.4 GHz for the same distance
- **Practical single-hop max (outdoor LOS): ~50-100m**
- **Practical single-hop max (indoor): ~10-20m**

**LoRa (irrelevant for MoE routing but included for reference):**
- TX power: 14-20 dBm
- Receiver sensitivity: -137 dBm
- Link budget: ~157 dB
- **Practical single-hop max (outdoor LOS): 2-15 km**
- Latency makes it unusable for real-time routing, but interesting for slow-loop swarm coordination.

### Multi-Hop Mesh: Upper Bound

For a mesh with N drones acting as relays, the theoretical max range is `N * single_hop_range`. But each hop adds latency and reduces reliability.

**Latency constraint determines max hops:**
- Available routing latency: ~40ms
- Per-hop latency (TX + RX + processing): ~5-10ms for UWB, ~10-20ms for ESP-NOW
- **Max hops within latency budget:** 2-4 hops (UWB), 1-2 hops (ESP-NOW)

**Upper bound mesh range (outdoor LOS):**

| Radio     | Single Hop | Max Hops (latency-limited) | Mesh Range Upper Bound |
|-----------|-----------|---------------------------|----------------------|
| ESP-NOW   | ~150m     | 2                         | **~300m**            |
| UWB       | ~75m      | 4                         | **~300m**            |
| ESB       | ~100m     | 3                         | **~300m**            |

They converge around **~300m** because the latency budget and single-hop range trade off against each other. Longer-range radios have higher latency; shorter-latency radios have shorter range.

**Upper bound mesh range (indoor):**

| Radio     | Single Hop | Max Hops (latency-limited) | Mesh Range Upper Bound |
|-----------|-----------|---------------------------|----------------------|
| ESP-NOW   | ~30m      | 2                         | **~60m**             |
| UWB       | ~15m      | 4                         | **~60m**             |

Again convergent: **~60m indoor**, which is roughly "one large building floor."

### Relaxing the Latency Constraint

If you drop to 5 Hz inference (200ms budget) or use asynchronous/pipelined routing (frame N's result arrives during frame N+1's backbone pass), you can afford more hops:

| Scenario                     | Latency Budget | Max Hops (UWB) | Outdoor Range |
|------------------------------|---------------|-----------------|--------------|
| 10 Hz, synchronous           | 40 ms         | 4               | ~300m        |
| 5 Hz, synchronous            | 100 ms        | 10              | ~750m        |
| 10 Hz, pipelined (1-frame)   | 140 ms        | 14              | **~1 km**    |
| 2 Hz, synchronous            | 300 ms        | 30              | **~2 km**    |

**Absolute upper bound with pipelining on UWB: ~1 km outdoor.** Beyond that, you're either flying too slowly to need 10 Hz perception or the mesh topology itself becomes fragile (drones must maintain relay chains).

## Key Takeaways

1. **Bandwidth is not the bottleneck.** A 5-drone MoE swarm needs ~20 KB/s aggregate — any radio can handle this.

2. **Latency is the bottleneck.** The ~40ms routing budget limits you to 2-4 hops, capping mesh range at ~300m outdoor / ~60m indoor for real-time (10 Hz) operation.

3. **UWB is the best radio for MoE routing** because it gives ranging + data, has the lowest per-hop latency, and the Crazyflie Loco Positioning deck already exists. You get swarm-relative positioning for free.

4. **The ~300m outdoor / ~60m indoor envelope is adequate** for the target use cases: indoor warehouse inspection, indoor search, and small outdoor formations. It covers the same operational envelope as the drone's flight time (~7 min on a Crazyflie).

5. **For the sim (v2-v3), model the channel as:** fixed bandwidth cap (1 Mbps shared), 5-10ms per-hop latency, max 2-4 hops, no packet loss (per the simplification from chats.md). This captures the binding constraints without over-engineering.

## Open Questions

- Can we piggyback feature vectors onto UWB ranging packets (they already exchange timestamps — is there room for 128 extra bytes)?
- What's the MAC protocol for a 5-drone mesh with mixed ranging + data traffic? TDMA with fixed slots per drone, or contention-based?
- Does pipelined routing (use stale expert results) degrade MoE accuracy meaningfully, or is visual perception smooth enough that one-frame-old results are fine?
- Power: UWB at ~50 mW continuous is ~50% of the AI-deck compute budget. Is this acceptable on a 250 mAh battery?

## Sources

- Crazyflie 2.1 + AI-deck specs: [../specs/01-crazyflie-2.1.md](../specs/01-crazyflie-2.1.md)
- MoE architecture discussion: [../moe/chats.md](../moe/chats.md)
- DW1000 datasheet: Decawave DW1000 (UWB transceiver)
- ESP-NOW protocol: Espressif ESP-NOW (peer-to-peer over ESP32)
- Free-space path loss formula: `FSPL(dB) = 20*log10(d_m) + 20*log10(f_Hz) - 147.55`
