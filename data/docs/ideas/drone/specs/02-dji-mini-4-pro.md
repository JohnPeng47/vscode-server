# DJI Mini 4 Pro

> Sub-250g consumer drone — lightest mainstream commercial platform

## Classification
- **Category:** Consumer camera drone (sub-250g)
- **Manufacturer:** DJI
- **Price:** ~$760-$960
- **Use case:** Aerial photography, recreation
- **EU class:** C0 (no registration needed in many jurisdictions)

## Physical
- **Weight (with battery):** <249g
- **Dimensions (folded):** 148 x 94 x 64 mm
- **Dimensions (unfolded):** 298 x 373 x 101 mm
- **Payload capacity:** ~0g (no external payload support; at weight limit already)

## Flight Performance
- **Flight time:** 34 min (standard battery), 45 min (Plus battery)
- **Max horizontal speed:** 16 m/s (S mode)
- **Max ascent speed:** 5 m/s
- **Max descent speed:** 5 m/s
- **Max altitude:** 4000m (standard), 3000m (Plus)
- **Max wind resistance:** 10.7 m/s
- **Max flight distance:** 18 km (standard), 25 km (Plus)

## Battery
- **Standard:** 2590 mAh, 7.32V nominal, 18.96 Wh, ~77.9g, Li-ion
- **Plus:** 3850 mAh, 7.38V nominal, 28.4 Wh, ~121g, Li-ion
- **Charging time:** 70 min (standard), 101 min (Plus)

## Onboard Compute
- **Processor:** Not publicly disclosed (likely Ambarella CV-series or similar)
- **Internal storage:** 2 GB
- **Video processing:** H.264/H.265 encoding up to 4K@100fps, 150 Mbps bitrate
- **Obstacle avoidance:** Omnidirectional binocular vision + 3D infrared
- **Inference capability:** Runs ActiveTrack, APAS (obstacle avoidance), subject tracking — implies moderate NN inference capability

## Sensors
- **Camera:** 1/1.3" CMOS, 48MP, f/1.7, 24mm equiv, 82.1° FOV
- **Video:** 4K@24/25/30/48/50/60/100fps, FHD@up to 200fps
- **Vision system:** Omnidirectional binocular (forward/backward/lateral/upward/downward)
- **3D infrared:** 0.1-8m range
- **GNSS:** GPS + Galileo + BeiDou

## Video Transmission
- **System:** DJI O4
- **Live view:** Up to 1080p/60fps
- **Range:** 20 km (FCC), 10 km (CE)
- **Latency:** ~120 ms
- **Frequencies:** 2.4 GHz, 5.1 GHz, 5.8 GHz
- **Antennas:** 4 antennas, 2T4R

## Power Budget Estimate (for compute)
- **Total battery energy:** ~19-28 Wh
- **Total system power (hovering):** ~15-20W estimate (motors + avionics)
- **Compute power draw:** Likely 2-5W (SoC + camera ISP + vision processing)
- **Available headroom for additional compute:** Near zero — weight-limited platform

## Key Constraints for MoE
- **No external payload:** Cannot add custom compute hardware
- **Onboard SoC:** Closed platform, no user-accessible compute
- **Relevance:** Represents the ~250g class power/compute envelope — any custom 250g drone with similar battery could allocate ~2-5W to a user-accessible compute module
- **Theoretical model budget:** If running on a Jetson Orin Nano-class (10W), would consume majority of power budget

## Sources
- https://www.dji.com/mini-4-pro/specs
