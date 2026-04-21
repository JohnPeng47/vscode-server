# DJI Matrice 350 RTK

> Heavy enterprise workhorse — modular payload system, industrial-grade

## Classification
- **Category:** Heavy enterprise drone (inspection, mapping, surveying)
- **Manufacturer:** DJI Enterprise
- **Price:** ~$12,000-$18,000 (drone only, payloads extra)
- **Use case:** Professional surveying, infrastructure inspection, public safety, search & rescue
- **EU class:** C3

## Physical
- **Weight (without batteries):** ~3.77 kg
- **Weight (with 2x TB65 batteries):** ~6.47 kg
- **Max takeoff weight:** 9.2 kg
- **Dimensions (unfolded, no propellers):** 810 x 670 x 430 mm
- **Dimensions (folded, with propellers):** 430 x 420 x 430 mm
- **Diagonal wheelbase:** 895 mm
- **Payload capacity (single downward gimbal):** 960g
- **Payload capacity (max, with weight budget):** ~2.73 kg (MTOW - aircraft with batteries)
- **IP rating:** IP55
- **Motor model:** 2008

## Flight Performance
- **Flight time:** 55 min max (no payload, ~8 m/s, windless)
- **Max horizontal speed:** 23 m/s
- **Max ascent speed:** 6 m/s
- **Max descent speed:** 5 m/s (vertical), 7 m/s (tilted)
- **Max angular velocity:** Pitch 300°/s, Yaw 100°/s
- **Max pitch angle:** 30°
- **Max wind resistance:** 12 m/s
- **Max altitude:** 5,000m (standard propellers), 7,000m (high-altitude)
- **Operating temperature:** -20°C to 50°C

## Battery (TB65 Intelligent Flight Battery x2)
- **Capacity:** 5880 mAh per battery
- **Voltage:** 44.76V nominal
- **Energy:** 263.2 Wh per battery → **526.4 Wh total (dual battery)**
- **Type:** Li-ion
- **Weight:** ~1.35 kg per battery → 2.7 kg total
- **Charging time:** ~60 min (220V), ~70 min (110V)
- **Cycle life:** 400 cycles
- **Operating temperature:** -20°C to 50°C
- **Hot-swappable:** Yes (dual battery system)

## Onboard Compute
- **Processor:** Not publicly disclosed (DJI custom SoC)
- **Inference capability:** Runs DJI Pilot 2 with AI features, FPV processing, obstacle avoidance
- **FPV camera:** 1080p, 142° FOV, 30fps
- **Note:** The M350 is a payload platform — compute lives in the gimbal payloads (Zenmuse series)

### Supported Gimbal Payloads (with onboard compute)
- **Zenmuse H30/H30T:** Multi-sensor with AI detection, thermal, laser rangefinder
- **Zenmuse L2:** LiDAR + RGB mapping
- **Zenmuse P1:** Full-frame photogrammetry
- **DJI Dock 2 compatible:** For autonomous operations

## Positioning
- **GNSS:** GPS + GLONASS + BeiDou + Galileo
- **RTK accuracy:** ±1cm horizontal, ±1.5cm vertical (RTK Fix)
- **Hovering accuracy:** ±0.1m vertical (vision), ±0.3m horizontal (vision)

## Sensing / Obstacle Avoidance
- **Forward/Backward/Left/Right:** 0.7-40m range
- **Upward/Downward:** 0.6-30m range
- **FOV:** 65° horizontal, 50° vertical
- **Infrared:** 0.1-8m range

## Comms
- **Video transmission:** DJI O3 Enterprise
- **Range:** 20 km (FCC), 8 km (CE)
- **Frequencies:** 2.4 GHz, 5.15 GHz, 5.8 GHz
- **Antennas:** 4 video transmission, 2T4R
- **Wi-Fi:** Wi-Fi 6
- **Bluetooth:** 5.1
- **AES-256 encryption**

## Power Budget (for compute)
- **Total battery energy:** 526.4 Wh (dual TB65)
- **Total system power (hovering):** ~300-500W estimate (based on 55min flight / 526Wh)
- **Compute power draw (flight controller + avionics):** ~10-20W estimated
- **Available for payload compute:** Significant — with 2.73kg payload budget and 526Wh battery, could support 30-60W compute payload
- **Payload interface:** Proprietary gimbal port (power + data)

## Key Parameters for MoE Analysis
- **Payload weight budget:** 2.73 kg (enough for Jetson AGX Orin + cooling + carrier board)
- **Payload power budget:** ~30-60W available (conservative estimate)
- **If equipped with Jetson AGX Orin 64GB (60W):**
  - 275 TOPS (INT8)
  - 64 GB LPDDR5 memory
  - Could host a ~30B parameter INT8 model
  - Per-expert budget (8 experts): ~3-4B params each
- **If equipped with Jetson Orin NX 16GB (25W):**
  - 100 TOPS (INT8)
  - 16 GB LPDDR5
  - Could host ~8B parameter INT8 model
  - Per-expert budget (8 experts): ~1B params each
- **Inter-drone bandwidth:** WiFi 6 + DJI O3, potentially high short-range throughput
- **Flight time impact of compute:** Adding 30W compute reduces flight time by ~10-15%

## Sources
- https://enterprise.dji.com/matrice-350-rtk/specs
