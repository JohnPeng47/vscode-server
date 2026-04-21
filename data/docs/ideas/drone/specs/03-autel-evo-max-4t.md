# Autel EVO Max 4T

> Mid-size enterprise drone with multi-sensor payload

## Classification
- **Category:** Enterprise inspection / public safety
- **Manufacturer:** Autel Robotics
- **Price:** ~$9,000-$12,000
- **Use case:** Public safety, inspection, search & rescue, mapping

## Physical
- **Weight (with battery + propellers):** 1640g (3.62 lbs)
- **Max takeoff weight:** 1999g (4.41 lbs)
- **Payload capacity:** ~359g (MTOW - aircraft weight)
- **Form factor:** Foldable quadrotor

## Flight Performance
- **Flight time:** 42 min max
- **Max speed:** Not specified in public specs (estimated ~20 m/s)
- **Max wind resistance:** ~12 m/s (estimated, enterprise class)

## Battery
- **Type:** Proprietary intelligent battery
- **Capacity:** Not publicly disclosed (estimated ~5000-6000 mAh based on class)
- **Voltage:** Estimated ~14.4-15.4V (4S LiPo)
- **Energy:** Estimated ~70-90 Wh (based on weight class and flight time)
- **Controller battery life:** 4.5 hours continuous

## Onboard Compute
- **Processor:** Not publicly disclosed
- **Inference capability:** Runs AI-powered subject detection, tracking, thermal analytics, 160x hybrid zoom processing — implies significant onboard compute (likely Ambarella or similar vision SoC)
- **Video processing:** 8K video encoding (48MP zoom camera)

## Sensors
- **Zoom camera:** 48MP, 8K, 10x optical / 160x hybrid zoom
- **Wide-angle camera:** 50MP
- **Thermal camera:** 640x512 uncooled VOx, -20°C to 550°C measurement range, 16x digital zoom
- **Laser rangefinder:** Integrated
- **Obstacle avoidance:** Omnidirectional

## Comms
- **Video transmission:** Proprietary, likely SkyLink-based
- **Range:** Estimated 15+ km (FCC)

## Power Budget Estimate (for compute)
- **Total battery energy:** ~70-90 Wh (estimated)
- **Total system power (hovering):** ~50-80W estimate
- **Compute power draw:** Likely 5-10W (multi-camera ISP + AI inference + thermal processing)
- **Available headroom:** ~5-15W potentially available for additional compute payloads

## Key Constraints for MoE
- **Limited external payload:** ~359g available
- **Compute allocation:** Could theoretically support a Jetson Orin Nano (7-15W, ~50g module) within power and weight budget
- **Theoretical model budget:** With ~8-16 GB memory on Orin Nano class, could host experts in the 1M-50M parameter range per expert

## Sources
- https://www.autelrobotics.com/productdetail/evo-max-4t/
