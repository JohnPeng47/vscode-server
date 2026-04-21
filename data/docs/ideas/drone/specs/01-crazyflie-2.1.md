# Crazyflie 2.1 + AI-deck v1.1

> Nano research quadrotor — the baseline from the MoE chat (PULP-Dronet platform)

## Classification
- **Category:** Nano research drone
- **Manufacturer:** Bitcraze (Sweden)
- **Price:** ~$230 (drone) + ~$125 (AI-deck) = ~$355 total
- **Use case:** Indoor research, swarm experiments, tinyML development

## Physical
- **Weight (drone only):** 29g
- **Weight (drone + AI-deck):** ~33g
- **Dimensions:** 92 x 92 x 29 mm
- **Max recommended payload:** 15g
- **Max takeoff weight:** ~44g (with 15g payload)

## Flight Performance
- **Flight time:** ~7 min (250mAh battery)
- **Max speed:** ~2-3 m/s (typical research use)
- **Max altitude:** Indoor only (no GPS)

## Battery
- **Capacity:** 250 mAh
- **Voltage:** 3.7V nominal (1S LiPo)
- **Energy:** ~0.93 Wh
- **Charging time:** ~40 min

## Onboard Compute (Main MCU)
- **Processor:** STM32F405 (ARM Cortex-M4)
- **Clock:** 168 MHz
- **RAM:** 192 KB SRAM
- **Flash:** 1 MB
- **Role:** Flight controller, PID loops, state estimation

## Onboard Compute (AI-deck v1.1)
- **Processor:** GreenWaves GAP8 (RISC-V, 8+1 core)
- **AI performance:** ~10 GOPS
- **RAM:** 64 Mbit (8 MB) HyperRAM
- **Flash:** 512 Mbit (64 MB) HyperFlash
- **On-chip L2:** 512 KB
- **On-chip L1 (per cluster):** 64 KB
- **CNN accelerator:** Hardware Convolution Engine (HWCE)
- **Power consumption:** <100 mW (AI inference)
- **Weight:** 4.4g
- **Dimensions:** 30 x 52 x 8 mm
- **Camera:** Himax HM01B0 (320x320 monochrome)
- **Wi-Fi:** ESP32 (NINA-W102)

## Power Budget (for compute)
- **Total system power:** ~5-8W in flight (motors dominate)
- **Available for compute:** ~100-300 mW
- **AI-deck typical draw:** ~100 mW at inference

## Comms
- **Radio:** nRF51822 (Cortex-M0, BLE + proprietary 2.4GHz)
- **Range:** ~10-30m indoor
- **Data rate:** ~1 Mbps (ESB mode)
- **Wi-Fi (via AI-deck):** ESP32, 802.11 b/g/n

## Key Constraints for MoE
- **Max model size per drone:** ~200-500 KB (8-bit quantized, fits in GAP8 L2+Flash)
- **Inference latency budget:** 50-100ms per frame
- **Inter-drone bandwidth:** ~1-2 Mbps shared channel
- **Power for compute:** ~100-300 mW absolute max

## Sources
- https://www.bitcraze.io/products/crazyflie-2-1-plus/
- https://www.bitcraze.io/products/ai-deck/
- https://www.bitcraze.io/documentation/hardware/crazyflie_2_1/crazyflie_2_1-datasheet.pdf
