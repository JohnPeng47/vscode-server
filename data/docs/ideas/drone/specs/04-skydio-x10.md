# Skydio X10

> Mid-size autonomous drone — the most compute-dense commercial drone available

## Classification
- **Category:** Enterprise autonomous drone (inspection, public safety, DFR)
- **Manufacturer:** Skydio (San Mateo, CA — designed & assembled in USA)
- **Price:** ~$12,000-$18,000
- **Use case:** Drone-as-First-Responder, infrastructure inspection, mapping, public safety
- **NDAA compliant**

## Physical
- **Weight (with battery):** 2.11 kg / 4.65 lbs (Connect SL), 2.14-2.16 kg (5G)
- **Max takeoff weight:** 2.49 kg / 5.49 lbs
- **Dimensions (unfolded, with propellers):** 790 x 650 x 145 mm
- **Dimensions (folded):** 350 x 165 x 119 mm
- **Payload capacity:** ~340g (MTOW - aircraft weight)
- **Startup time:** Under 40 seconds
- **IP rating:** IP55

## Flight Performance
- **Flight time:** 40 min max
- **Hover time:** 35 min
- **Max horizontal speed:** 20 m/s / 45 mph
- **Max ascent speed:** 6 m/s
- **Max descent speed:** 4 m/s (vertical), 6 m/s (non-vertical)
- **Max tilt angle:** 40°
- **Max angular velocity:** Yaw 100°/s, Roll/Pitch 225°/s
- **Max wind handling:** 12.8 m/s / 28.6 mph gusts
- **Max ceiling:** 4,572m / 15,000 ft
- **Obstacle avoidance:** True 360°, max 16 m/s with standard OA
- **Operating temperature:** -20°C to +45°C

## Battery
- **Rev 1:** 8419 mAh, 18.55V, 156.17 Wh, ~707.5g, LiPo
- **Rev 2:** 8800 mAh, 17.5V, 154 Wh, ~685g, Li-ion
- **Charging time:** ~1 hour (230W charger), ~1h47m (100W)
- **Operating temp:** -20°C to 60°C

## Onboard Compute ← KEY DIFFERENTIATOR
- **Primary AI processor:** NVIDIA Jetson Orin SoC
  - Variant not publicly disclosed (likely Orin NX 16GB based on SWaP constraints)
  - Jetson Orin NX specs: up to 100 TOPS (INT8), 8-16 GB LPDDR5, 10-25W configurable
  - Jetson AGX Orin specs: up to 275 TOPS (INT8), 32-64 GB LPDDR5, 15-60W configurable
- **Secondary processor:** Qualcomm Snapdragon 865 SoC (QRB5165)
  - Adreno 650 GPU (used for thermal ISP pipeline)
  - Kryo 585 CPU, up to 2.84 GHz
  - Hexagon 698 DSP
  - 5th gen Qualcomm AI Engine (~15 TOPS)
- **Combined AI compute:** Likely 100-115+ TOPS
- **Image processing:** Adreno 650 GPU accelerated ISP pipeline (thermal)

## Sensors (6 navigation cameras + 4 payload cameras)
### Navigation
- **Configuration:** 6x cameras in trinocular config (top + bottom)
- **Sensor:** Samsung 1/2.8" 32MP color CMOS
- **FOV:** 200° diagonal per camera
- **Aperture:** f/1.8
- **Obstacle sensing range:** 20m

### Wide Camera
- **Sensor:** 1" 50.3MP CMOS, f/1.95, 93° DFOV, 20mm equiv

### Telephoto Camera
- **Sensor:** 0.5" 48MP CMOS, f/2.2, 13° DFOV, 190mm equiv

### Narrow Camera
- **Sensor:** 1/1.7" 64MP CMOS, f/1.8, 50° DFOV, 46mm equiv

### Thermal Camera
- **Imager:** FLIR Boson+ uncooled VOx microbolometer
- **Resolution:** 640x512, 12μm pixel pitch
- **NETD:** <30mK
- **FOV:** 41° DFOV
- **Temperature range:** -40°C to 150°C (high gain), -40°C to 350°C (low gain)

## Comms
- **Connect SL:** WiFi 6 (2.4/5 GHz), range 12km LOS
- **Connect 5G:** Cellular LTE/5G, unlimited range with coverage
- **Encryption:** AES-256
- **Antennas:** 2Tx, 4Rx

## Power Budget (for compute)
- **Total battery energy:** ~154-156 Wh
- **Total system power (hovering):** ~150-200W estimate (based on 35min hover / 154Wh)
- **Compute power draw (Jetson Orin NX @ 25W + QRB5165 @ ~10W):** ~35W
- **Compute as % of total power:** ~17-23%
- **Available for additional compute payload:** Limited — system already runs hot compute budget

## Key Parameters for MoE Analysis
- **Memory available for models:** 8-16 GB (Orin NX) + ~8 GB (QRB5165) = 16-24 GB total
- **AI throughput:** ~100-115 TOPS (INT8)
- **Max model size (FP16):** Could host 4-8B parameter model in memory
- **Max model size (INT8):** Could host 8-16B parameter model in memory
- **Per-expert budget (8 experts, INT8):** ~1-2B params per expert (1-2 GB each)
- **Inter-drone bandwidth:** 12km range WiFi 6, theoretical ~1 Gbps short-range
- **Latency budget:** With 360° OA running, ~100-200ms available for MoE routing
- **Power per TOPS:** ~0.3W/TOPS (very efficient)

## Sources
- https://www.skydio.com/x10/technical-specs
- https://www.skydio.com/x10
