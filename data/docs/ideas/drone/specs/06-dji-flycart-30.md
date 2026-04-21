# DJI FlyCart 30

> Heavy-lift delivery drone — maximum payload and power budget

## Classification
- **Category:** Heavy-lift cargo/delivery drone
- **Manufacturer:** DJI
- **Price:** ~$12,500-$17,000
- **Use case:** Cargo delivery, emergency supply drops, logistics
- **IP rating:** IP55

## Physical
- **Weight (without battery):** 42.5 kg
- **Weight (with 2x DB2000 batteries):** 65 kg
- **Max takeoff weight:** 95 kg (with 30kg cargo, dual battery)
- **Max payload:** 30 kg (dual battery), 40 kg (single battery)
- **Dimensions (fully unfolded):** 2800 x 3085 x 947 mm
- **Dimensions (fully folded):** 1115 x 760 x 1027 mm
- **Diagonal wheelbase:** 2200 mm
- **Rotors:** 8 (coaxial quad configuration)
- **Propeller diameter:** 54 inch / 1375 mm (carbon fiber, foldable)

## Flight Performance
- **Flight time (30kg load, dual battery):** 18 min
- **Flight time (empty, dual battery):** 29 min (hover)
- **Flight distance (30kg load, dual battery):** 16 km
- **Flight distance (empty, dual battery):** 28 km
- **Max horizontal speed:** 20 m/s / 72 km/h
- **Max ascent speed:** 5 m/s
- **Max descent speed:** 3 m/s (vertical), 5 m/s (tilted)
- **Max pitch angle:** 30°
- **Max altitude:** 6,000m (without payload)
- **Max wind resistance:** 12 m/s
- **Operating temperature:** -20°C to 45°C

## Propulsion
- **Motor stator size:** 100 x 33 mm
- **Motor KV:** 48 rpm/V
- **Max motor power:** 4,000W per rotor → **32,000W total (8 rotors)**

## Battery (DB2000 x2)
- **Capacity:** 38,000 mAh per battery
- **Voltage:** 52.22V nominal (14S1P)
- **Energy:** 1,984.4 Wh per battery → **3,968.8 Wh total (dual battery)**
- **Weight:** ~11.3 kg per battery → 22.6 kg total
- **Charging rate:** 1.0C (5-15°C), 2.5C (15-45°C)
- **Max charging power:** 5,700W
- **Operating temperature:** -20°C to 45°C
- **Auto-heating:** Supported

## Onboard Compute
- **Processor:** Not publicly disclosed
- **Video transmission:** DJI O3
- **FPV camera:** 1920x1440, 149° DFOV, 30fps, single-axis gimbal
- **Sensing:** Binocular vision (90° H x 106° V FOV) + forward/backward radar
- **Radar forward:** Detection range 1.5-200m
- **Radar rear:** Detection range 1.5-50m

## Positioning
- **GNSS:** GPS L1/L2, Galileo F1/F2, BeiDou B1I/B2I/B3I, QZSS L1/L2
- **RTK accuracy:** ±10cm horizontal, ±10cm vertical
- **ADS-B:** Supported

## Comms
- **Video transmission:** DJI O3
- **Range:** 20 km (FCC), 8 km (CE)
- **Frequencies:** 2.4 GHz, 5.8 GHz
- **Encryption:** AES-256
- **Dual operator mode:** Supported

## Cargo Systems
- **Cargo case:** 573 x 416 x 305 mm interior, EPP + aluminum, ~3kg, 0-40kg capacity
- **Parachute:** Included, ~2.1kg, max 95kg, ~22m² canopy, <6 m/s descent
- **Winch (optional):** 20m cable, 5-40kg capacity, 0.8 m/s retraction

## Power Budget (for compute)
- **Total battery energy:** 3,968.8 Wh (dual DB2000)
- **Total system power (hovering, 30kg load):** ~13,000W estimate (3969Wh / 18min × 60)
- **Total system power (hovering, empty):** ~8,200W estimate
- **Compute power draw (avionics):** ~20-40W estimated
- **Available for payload compute:** Enormous — with 30kg payload budget and ~4kWh battery, could easily support 100-200W+ compute payload with negligible flight time impact

## Key Parameters for MoE Analysis
- **Payload weight budget:** 30 kg (!!)
- **Payload power budget:** 100-200W+ easily available
- **If equipped with NVIDIA Jetson AGX Orin 64GB (60W):**
  - 275 TOPS (INT8)
  - 64 GB LPDDR5 memory
  - Weight: ~700g with carrier board — trivial vs 30kg budget
  - Could host ~30B parameter INT8 model per drone
  - Per-expert budget (8 experts): ~3-4B params each
- **If equipped with multiple Orin modules or an NVIDIA A2/L4 (40-75W):**
  - Could potentially host GPU-class inference (L4: 31 TFLOPS FP16, 24GB)
  - Weight ~1-2kg with cooling — still small vs payload budget
  - Per-expert could be 5-10B+ params
- **If equipped with Qualcomm Cloud AI 100 (25W):**
  - 400+ TOPS (INT8)
  - 16 GB on-chip
  - Could host very large experts
- **Inter-drone bandwidth:** DJI O3 + could carry custom high-power radio
- **Key insight:** Power and weight are NOT the constraint at this scale. The constraint shifts to inter-drone communication bandwidth and flight time (only 18min loaded).

## Sources
- https://www.dji.com/flycart-30/specs
- https://drdrone.ca/pages/dji-flycart-30-technical-specifications
