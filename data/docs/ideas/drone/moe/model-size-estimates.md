# MoE Model Size Estimates by Drone Class & Swarm Size

> For each drone class, we estimate what compute module could plausibly be carried,
> then derive the per-expert size and total swarm MoE model capacity at N=5, 10, 20.

## Assumptions

- **Quantization:** INT8 (1 byte per parameter) unless noted
- **MoE structure:** shared backbone (replicated on every drone) + 1 expert per drone + router (replicated, negligible size)
- **Routing:** top-1 (each input activates exactly 1 expert)
- **Active params per inference** = backbone + 1 expert (what any single drone computes)
- **Total params** = backbone + N × expert_size (the "virtual model" the swarm collectively hosts)
- **Memory allocation:** ~60% of available memory for model weights (rest for activations, runtime, OS)
- **Backbone:** ~20% of per-drone model memory budget
- **Expert:** ~80% of per-drone model memory budget

---

## 1. Crazyflie 2.1 + AI-deck (33g)

### Compute module
GAP8 RISC-V (already onboard). No room to add anything else.

| Spec | Value |
|------|-------|
| Usable memory for model | ~400 KB (from 512KB L2 + paging from 64MB HyperFlash) |
| Compute | ~10 GOPS |
| Power for inference | ~100 mW |
| Backbone size | ~80 KB → **80K params** |
| Expert size | ~320 KB → **320K params** |
| Router | ~3 KB → 3K params |
| Active params (per inference) | **~400K** |

| Swarm size | Total experts | Total MoE params | Equivalent dense model |
|-----------|--------------|-------------------|----------------------|
| 5 drones | 5 | 80K + 5 × 320K = **1.68M** | ~4× larger than what fits on one drone |
| 10 drones | 10 | 80K + 10 × 320K = **3.28M** | ~8× larger |
| 20 drones | 20 | 80K + 20 × 320K = **6.48M** | ~16× larger |

**Context:** A single Crazyflie can host ~400K params. A 20-drone swarm collectively hosts 6.5M — comparable to a small MobileNet. The per-inference compute is still only 400K params (fast), but the swarm has 16× the specialization capacity.

**Bottleneck:** Inter-drone bandwidth (~1-2 Mbps shared). Routing a 128-byte feature vector at 10Hz = ~10 kbps per route — feasible even at 20 drones if routing is sparse.

---

## 2. DJI Mini 4 Pro class (249g)

### Theoretical compute module
This is a closed platform, so we estimate what a **custom 250g-class drone** could carry.
Best fit: **Hailo-8** (26 TOPS, 2.5W, <10g) or **Google Coral Edge TPU** (4 TOPS, 2W, <5g) with external 1-2GB LPDDR4.

| Spec | Value |
|------|-------|
| Plausible compute module | Hailo-8 (26 TOPS, 2.5W) |
| Usable memory for model | ~600 MB (from ~1 GB LPDDR4, 60% for weights) |
| Power for inference | ~2.5W |
| Backbone size | ~120 MB → **120M params** |
| Expert size | ~480 MB → **480M params** |
| Router | ~1 MB → 1M params |
| Active params (per inference) | **~600M** |

| Swarm size | Total experts | Total MoE params | Equivalent dense model |
|-----------|--------------|-------------------|----------------------|
| 5 drones | 5 | 120M + 5 × 480M = **2.52B** | ~4× larger than one drone |
| 10 drones | 10 | 120M + 10 × 480M = **4.92B** | ~8× larger |
| 20 drones | 20 | 120M + 20 × 480M = **9.72B** | ~16× larger |

**Context:** A single 250g drone could run a ~600M model (think EfficientNet-L2 or a small ViT). A 20-drone swarm collectively hosts ~10B params — approaching GPT-2-XL territory, but for vision. Active compute per inference is still only 600M (real-time capable on Hailo-8).

**Bottleneck:** Power. 2.5W compute on a ~19Wh battery is ~13% of power budget. Flight time drops from ~34min to ~30min. Acceptable.

---

## 3. Autel EVO Max 4T class (1.6kg)

### Theoretical compute module
Weight budget: ~360g. Power budget: ~5-15W.
Best fit: **Jetson Orin Nano 8GB** (40 TOPS, 7-15W, ~50g with carrier).

| Spec | Value |
|------|-------|
| Compute module | Jetson Orin Nano 8GB |
| Compute | 40 TOPS (INT8) |
| Usable memory for model | ~4.8 GB (from 8GB LPDDR5, 60% for weights) |
| Power for inference | ~10W |
| Backbone size | ~960 MB → **960M params** |
| Expert size | ~3.84 GB → **3.84B params** |
| Router | ~5 MB → 5M params |
| Active params (per inference) | **~4.8B** |

| Swarm size | Total experts | Total MoE params | Equivalent dense model |
|-----------|--------------|-------------------|----------------------|
| 5 drones | 5 | 960M + 5 × 3.84B = **20.2B** | ~4× larger than one drone |
| 10 drones | 10 | 960M + 10 × 3.84B = **39.4B** | ~8× larger |
| 20 drones | 20 | 960M + 20 × 3.84B = **77.8B** | ~16× larger |

**Context:** A single 1.6kg drone could run a ~4.8B model (think LLaMA-3B or a large vision model). A 20-drone swarm hosts ~78B — Mixtral-8x7B territory. Per-inference is only 4.8B active params.

**Bottleneck:** Memory bandwidth on the Orin Nano (~68 GB/s). At 4.8B INT8 params, a single forward pass reads ~4.8GB — achievable in ~70ms. Leaves room for ~14 inferences/sec. Fine for 10Hz perception.

---

## 4. Skydio X10 class (2.1kg)

### Compute module
Already has **Jetson Orin SoC + Qualcomm Snapdragon 865**. No need to add anything — this is the reference "compute-dense" drone.

| Spec | Value |
|------|-------|
| Compute module | Jetson Orin (likely NX 16GB) + QRB5165 |
| Compute | ~100-115 TOPS (INT8) combined |
| Usable memory for model | ~9.6 GB (from ~16GB, 60% for weights) |
| Power for inference | ~35W |
| Backbone size | ~1.9 GB → **1.9B params** |
| Expert size | ~7.7 GB → **7.7B params** |
| Router | ~10 MB → 10M params |
| Active params (per inference) | **~9.6B** |

| Swarm size | Total experts | Total MoE params | Equivalent dense model |
|-----------|--------------|-------------------|----------------------|
| 5 drones | 5 | 1.9B + 5 × 7.7B = **40.4B** | ~4× larger than one drone |
| 10 drones | 10 | 1.9B + 10 × 7.7B = **78.9B** | ~8× larger |
| 20 drones | 20 | 1.9B + 20 × 7.7B = **155.9B** | ~16× larger |

**Context:** A single Skydio-class drone runs ~9.6B active params (think LLaMA-7B INT8). A 20-drone swarm collectively hosts ~156B params — larger than GPT-3 (175B dense), achieved with only 9.6B active compute per inference. This is genuinely interesting.

**Bottleneck:** Inter-drone latency. WiFi 6 gives ~1 Gbps short-range. Routing a 2KB feature vector takes <0.02ms. But round-trip (send feature + receive result) adds ~5-15ms over-the-air. At 10Hz perception that's 50-150ms of your 100ms budget — tight but feasible with top-1 routing.

---

## 5. DJI Matrice 350 RTK class (6.5kg)

### Theoretical compute module
Weight budget: 2.73kg. Power budget: ~30-60W.
Best fit: **Jetson AGX Orin 64GB** (275 TOPS, 60W, ~700g with carrier + cooling).

| Spec | Value |
|------|-------|
| Compute module | Jetson AGX Orin 64GB |
| Compute | 275 TOPS (INT8) |
| Usable memory for model | ~38 GB (from 64GB LPDDR5, 60% for weights) |
| Power for inference | ~50W |
| Backbone size | ~7.6 GB → **7.6B params** |
| Expert size | ~30.4 GB → **30.4B params** |
| Router | ~20 MB → 20M params |
| Active params (per inference) | **~38B** |

| Swarm size | Total experts | Total MoE params | Equivalent dense model |
|-----------|--------------|-------------------|----------------------|
| 5 drones | 5 | 7.6B + 5 × 30.4B = **159.6B** | ~4× larger than one drone |
| 10 drones | 10 | 7.6B + 10 × 30.4B = **311.6B** | ~8× larger |
| 20 drones | 20 | 7.6B + 20 × 30.4B = **615.6B** | ~16× larger |

**Context:** A single M350-class drone runs ~38B active params — competitive with Mixtral-8x7B's active compute. A 20-drone swarm hosts ~616B total params. That's larger than any single commercially deployed model as of 2026 in terms of total parameter count, with only 38B active per inference.

**Bottleneck:** Flight time. 50W compute on a 526Wh battery steals ~10% of power → flight time drops from 55min to ~50min. Acceptable for most missions. Communication bandwidth becomes the real constraint for sharing large activations across drones.

---

## 6. DJI FlyCart 30 class (65kg)

### Theoretical compute module
Weight budget: 30kg (!!). Power budget: 100-200W+.
Best fit: **2× Jetson AGX Orin 64GB** (550 TOPS total, ~120W, ~1.5kg) or **NVIDIA L4 GPU** (31 TFLOPS FP16, 24GB, 72W, ~1kg).

| Spec | Value |
|------|-------|
| Compute module | 2× Jetson AGX Orin 64GB |
| Compute | 550 TOPS (INT8) |
| Usable memory for model | ~77 GB (from 128GB total, 60% for weights) |
| Power for inference | ~120W |
| Backbone size | ~15 GB → **15B params** |
| Expert size | ~62 GB → **62B params** |
| Router | ~50 MB → 50M params |
| Active params (per inference) | **~77B** |

| Swarm size | Total experts | Total MoE params | Equivalent dense model |
|-----------|--------------|-------------------|----------------------|
| 5 drones | 5 | 15B + 5 × 62B = **325B** | ~4× larger than one drone |
| 10 drones | 10 | 15B + 10 × 62B = **635B** | ~8× larger |
| 20 drones | 20 | 15B + 20 × 62B = **1.255T** | ~16× larger |

**Context:** A single FlyCart-class drone runs ~77B active params — LLaMA-70B territory. A 20-drone swarm hosts **1.26 trillion params** — approaching GPT-4-class parameter counts. Per-inference compute is 77B active, which is already substantial.

**Bottleneck:** NOT compute or power. The constraint flips entirely to **flight time** (18min loaded) and **inter-drone bandwidth**. At this scale, the MoE routing overhead is negligible but you can only fly for 18 minutes. Also, 20 FlyCart 30s cost ~$250K-$340K in hardware alone.

---

## Summary Table

### Per-drone active parameters (what runs per inference)

| Drone class | Weight | Compute chip | Active params | Comparable to |
|------------|--------|-------------|---------------|--------------|
| Crazyflie 2.1 | 33g | GAP8 | 400K | Tiny custom CNN |
| Mini 4 Pro class | 249g | Hailo-8 | 600M | EfficientNet-L2 |
| EVO Max 4T class | 1.6kg | Orin Nano 8GB | 4.8B | LLaMA-3B |
| Skydio X10 class | 2.1kg | Orin NX 16GB | 9.6B | LLaMA-7B |
| Matrice 350 class | 6.5kg | AGX Orin 64GB | 38B | Mixtral active |
| FlyCart 30 class | 65kg | 2× AGX Orin 64GB | 77B | LLaMA-70B |

### Total swarm MoE parameters

| Drone class | 5 drones | 10 drones | 20 drones |
|------------|----------|-----------|-----------|
| Crazyflie 2.1 | 1.7M | 3.3M | 6.5M |
| Mini 4 Pro class | 2.5B | 4.9B | 9.7B |
| EVO Max 4T class | 20B | 39B | 78B |
| Skydio X10 class | 40B | 79B | 156B |
| Matrice 350 class | 160B | 312B | 616B |
| FlyCart 30 class | 325B | 635B | 1.26T |

### The scaling insight

The ratio is always ~N:1 (total params : active params) because each drone adds one expert. But the absolute numbers shift dramatically:

- **Nano scale (Crazyflie):** Even 20 drones only reach 6.5M. This is "mixture of tiny specialists" — useful for multi-modal perception but not for general intelligence. The research question is whether MoE even helps at this scale (this is the v1 experiment from the chat).

- **Small scale (250g-2kg):** 5-10 drones reach 2.5B-79B total. This is the **sweet spot** for the MoE-on-drones idea — the swarm collectively hosts a model that no single drone could run, and the per-drone compute is fast enough for real-time perception. A 10-drone Skydio swarm at 79B total params is genuinely impressive.

- **Large scale (6.5kg+):** 10-20 drones reach 300B-1.26T. At this point you're hosting LLM-class parameter counts on flying hardware. The question shifts from "can we fit the model" to "what would we even DO with a trillion-parameter vision model on 20 drones?" This is where the research framing needs to get creative — maybe multi-task generalist perception, maybe foundation-model-class scene understanding.

### The real bottleneck by scale

| Scale | Bottleneck | Why |
|-------|-----------|-----|
| Nano (33g) | Per-expert capacity | Experts are so small they may not meaningfully specialize |
| Small (250g-2kg) | Inter-drone bandwidth | Feature vectors are big, radio channels are shared |
| Medium (2-7kg) | Power budget / flight time | Compute eats into already-limited flight endurance |
| Heavy (65kg+) | Flight time & cost | 18min flights, $15K+ per drone, diminishing returns on model size |

### Implication for MoE research progression

| Phase | Drone class | Swarm | Total params | Research question |
|-------|------------|-------|-------------|-------------------|
| v1 | (Desktop, no drones) | N/A | N/A | Does MoE work at sub-1M expert scale? |
| v2 | Crazyflie sim | 5-10 | 1.7M-3.3M | Does comm-aware routing beat monolithic at nano scale? |
| v3 | 250g-2kg class sim | 5-10 | 2.5B-79B | Does distributed MoE scale with drone size? |
| v4 | Skydio/M350 real hw | 3-5 | 30B-160B | First-to-fly real MoE on real drones |
