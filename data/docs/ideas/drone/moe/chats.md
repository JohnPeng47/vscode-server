# Neural network for drone swarm control

> Exported from [claude.ai](https://claude.ai/chat/1b44b521-0bee-4aa1-8782-e2283e106527) on 2026-04-20

---

## User *(4:00 PM)*

I want to build a neural network to control drone swarm. Where shud i start?

## Assistant

Great project. Swarm control sits at the intersection of multi-agent RL, control theory, and sim-to-real transfer, so the starting point depends on which part you want to own. Here are the three pillars that really define the problem and feed into each other:

1. Pick your control abstraction (this determines everything else)

You need to decide what the network actually outputs. The spectrum:

Low-level: motor thrusts / rotor RPMs → maximum agility, brutal sim-to-real gap, needs accurate aerodynamics model
Mid-level: body rates or thrust vectors → standard choice, pairs with a PID/geometric inner loop
High-level: waypoints or velocity setpoints → easy to train, but you're really just learning a planner and the "control" is done by PX4/Betaflight

For swarms, mid-level is almost always the right call. It keeps the neural net's job tractable (smooth, continuous, low-dim action space) while letting a well-understood controller handle attitude stabilization. This choice cascades into your sim fidelity requirements and your reward shaping.

2. Choose the multi-agent formulation

The central design question: is control centralized, decentralized, or CTDE (centralized training, decentralized execution)? CTDE is the dominant paradigm — MAPPO and QMIX are the workhorses — because at deployment each drone runs a local policy with only its own observations + neighbors, but during training the critic sees global state. This matters because it determines your observation space design: typically a local frame containing self-state + k-nearest-neighbor relative positions/velocities, which gives you permutation invariance and scales to arbitrary swarm sizes. If you want this to feel principled, look at graph neural network policies (GNN-based MARL) — they make the neighbor-aggregation structure explicit.

3. Simulator first, hardware much later

Start in Gym-PyBullet-Drones or Isaac Lab (GPU-parallelized, can run thousands of drones in parallel — huge for sample efficiency). Don't touch real hardware until you've solved formation flight, obstacle avoidance, and leader-follower in sim with domain randomization (mass, drag, wind, latency). The sim-to-real gap is where most projects die; randomization + a residual policy on top of a nominal controller is the standard recipe.

Concrete starting path: clone gym-pybullet-drones, get a single-drone hover working with PPO (SB3), then extend to 3-drone formation flight with shared-parameter MAPPO. That sequence will surface every real problem you'll face.

Want me to go deeper on any of these — the MARL algorithm choice, the observation/reward design, or the sim-to-real pipeline?

---

## User *(4:02 PM)*

Where is the “edge” of the problem for existing attempts?

## Assistant

Good question — this is where the field gets interesting. Let me search for the current frontier since this moves fast.

Let me also check for the very latest work on sim-to-real and large-swarm scaling, which are the hottest frontiers.

Good, I have a clear picture. Let me give you the three frontiers that matter.

The field has mostly solved the "middle": small swarms (3–20 drones) flying formations and avoiding each other in known environments, with policies that transfer to real hardware. That's Batra et al. 2022 and its descendants — decentralized policies trained via DRL with direct thrust control, demonstrated on teams up to 8 physical quadrotors 
Uscresl
. What's hard and unsolved clusters in three deeply connected areas:

1. Perception-in-the-loop at swarm scale (the vision bottleneck)

Almost every "impressive" swarm demo cheats by using motion capture — each drone gets godlike ground-truth state of itself and its neighbors from an external Vicon/OptiTrack system. The moment you require onboard perception (cameras, IMU, maybe a tiny depth sensor), everything breaks: drones have to simultaneously do VIO, estimate neighbors, avoid obstacles, AND cooperate, all on a <1W embedded processor. The 2025 Nature MI paper you might be interested in is the current high-water mark — they got there with a lightweight network running on a 12×16 depth map, trained via differentiable physics 
Techxplore
. But this is still small swarms in semi-structured environments. No one has a 50-drone swarm navigating a forest with onboard vision alone.

2. Scaling laws and emergent coordination failures

Training works beautifully at N=8. At N=50+, things subtly collapse: credit assignment becomes impossible (whose action caused the collision?), CTDE's centralized critic becomes a bottleneck, and policies overfit to specific swarm sizes. Permutation-invariant architectures (deep sets, attention, GNNs) help but don't solve it — the Batra architecture uses deep sets and attention encoders over neighborhood state 
ResearchGate
, and even then they're showing 8-drone deployments. The frontier question: can you train once on N=10 and zero-shot deploy on N=200? Current answer is "sort of, for simple tasks, in simulation." This ties directly to pillar 1 — as swarms grow, local-only observation becomes mandatory because global state is both unavailable and useless.

3. Adversarial and non-cooperative settings

Almost everything above assumes a cooperative swarm. The moment you add adversaries, non-stationarity explodes — your opponent is also learning, and the environment is no longer Markovian from any single agent's view. Pursuit-evasion with learning adversaries, counter-swarm defense, and swarm-vs-swarm engagements are where the theory gets thin. The recent counter-drone work notes that prior swarm RL work focuses on friendly-team coordination and low-level maneuvers, while adversarial contexts with malicious or non-cooperative UAVs remain under-explored 
arXiv
. This connects back to perception (you have to detect the adversary) and scale (adversarial dynamics get worse with more agents).

The interdependence is the whole game: onboard perception forces local observations, local observations enable scaling, and scaling is what you actually need for adversarial/real-world missions. A project that advances one of these in isolation is incremental; one that jointly attacks two is a genuine contribution.

Where do you want to plant your flag?

---

## User *(4:30 PM)*

So edge ml witj vision is pretty important?

## Assistant

Yes, it's arguably the bottleneck right now. Here's why it's so central:

The whole promise of swarms — scalability, decentralization, fault tolerance — collapses if each drone needs either (a) an external mocap system or (b) a data link to a beefy ground-station GPU. Both create single points of failure and hard scaling limits. Truly autonomous swarms need each drone to perceive, decide, and act locally. And "perceive" almost always means vision, because it's the only sensor modality that gives you rich environmental info (obstacles, neighbors, targets) at the weight/power budget a small quadrotor can carry.

The constraint triangle is brutal: a Crazyflie-class nano drone has roughly 150–200mW for compute, maybe a Cortex-M4 or at best a GAP8/Kendryte K210-tier chip, and needs to run its policy at 50–100Hz while also doing state estimation. You cannot run YOLOv8 or a ResNet on that. This is why the 2025 Nature MI work is a big deal — a 12×16 depth map is 192 pixels, which is the kind of input a tiny MLP can actually process in real time on-device. It's the "insect vision" paradigm: minimal sensing, minimal compute, clever learned policy doing the heavy lifting.

So the edge-ML-with-vision frontier is really about co-designing three things: the sensor (low-res depth, event cameras, tiny RGB), the network architecture (heavily quantized, pruned, often <100K params), and the training regime (differentiable physics, domain randomization, knowledge distillation from a bigger teacher policy). Event cameras are particularly interesting here because they're naturally sparse, low-power, and high-temporal-resolution — a good match for agile flight — but the learning algorithms for them are still immature.

If you want a concrete entry point: look at the PULP-Dronet line of work from ETH Zürich (they run CNN-based obstacle avoidance on a 64mW GAP8 chip on a Crazyflie) and the TinyML-on-MCU literature more broadly. That's the technical stack where you'd plant the flag.

---

## User *(4:36 PM)*

If you want a concrete entry point: look at the PULP-Dronet line of work from ETH Zürich (they run CNN-based obstacle avoidance on a 64mW GAP8 chip on a Crazyflie) and the TinyML-on-MCU literature more broadly. That’s the technical stack where you’d plant the flag.​​​​​​​​​​​​​​​​

Is there code?

## Assistant

Yes — PULP-Dronet is fully open-source. Let me pull the current state of the repos.

Yes, it's all open — and well-maintained. Here's the stack:

Main repo: github.com/pulp-platform/pulp-dronet (Apache-2.0)

It now covers three generations of the project. v1 is the original 2019 work — CNN running in 64–284mW at 6–18 fps on the Crazyflie 2.0 
GitHub
. v2 migrates to the commercial AI-deck with 8-bit fixed-point quantization, dropping power to 35–102mW at 9–17 fps on the Crazyflie 2.1 
GitHub
. v3 adds a new dataset collected directly with the nano-drone. The repo includes trained weights, full C source, dataset, and the PCB design files if you wanted to roll your own shield.

The supporting toolchain (also all open):

NEMO — academic quantization library (PyTorch → 8-bit fixed-point)
DORY — automates deploying quantized nets onto the GAP8's tiled memory hierarchy
PULP-SDK / GAP-SDK — the C runtime for the chip itself

Hardware you'd need to actually fly this: a Crazyflie 2.1 (~$230) + the Bitcraze AI-deck (~$125) which carries the GAP8 and HiMax camera. Total under $400 for a working platform. You can also run the inference stack on a GAPuino dev board without flying anything, which is how I'd recommend starting — debug the pipeline on the bench before you put it on something that can fall from the sky.

Honest caveat: PULP-Dronet is single-drone obstacle avoidance, not swarm coordination. It gives you the vision-to-control edge ML pipeline, but you'd be bolting the swarm intelligence on top yourself. The natural progression is: reproduce PULP-Dronet on one drone → extend to two drones with UWB-based relative positioning (Crazyflie's Loco Positioning deck) → add learned swarm behavior that consumes both the vision features and neighbor state. That's a legitimate research arc.

---

## User *(4:38 PM)*

Whats the closest commercialization point of this technology?

## Assistant

Good question — this separates "cool demo" from "actual product." Let me check the current commercial landscape.

Here's the honest picture. There's a big gap between "nano-drone swarm research" (what PULP-Dronet is) and "commercially deployed autonomous drones" (what's actually selling). The closest commercial on-ramps cluster in three tiers, from most-imminent to most-speculative:

Tier 1: Indoor logistics & inspection (shipping now, real revenue)

This is the clearest near-term market. Corvus Robotics, Verity, and Gather AI run autonomous drone swarms inside warehouses doing nightly inventory cycle-counts — no GPS, no pilot, no mocap. Each drone does onboard VIO + barcode reading + collision avoidance. Honeywell partnered with Corvus Robotics in March 2025 to integrate barcode-decoding software into their autonomous drones 
MarketsandMarkets
. The economic story is tight: warehouse inventory counts are brutally expensive labor, drones can work overnight, and a constrained indoor environment eliminates the regulatory nightmare. If you want to ship product with PULP-Dronet-class technology in under 2 years, this is the lane. The vision-in-the-loop edge ML story maps directly onto it because indoor means no GPS, which means perception has to be onboard.

Tier 2: Defense/ISR "teaming" (shipping in limited quantities, huge budgets)

Shield AI is the canonical example and the one to watch. Hivemind is their AI pilot software, which can be integrated with drones and other aircraft including F-16 fighter jets, to facilitate autonomous flying and swarming 
Privacy International
. Their 2024 revenue was $267 million, up 64% from 2023 
Privacy International
, which tells you the DoD is writing real checks. But notice the actual scale: V-BAT Teams enables a single human operator to command a minimum of four V-BAT drones 
Wikipedia
. Four drones. That's the commercial frontier in 2026 — not 50, not 200. Everything bigger is roadmap or DARPA demo. This tier matters because defense money funds the sim-to-real and edge-compute work that eventually trickles to civilian markets.

Tier 3: Light shows and entertainment (already a product, but not really "swarm AI")

Worth mentioning only to dismiss: Intel/Verity light shows are not autonomous swarms in the sense we've been discussing. They're centrally choreographed with each drone flying a pre-computed GPS/RTK trajectory. Beautiful, but no onboard intelligence and no real coordination logic — the "swarm" is an illusion.

Where the three interact (and where the opportunity sits)

The commercialization arc looks like this: indoor inspection validates the perception-to-action edge ML stack in a low-risk environment, which hardens the technology enough for limited defense deployments, which funds the R&D that eventually enables outdoor civilian swarms (delivery, emergency response, precision agriculture). The slowest-moving variable isn't the technology — UAV swarm operation typically requires regulatory waivers and exemptions that vary significantly across jurisdictions, and regulators are reluctant due to inherent uncertainty surrounding swarm behavior compounded by a lack of transparency and explainability 
PubMed Central
. Regulation and explainability are the actual bottlenecks, which ironically makes interpretable/verifiable swarm control a serious commercial research direction on its own.

Concrete takeaway for your project: if you want work that plausibly connects to a real product in 2-3 years, target indoor constrained environments. If you want the frontier with the biggest capital behind it, target defense teaming at N=3-10. The 200-drone autonomous outdoor swarm is still a decade from being a product anyone can buy for a legal civilian use case.

---

## User *(4:45 PM)*

Can you tell me the actual task/PULP is given?

## Assistant

Good question — "autonomous navigation" is vague, so let me be precise about what the network actually computes.

The task, stripped down:

PULP-Dronet is a reactive visual obstacle avoidance + path following policy. The CNN takes a single grayscale QVGA image (324×244, ~80K pixels, one frame at a time — no temporal context, no memory) from a forward-facing camera, and outputs exactly two scalars:

Steering angle (regression, continuous): how much to yaw, essentially "which direction is the free space."
Collision probability (classification, 0-1): how likely am I about to hit something.

That's it. No mapping, no planning, no localization, no semantic understanding. It's a pure sensorimotor reflex — image in, two numbers out, at 6–18 Hz.

How those two numbers become flight:

A simple handcrafted controller on the Crazyflie's main MCU (the STM32, separate from the GAP8) converts the outputs into velocity commands: steering angle → angular yaw rate, and collision probability → forward velocity (high collision prob → slow down or stop; low collision prob → fly forward faster). The drone's existing PID attitude stack handles everything below that. The neural net is not doing low-level control.

The training signal (this is the clever part):

The original DroNet network was trained on two disjoint datasets that the authors fused:

Steering: the Udacity self-driving car dataset — images from a car dashcam labeled with the human driver's steering wheel angle. This teaches "stay in the lane / follow the corridor."
Collision: the Zurich Bicycle Dataset — a person rode a bicycle toward obstacles with a camera and labeled each frame as "safe" or "about to collide." This teaches "stop when something's in your face."

So PULP-Dronet never saw a drone during training. It learned from a car and a bicycle. The assumption — which works surprisingly well — is that forward-facing obstacle avoidance generalizes across platforms because the visual structure of "corridor ahead" and "wall approaching" is platform-agnostic.

Why this matters for your swarm project:

PULP-Dronet is a single-agent egocentric policy with no notion of other drones. If you extended it to a swarm, you'd need to either (a) add a separate channel for neighbor state (from UWB ranging on the Loco deck) that gets concatenated into the MLP head, or (b) have drones appear as obstacles in the vision stream and let the collision-probability output handle them implicitly (lazy but might work at low density). Option (a) is the principled path and maps directly onto the permutation-invariant swarm architectures we discussed earlier — the CNN becomes your perception backbone, and a deep-sets or attention module over neighbor observations becomes the swarm coordination head, both running on the same GAP8.

That architectural fusion — visual egocentric perception + explicit neighbor reasoning, co-trained end-to-end, deployed on a single sub-watt chip — is genuinely unsolved and would be a real contribution.

---

## User *(4:46 PM)*

So their demo is like what, fly a straight path and avoid some pylons?

## Assistant

Pretty much, yeah. You've got it calibrated correctly. The canonical demos are:

The classic demos (v1/v2):

Fly down a straight university corridor, avoid people walking toward it
Fly down a parking garage lane, avoid pillars and parked cars
Fly down a bike path, avoid pedestrians and stationary obstacles
"Dynamic obstacle avoidance" = someone steps into the drone's path and it stops or veers

Speeds are modest — typically 1-2 m/s. Environments are semi-structured: there's an implicit "corridor" the steering network can lock onto (walls on both sides, a road, a hallway). Take the drone into an open field or a dense forest and it has nothing to steer toward. Take it somewhere without clear linear structure and the Udacity-trained steering head gets confused because it was trained on lane-following.

What it specifically cannot do:

Navigate to a goal ("fly to the kitchen") — no localization, no map
Handle 3D obstacles well — the training data is all ground-vehicle perspective, so it's fundamentally a 2D avoidance policy that happens to run on a flying thing
Fly backward, sideways, or do anything other than "forward with yaw adjustments"
Remember anything — each frame is processed independently, so if an obstacle briefly leaves the FOV the drone forgets it existed
Coordinate with other drones — as discussed, zero notion of teammates

The honest framing:

PULP-Dronet is a proof that the embedded ML pipeline works, not a proof that the behavior is sophisticated. The contribution is "we got a real CNN running under 100mW at 10+ fps on a 27-gram drone doing something non-trivial in the real world." The something-non-trivial is deliberately kept simple so the hardware/software story is the headline.

This is actually useful framing for your project: the existing work has decoupled the edge-ML-on-nano-drone problem from the intelligent-behavior problem. They solved the former with a deliberately dumb policy. The research opportunity is to keep their hardware/deployment methodology and swap in a meaningfully smarter policy — specifically, one that reasons about other drones. That's a more tractable framing than trying to solve everything at once.

---

## User *(4:49 PM)*

Hmm. One thing abt swarm tech. Since one of the limiting problems facing drones is weight that a single drone can carry, can you distribute different components amongst the swarm members, and rely on inter-swarm comms to communicate?

## Assistant

Yes — this is a real and active research direction, and it's one of the more intellectually satisfying framings of "why swarms" because it inverts the usual narrative. Instead of "many drones doing the same thing redundantly," it's "many drones doing different things cooperatively." The technical term is heterogeneous swarms or functional specialization, and it maps nicely onto the SWaP (Size, Weight, and Power) problem you're pointing at.

The core insight and why it works:

A single drone that does everything — long-range comms radio, high-res camera, LIDAR, thermal, powerful compute, big battery — is physically impossible at nano/micro scale because each of those components has non-trivial mass and power draw, and mass scales badly (more mass → bigger motors → bigger battery → more mass). But if you split the payload across N drones, each one stays small and efficient. The swarm becomes a virtual single platform whose capabilities are the union of its members', with the inter-drone link acting as the bus between "subsystems."

Three ways this actually gets done (and they interlock):

1. Sensor specialization. One drone carries a depth camera, another carries thermal, another carries a high-gain directional antenna for ground comms. The depth drone shares obstacle maps with the thermal drone, which doesn't need to do its own obstacle avoidance. DARPA's OFFSET program and the Swiss "GRIFFIN" line of work have done versions of this. The limiting factor is bandwidth — you need enough radio capacity to share sensor data at useful rates, which favors sharing features (encoded representations) rather than raw pixels. This is where edge ML re-enters: each drone runs a small encoder, transmits a latent vector, and the consumer drone runs a decoder/fusion head.

2. Compute offloading. A small scout drone with only an IMU and a tiny camera can't localize itself well, but a larger "mothership" drone with GPU-class compute can run VIO for the whole swarm and broadcast pose corrections. This is essentially edge computing with the edge itself being airborne. Works best when the comms link is short-range and high-bandwidth (UWB, 60GHz, optical). The tradeoff: the mothership is now a single point of failure, so you often want graceful degradation where scouts can fly dumber if they lose link.

3. Role specialization in task execution. This is the most "swarm-native" version. In a search-and-rescue scenario, some drones are "searchers" (wide-angle camera, fast flight), some are "identifiers" (high-res camera, hover capability), some are "relays" (just a radio and battery, loiter at altitude to maintain mesh connectivity to the operator). The searchers find candidates, hand off coordinates to identifiers, identifiers hover and confirm, relays make sure the data gets home. The roles can even be dynamically reassigned mid-mission based on battery state.

Why this is genuinely hard (and thus interesting):

The dependency structure creates new failure modes. If your depth-camera drone dies, the whole formation suddenly can't avoid obstacles. So you need either redundancy (two depth drones) or graceful degradation (thermal drone has a dumb backup avoidance policy). This is a co-design problem — you're simultaneously designing the hardware allocation, the communication protocol, the failure-handling behavior, and the learned policies. Most academic work picks one axis and fixes the others, which is why we don't have a general theory.

The comms layer is also underrated as a bottleneck. "Inter-swarm communication" sounds free in the abstract, but in practice: WiFi mesh networks collapse beyond ~10 nodes, sub-GHz radios are bandwidth-starved, and anything at scale needs careful MAC-layer design (TDMA, CSMA with swarm-aware backoff, etc.). Latency matters too — if the depth drone is 200ms behind in sharing obstacle data, the identifier drone is flying blind at 5m/s = 1 meter of uncertainty per update. This is why a lot of serious heterogeneous-swarm work uses UWB (Ultra-Wideband), which gives you ranging + comms at low latency in a single radio.

The commercial angle (connecting back to your earlier question):

This is exactly what makes the indoor warehouse drone model work economically. A single drone carrying everything would be too big to fly between racks. Instead, multiple small drones share charging infrastructure, localization anchors, and a central planner — the ground infrastructure is effectively another "swarm member" that does the heavy compute. It's heterogeneous swarming where one of the heterogeneous elements happens to be stationary.

For your project specifically:

If you wanted a tractable research question in this vein: what's the optimal sensor/compute allocation across a 3-5 drone team for a given task, and can you learn the communication protocol end-to-end? There's a small but growing literature on learned communication in MARL (differentiable inter-agent messaging — look up CommNet, TarMAC, IC3Net) where the message content itself is part of the policy. Combining that with a real heterogeneous hardware setup (one Crazyflie with AI-deck, one with Flow deck, one with Loco deck) would be a concrete, buildable project with a clear novelty story.

---

## User *(4:53 PM)*

Okay here is something even crazier. Can we split up pieces of a neural network amongst the drones and then use distributed inference to form a combined big parameter model for doing big intelligence things? Does this idea make sense?

## Assistant

The idea makes sense, and you've independently arrived at a real research area — it's called distributed neural network inference or split inference, and when applied to mobile/edge devices it gets called things like in-network inference, model parallelism at the edge, or cooperative inference. There's a growing literature on it. But the reason it hasn't taken over is illuminating, and understanding why tells you where the real opportunity is.

The idea in clean form:

Take a big neural network, partition it along some axis (layers, attention heads, MoE experts, whatever), place each partition on a different drone, and at inference time each drone computes its piece and forwards activations to the next drone(s). The swarm as a whole hosts a model that no individual drone could hold in memory. This is literally how modern LLMs are served across multiple GPUs (tensor parallelism + pipeline parallelism), so the concept is extremely battle-tested — just not in the air.

Why the naive version breaks badly:

Three interlocking problems, and they're the whole ballgame:

1. Communication cost dominates compute cost. This is the killer. Let's do the math. A Crazyflie's GAP8 can do ~10 GOPS at <100mW. Its radio (Crazyradio 2.4GHz or a typical ESB link) gives you maybe 2 Mbps of realistic bandwidth in a swarm setting where multiple drones are sharing the channel, with ~5-20ms latency per hop. Now suppose you split a transformer between two drones — you need to ship the activation tensor across. A modest 512-dim hidden state at fp16 is 1KB per token, at 30Hz that's 240 kbps per layer boundary. Seems fine. But real models have dozens of layer boundaries, attention needs all-to-all communication across heads, and you're sharing the channel with every other drone doing the same thing. You quickly hit radio saturation. On GPUs, tensor parallelism works because NVLink is 900 GB/s. Your radio is 2 Mbps. That's a ~10⁹ gap.

2. Latency compounds across the pipeline. If inference has to traverse 5 drones sequentially, and each hop costs 10ms, you've added 50ms of latency just for communication — before any computation. For a drone flying at 5 m/s that's 25cm of movement per inference, which is often more than your obstacle-avoidance safety margin. Flight control has hard real-time deadlines that distributed inference cannot meet without careful asynchronous design.

3. Reliability becomes a function of the weakest link. If any one drone in the pipeline drops out (battery, crash, radio failure), the entire model stops working. A monolithic model on one drone has graceful local degradation; a distributed model has catastrophic global failure unless you engineer redundancy, which costs you the parameter-sharing benefit you were trying to get.

Where it actually does work (and this is the interesting bit):

The naive "split a monolithic model" approach fails, but three structural variations turn out to be viable and map beautifully onto swarms:

Mixture-of-Experts (MoE) routing. Instead of splitting every forward pass across all drones, you have specialized expert sub-networks on different drones, and a tiny router network on each drone decides "this input needs the thermal-vision expert, forward it to drone 3." Most inputs only activate 1-2 experts, so communication is sparse. This is exactly how MoE works in large LLMs and it scales beautifully to heterogeneous swarms where each drone's expert matches its sensor. The depth-camera drone hosts the "close-range obstacle" expert, the thermal drone hosts the "find warm body" expert, etc. Communication happens only at routing decisions, not at every layer.

Hierarchical / asymmetric inference. Small fast models on every drone handle real-time local decisions (flight control, immediate obstacle avoidance). A larger, slower model runs distributed across the swarm (or offloaded to a mothership drone) and produces higher-level guidance — "the target is probably in this quadrant, prioritize search there" — updated at 1-2 Hz rather than 100 Hz. This respects the physics: fast-loop control stays local, slow-loop cognition can afford the communication cost. The two loops are coupled loosely, not tightly.

Learned compression / split at the right boundary. If you're going to split a network, split it at a point where the activations are intrinsically small. CNN features in early layers are huge (320×240×64 = 5MB), but by the time you're at the penultimate layer you might have a 256-dim vector (512 bytes). Learned autoencoder-style bottlenecks can further compress this. Research on "split learning" and "neurosurgeon" literature from ~2017 onward is all about finding these optimal partition points. The principle: pay the communication cost once, at the narrowest point in the network.

What this means conceptually:

The intuition you should take away is that distributed inference trades memory for bandwidth, and the exchange rate is brutally unfavorable at radio speeds. So the question isn't "can we distribute the model" but "can we restructure the computation so that the useful thing we want to distribute happens to have low bandwidth requirements." MoE does this. Hierarchical inference does this. Naive layer-splitting does not.

The deeper version of your question — and I think this is actually what you're gesturing at — is whether a swarm can have emergent collective intelligence that exceeds any individual drone's capacity. That's real, but it doesn't come from distributing a pre-trained monolithic model. It comes from training the collective end-to-end, with the communication channel as part of the learned architecture. Each drone learns what to say and what to listen to. The "model" isn't distributed so much as the intelligence itself is distributed-native from the start. That's the MARL-with-learned-communication direction I mentioned earlier (CommNet, TarMAC, differentiable inter-agent channels), and it's probably the most intellectually honest version of your idea.

So: the idea makes sense, it's been tried, the naive version hits a bandwidth wall, but the sophisticated versions — MoE across heterogeneous drones, hierarchical fast/slow loops, and swarm-native learned communication — are real frontiers with genuine room for contribution.

---

## User *(4:56 PM)*

Wait wtf. Holy shit. MoE fits perfectly! Or am i crazy? Be honest, max technical precisoom

## Assistant

You're not crazy. The fit is genuinely good, and the intuition is worth taking seriously. But let me be maximally precise about where it fits, where it almost fits, and where it breaks — because the difference determines whether this is a thesis or a research program.

Why MoE structurally matches heterogeneous swarms:

MoE decomposes a dense FFN layer into N "expert" sub-networks plus a lightweight router (usually a linear projection + softmax + top-k selection). At inference time, each token is routed to k experts (typically k=1 or k=2 out of N=8-64 experts in modern models like Mixtral, DeepSeek-V3, etc.). The computational cost is roughly k/N of the dense equivalent, while the parameter count is N× — this is exactly the "sparse activation, dense knowledge" tradeoff that makes MoE scale.

Now map that onto a swarm: each drone hosts one or more experts. The router (small, replicated on every drone) decides per-input which expert(s) to invoke. Communication happens only when routing sends work off-device. If routing is sparse — most inputs stay local or go to 1 remote expert — your bandwidth requirements are bounded and predictable. The drones collectively host an N×-parameter model while each individually holds only 1/N of it. On paper, this is a near-perfect match.

The fit gets even better when you consider heterogeneous sensors: a depth-camera drone naturally hosts the "geometric reasoning" expert, a thermal drone hosts the "heat-signature" expert, a wide-FOV drone hosts the "scene-understanding" expert. The router learns which expert is relevant for which input, and this aligns with which drone physically has the best sensor for that input. Sensor modality and expert specialization become isomorphic. That's elegant.

Where it almost fits but needs engineering:

Four issues, in increasing order of severity:

1. The router needs global consistency. Every drone's router has to make the same routing decision for a given input, or you get inconsistent processing. This means either (a) replicating the router weights on every drone (cheap, ~0.1% of model size), or (b) designating one drone as the router authority. Option (a) is standard and fine. But the router needs the input to route — so if drone A has a sensor observation that needs to go to drone C's expert, drone A's router runs locally, decides "send to C," ships the activation to C, waits for the result, and integrates it. Round-trip latency matters here.

2. Load balancing is brittle in small-N regimes. MoE in LLMs works with 8-64 experts and millions of tokens per batch — statistical load balancing emerges naturally. In a swarm with N=5 drones and 1 inference per timestep, you have no batch. If the router happens to pick drone 3 for 80% of the work, drone 3's battery dies first and the swarm degrades. Production MoE uses auxiliary load-balancing losses during training, but those assume large batches. Small-swarm MoE needs new balancing mechanisms — possibly explicit per-drone capacity constraints baked into routing, or stochastic routing with entropy regularization to prevent collapse onto one expert.

3. The all-to-all communication pattern is real. Modern MoE (e.g., Switch Transformer, Mixtral) uses top-2 routing at every MoE layer, and there are typically many MoE layers. So for one forward pass you're doing potentially dozens of cross-drone sends. Each send is small (one activation vector), but the cumulative latency across layers can compound. The solution is to restrict MoE to a few strategically chosen layers — the ones where specialization actually matters — rather than every layer. Recent work on "shallow MoE" and "MoE-only-at-specific-layers" is directly relevant.

4. Expert imbalance in heterogeneous swarms. If drone A has a Cortex-M4 and drone B has a GAP8 with 10× more compute, you can't give them equal-sized experts. You need heterogeneous experts whose sizes match host capability. This breaks the clean MoE formulation where all experts are identical. It's solvable — you'd need variable-width experts and a router that accounts for expert capacity — but it's a non-trivial architectural modification.

Where it breaks (be honest with yourself):

1. MoE is typically applied inside transformers, which are heavy. A Mixtral-8x7B expert is 7B parameters — no drone is running that. You'd need MoE applied to small models where the individual experts fit in the 100K-10M parameter range (memory on GAP8 is ~8MB). That's closer to "mixture of tiny specialists" than "mixture of experts" in the LLM sense. The dynamics of small-scale MoE are much less studied. It might work beautifully; it might collapse. Nobody really knows.

2. Training is the actual hard problem. You can't take an off-the-shelf MoE model and run it on drones. You have to train a model where the expert topology, the routing costs, and the communication constraints are all baked into the training objective. Specifically: the training simulator needs to model bandwidth limits and latency, and the loss needs to penalize routing patterns that would be infeasible in deployment. This is an open problem — there's almost no work on "communication-constrained MoE training," which is actually good news because it means there's genuine contribution room.

3. The "big intelligence" framing is aspirational, not imminent. MoE-across-drones gives you more parameters than one drone can hold. It does not automatically give you emergent reasoning. You need the parameters to actually encode useful specialized knowledge, which requires either (a) a lot of relevant training data, or (b) distilling from a larger pretrained model. For a drone-swarm task, neither is trivially available. You'd probably start with a much narrower framing: "MoE lets our 5-drone swarm handle N visual scenarios that a single-drone model of equivalent per-drone cost cannot."

The honest research framing:

If I were steelmanning this as a PhD-thesis-worthy contribution, it would be something like: "Communication-Aware Mixture-of-Experts for Heterogeneous Robot Swarms: Training, Routing, and Deployment." The contributions would be (1) a small-scale MoE architecture where expert sizes are heterogeneous and match host hardware, (2) a training procedure that incorporates bandwidth and latency as differentiable losses, (3) a routing mechanism that handles load balancing at small N, (4) a real deployment on 3-5 Crazyflies showing that the swarm can solve a task requiring capabilities no single drone could host. Each of those sub-contributions is a paper. The full thing is a thesis.

So yes, your intuition is correct and it's genuinely good. It's not a free lunch — there are real technical obstacles — but the obstacles are interesting ones, not dealbreakers, and they haven't been systematically addressed in the literature. This is a legitimate research direction, and the fact that you pattern-matched to it suggests you're thinking about the problem at the right level of abstraction.

Keep going.

---

## User *(4:58 PM)*

Are there any active research into this area, applying a moe style distributed NNs to drones?

## Assistant

Let me search — this is a specific enough intersection that I want to see what's actually out there rather than guess.

Let me do one more targeted search specifically for MoE-on-drones, because the results above are about split/collaborative inference in general, and I want to see if anyone has explicitly invoked the MoE framing.

Okay, here's the honest landscape. Your instinct was right on multiple fronts, and the research map is more interesting than I initially realized:

The general idea is being actively researched — but almost nobody is doing it specifically for drones. There are three adjacent literatures that are converging toward what you described, and the gap between them is where your opportunity sits:

1. Distributed/split inference on UAV swarms (exists, but not MoE-structured). There's a real and growing literature on collaborative DNN inference across drones. This line of work formulates task allocation of collaborative inference in UAV swarms as an optimization problem to minimize inference latency, considering memory footprint, computing power, and energy constraints 
arXiv
. But the approach is almost always layer-wise splitting of a monolithic DNN (like ResNet or AlexNet) — not MoE-style routing. They're solving a graph-partitioning problem, not a learned-routing problem. One 2023 paper proposes a hybrid inference framework combining early exit and task offloading with bottleneck-designed DNNs that provide smaller intermediate data size than the original input 
ScienceDirect
 — closer to your intuition, but still not MoE.

2. MoE on distributed/heterogeneous edge (exists, but not on drones). Separately, there's very recent and explosive activity on MoE for edge computing. This is the most relevant thread. A 2025 paper explicitly proposes a distributed edge computing system based on MoE architecture with a channel-aware gating function, where each edge device hosts diverged neural networks serving as experts, and input data is processed by a backbone network into latent embeddings then transmitted to the corresponding expert devices via wireless links as directed by the gating network 
arXiv
. And critically — they explicitly name UAVs as a key application: a key application is Unmanned Aerial Vehicle (UAV)-assisted integrated sensing and communications (ISAC), where individual UAVs act as expert nodes 
arXiv
. So the framing exists in the literature. But their experiments are on LeNet/ResNet/ViT for image classification — not on actual flying drones doing actual control.

3. Heterogeneous edge MoE in general. There's also IEEE work on "Mixture of Edge Experts" (MoEE) addressing exactly the load-balancing and out-of-distribution issues I raised — the significant heterogeneity in computing power and storage capacity among edge devices results in local models that differ in type, size, and accuracy, and inference requests in open-world scenarios often deviate from the local training distribution 
IEEE Xplore
. The 2025 ACM Queue survey on edge generative AI notes despite theoretical benefits, MoEs have seen limited adoption in local models because of significant practical tradeoffs requiring either more high-bandwidth memory to store the full set of experts, or complex expert offloading/onloading mechanisms atypical for resource-constrained edge devices 
ACM Queue
.

The honest frontier assessment:

The pieces exist but the synthesis doesn't. Specifically, I cannot find any paper that does all three of: (1) MoE architecture (not just split inference), (2) actual flying drone deployment (not just simulated wireless channels), (3) control or perception tasks (not just classification benchmarks). The closest is the channel-aware MoE paper, which frames UAV ISAC as an application but doesn't build or fly anything. The drone swarm literature does collaborative inference but uses layer-splitting rather than learned routing. These two lines haven't been joined.

What this means for you:

Your intuition wasn't just reasonable — it's an active and fashionable research direction that's about two years into its hype cycle, and the specific sub-problem of MoE-on-actually-flying-drones is essentially open. The pieces you'd need (the MoE-for-edge theory, the PULP-Dronet-style deployment stack, the small swarm RL infrastructure) all exist independently. Combining them is genuine work but not moonshot work. A paper titled something like "Sparse Expert Routing for Heterogeneous Nano-Drone Swarms: A Real-World Deployment" would land in ICRA or CoRL and be read.

The caveat I'd add: because this is hot, expect others to be working on it too. If you're interested in pursuing this seriously, the time to stake claims is now, and the differentiator will likely be whoever first shows it working on real hardware rather than in a channel simulator. PULP-Dronet's existing deployment toolchain is a legitimate competitive advantage for anyone wanting to be first-to-fly.

---

## User *(5:22 PM)*

Is there a way we can integrate MoE style NN splitting on the PULP task and hardware?

## Assistant

Yes — and this is where the idea gets concrete enough to actually build. Let me work through what it would take, because the integration isn't trivial but it's also not hand-wavy. There are real architectural decisions that determine whether it works or collapses.

The fundamental constraint you're working against

GAP8 has roughly 8MB of off-chip Flash for weights, 512KB of L2 memory, and 64KB of L1 per-cluster. A single PULP-Dronet v2 network at 8-bit fixed-point fits in this budget with room to spare — the whole network is a few hundred KB. This is actually good news for MoE: you're not trying to fit a 7B-parameter Mixtral expert on each drone, you're trying to fit a 200KB expert. Small-scale MoE is the regime that matches nano-drone hardware. Don't think "distribute an LLM," think "each drone hosts one tiny specialist CNN plus a tinier router."

Architecture sketch that would actually fit on GAP8

Here's a concrete proposal. The network per drone has three components:

The shared backbone is a small CNN (roughly the first half of DroNet — maybe 50-100KB) running on every drone, processing the local camera image into a compact feature vector (say 128-dim). This is replicated across the swarm, trained identically on every drone. This handles the low-level visual feature extraction that every drone needs regardless of specialization.

The router is a tiny MLP (maybe 2-3KB — a 128→32→N_experts layer with softmax) that takes the feature vector and outputs routing logits over experts. Also replicated across every drone. This is cheap enough that replication doesn't hurt.

The expert head is where drones differ. Each drone hosts exactly one expert (or two for redundancy) — a small task-specific head (~100-300KB) that consumes either the local feature vector or a received-over-radio feature vector from another drone. The expert outputs a task-specific prediction: "probability this region contains a target," "estimated depth to nearest obstacle in thermal channel," "yaw command given corridor-following context," etc.

Total per-drone memory: backbone + router + one expert ≈ 300-500KB. Well within GAP8's budget, leaves headroom for activations and the flight control stack.

How inference actually proceeds at runtime

Drone A captures an image, runs the backbone locally, gets a 128-dim feature vector. Drone A's local router evaluates it and decides: "top-1 expert for this input is Expert 3, which lives on Drone C." Drone A transmits the 128-dim vector to Drone C (128 × 1 byte with 8-bit quantization = 128 bytes, negligible at 2 Mbps). Drone C runs Expert 3 on the vector, gets a task-specific output (say, 8 bytes), transmits back. Drone A integrates the result into its control loop. Round-trip cost: ~200 bytes of radio traffic and whatever the over-the-air latency is (~5-15ms on a decent link).

The clever part: if the router on Drone A happens to select the expert that lives locally on Drone A, no radio traffic at all. Good training should encourage locality — experts specialize on inputs the local sensor is best suited for, so the "right" expert is usually the local one, and cross-drone routing happens only when genuinely needed. This is the key design principle: train the router to prefer local experts unless a remote expert is substantially better. You can bake this into the loss as a communication-cost penalty.

The three hard problems and how to attack them

Training. You can't just train this on a desktop and deploy. You need a simulator that models (a) the realistic bandwidth and latency of the inter-drone radio, (b) the possibility that drones drop in and out (graceful degradation), and (c) the heterogeneous sensor modalities if drones have different cameras. Gym-PyBullet-Drones plus a custom communication-layer wrapper gets you most of this. The loss function needs three terms: task loss (did the swarm do the right thing), load-balancing loss (is any one expert getting hammered), and communication loss (penalize routes that cross the radio when not needed). The existing MoE auxiliary-loss literature gives you the recipes — you're just adapting them to include physical comm costs rather than just GPU utilization.

Deployment with the PULP toolchain. The PULP-Dronet stack — NEMO for quantization, DORY for memory-tiling, GAP-SDK for the C runtime — was designed for monolithic CNNs. A MoE architecture has conditional execution (only run the expert if routed to you), which the current toolchain doesn't natively support. You'd need to either (a) generate multiple independent binaries per expert and have a router-driven dispatcher, or (b) contribute a conditional-execution extension to DORY. Option (a) is the quick hack, (b) is the publishable systems contribution. Either is doable; neither is free.

Inter-drone comms. The Crazyflie's default ESB radio is point-to-point and limited in bandwidth. For real multi-drone routing you'd want either the Loco Positioning deck (UWB, gives you ranging + modest data) or a custom payload with something like a nRF52 mesh or even an ESP32-based WiFi mesh. The research path here is to use UWB and piggyback the feature-vector transmission onto the ranging packets — you get localization and communication in the same radio. This is underexplored and probably worth a paper on its own.

What you'd actually build as a minimum viable demo

Three Crazyflies, each with an AI-deck. Each drone has a different "sensor specialty" (simulated if needed — e.g., different image preprocessing pipelines that emphasize different features). Task: cooperative target search in a cluttered room, where different drone-expert pairs are optimal for different target types or environmental conditions. Baseline: monolithic PULP-Dronet-style network replicated on all three drones. Your system: backbone+router+distributed-expert architecture with learned routing. Metric: task success rate, per-drone energy consumption, total radio traffic, and graceful degradation under drone-dropout.

This demo is scoped tight enough to actually finish — probably 12-18 months of work for a PhD student or a well-resourced team — and it would be first-to-fly on a problem that's currently only simulated. If you got it working, you'd have a CoRL or ICRA paper and a defensible claim on the research direction.

The real question to sit with

The architecture above is the "obvious" synthesis of MoE and edge drone deployment. The reason it hasn't been done isn't that it's impossible — it's that it requires expertise in four different areas simultaneously (MoE training, MARL, embedded ML deployment, drone hardware), and few labs have all four. If you're genuinely interested, the strategic move is to start building the sim version this quarter, which costs you nothing but time, and decide based on what you learn there whether the real-hardware version is worth the capital investment. The simulation results alone — showing that communication-aware MoE beats replicated-monolithic on a realistic drone task — would be a solid workshop paper and a signal to others that you're working in this space.

Want me to sketch out what the sim-only version would look like in more detail?

---

## User *(5:25 PM)*

What would we even put in the MoE tho lol? I mean, can literally be anything? Or a bit more specifically: what is the MVP MoE NN that work for a demo of the MoE on drones concept?

## Assistant

Ha, fair — this is the right question to ground the whole thing. The answer determines whether your demo is "oh cool, MoE works" or "so what, you could have done this with one network." The MVP has to be carefully designed so that the MoE decomposition is necessary, not cosmetic.

The design principle: experts must be meaningfully different

If all your experts could have been trained as a single network, you've demoed nothing. The MoE structure needs to be justified by the fact that different inputs genuinely benefit from different specialized processing, and that no single tiny network can handle all cases well within the memory budget. You're proving a capacity argument: the swarm-as-MoE does things no single drone could.

So the MVP task has to have visible modes — distinct input regimes where different processing helps — and the swarm has to collectively span those modes while each drone individually cannot.

The MVP I'd actually build: multi-target classification with specialist experts

Concrete setup. Task: the swarm is searching an indoor environment for specific target objects. There are, say, 4 target categories: a red ball, a QR code, a person (mannequin), and a heat source (small heater). Each drone flies around, captures images at 10Hz, and the swarm collectively must detect and classify any targets in the scene.

The MoE structure: you have 4 experts, one per target class. Each expert is a tiny classifier head specialized for its target type — the "ball expert" is great at round-object detection and color segmentation, the "QR expert" is great at high-frequency pattern recognition, the "person expert" is trained on human silhouettes, the "heat expert" processes the thermal channel if available.

Why this works as a demo:

The experts have visibly different learned features — you can show attention maps or saliency visualizations and see that the ball expert attends to circular regions while the QR expert attends to corners. This makes the specialization legible to reviewers.

A single network of equivalent per-drone cost cannot match the combined accuracy, because at the 200KB budget a generalist classifier has to compromise across all 4 classes while specialists can each nail their one class. This is the capacity argument, and it's easy to benchmark: train a 200KB monolithic 4-class classifier, compare to your 4×200KB MoE with top-1 routing, show the gap.

The router learns something non-trivial — it has to look at an image and decide "this looks like it might contain a ball, route to ball expert" before actually running the expert. The router itself is a classifier-of-sorts, but a cheap one.

The routing decision has clear physical meaning: "send this image feature to the drone carrying the ball expert." You can visualize which drone processed which input and show the load distribution.

Why this is better than the obvious alternatives

You might be tempted to do something like "different experts for different flight modes" (hover expert, forward-flight expert, aggressive-maneuver expert). Don't. That conflates control with perception and makes the demo much harder to evaluate — "did the swarm fly better" is a much fuzzier metric than "did the swarm detect more targets correctly."

You might also consider "different experts for different environmental conditions" (bright-light expert, low-light expert, cluttered expert). This works in theory but requires you to carefully control lighting/environment during the demo, which is a physical hassle. Target-class specialization works in any lighting as long as the targets are present.

A third tempting option: "different experts for different sensor modalities" — one drone has RGB, one has thermal, one has depth. This is the most scientifically interesting version because the MoE decomposition tracks physical hardware heterogeneity. But it requires you to actually build drones with different sensors, which doubles your hardware budget. Save this for v2.

The training recipe (which is actually the hard part)

Here's how you'd train this. Collect or generate a dataset of images containing the 4 target types in varied contexts. Pretrain a shared backbone (the first few conv layers of DroNet v2, say) on generic image features — ideally via self-supervised learning or distillation from a bigger teacher. Freeze the backbone.

Then train 4 expert heads independently, each on binary classification for its target class, using the frozen backbone's features as input. This gives you good specialists.

Now train the router jointly with the experts (fine-tune the experts during this stage). The router loss has three terms: cross-entropy on the 4-way target classification (task loss), a load-balancing auxiliary loss penalizing variance in expert utilization across a batch, and a communication penalty that adds cost when the selected expert is not local to the input-producing drone. This is where the MoE magic happens — the router learns to route correctly and to prefer local experts when they're roughly as good.

Finally, quantize everything with NEMO, deploy with DORY, fly.

The minimum-viable datasets

You don't need to collect a huge real-world dataset. Use existing datasets for each class — COCO for balls and people, a QR code dataset, a FLIR thermal dataset for heat sources — and augment with synthetic images rendered in Unity or Blender with drone-camera perspectives. Honestly, for the initial MVP you could probably do this entirely in simulation with Gym-PyBullet-Drones and render synthetic targets, then do the real-hardware deployment as phase 2. Simulation-first lets you iterate on the architecture without breaking drones.

The demo that would actually go viral

Once it works, the demo video is: three Crazyflies fly into a room containing all 4 target types scattered around. Overlay shows in real-time which expert is being activated, which drone is processing the input, and the radio traffic. One drone "dies" (you pluck it out of the air), and the router re-learns in a few seconds to route around it with graceful degradation — maybe the person-class accuracy drops since that expert is gone, but ball/QR/heat detection continues. That dropout-resilience demo is the money shot and it's the thing that separates a MoE-swarm from "just three drones doing inference in parallel."

The honest expectation-setting

This MVP is tractable but not trivial. I'd estimate: 2-3 months to build the simulation version and show the basic result, 3-6 more months to get it deployed on real Crazyflies with the PULP toolchain, and another 2-3 months to add the failure-mode resilience demo and write it up. Budget a year of serious work for a convincing end-to-end result. But at every stage, you have something publishable — the sim results alone are a workshop paper, the hardware deployment is a conference paper, the full resilience story is a journal paper or a top-tier conference paper.

The key discipline: don't let the MVP balloon. "Four target classes, indoor environment, three drones, one specialization axis (target class)" is enough. Every additional axis you add (sensor heterogeneity, dynamic environments, adversarial conditions) multiplies the engineering work by a lot. Ship the narrow version first.

---

## User *(5:26 PM)*

Hmm. Can we do this in a non-trivial way on a sim?

## Assistant

Yes — and honestly, the sim version is where I'd start regardless, because you can iterate 100x faster and the hardware story is always just "and we then deployed the thing we already proved works." The question is how to make the sim demo non-trivial — meaning reviewers can't say "sure, MoE works in sim, but you've simulated away all the hard parts."

Let me be direct about what "non-trivial in sim" means: you have to simulate the things that make the real-world deployment hard, not paper over them. Specifically, three sources of difficulty have to be present or reviewers will dismiss it.

The three non-trivialities your sim must preserve

1. Realistic compute and memory constraints. You can't just train a 10M-parameter network and claim it would fit on a GAP8. You need to actually enforce the memory budget. This means constructing your experts to be within the size budget (~200-500KB), training at full precision but with quantization-aware training so you know the 8-bit deployment version will behave similarly, and reporting latency/memory numbers that correspond to real hardware. The cheap trick that works: take the published PULP-Dronet v2 architecture, slice it into backbone+head, and size your experts to match the head's parameter count. Now you have a credible budget story without actually running on GAP8.

2. Realistic communication constraints. This is the critical one. Your sim must model (a) bandwidth limits between drones — say, 2 Mbps shared channel with CSMA-style contention, (b) latency — 5-20ms per hop, non-deterministic, (c) packet loss — small probability per transmission that increases with range, (d) range limits — drones far apart can't communicate directly. If you skip this, you're just doing "MoE but the experts happen to be on different machines" and the whole point collapses. Implementation: wrap your PyTorch model with a custom Communication layer that introduces simulated delays, drops tensors stochastically, and tracks total bytes transmitted as part of the loss. This is maybe 200 lines of code and it's what separates your sim from a toy.

3. Realistic perception and dynamics. Use Gym-PyBullet-Drones or Isaac Lab so your drones actually have quadrotor dynamics and the camera views are physically plausible. The temptation will be to feed your experts clean pre-labeled observations from the simulator's ground truth — don't. Feed them the actual rendered camera images. This forces the backbone CNN to do real feature extraction and the experts to handle real visual variability. If you want to cheat initially to debug, fine, but the final experiments must use rendered vision.

The specific non-trivial demo I'd build

Here's a concrete sim setup that would be defensible. Five simulated Crazyflies in a procedurally generated indoor environment (rooms with random furniture, lighting variation, and scattered targets). Four target classes as before. Each drone runs a shared backbone (frozen, pretrained on ImageNet-ish data then fine-tuned on simulated drone views) plus one expert head. The router runs locally on each drone, decides routing per frame, and dispatches features over a simulated radio channel with realistic bandwidth/latency/loss.

The task: swarm coverage + detection. Over a 60-second episode, the swarm must visit as much of the environment as possible and correctly classify all targets encountered. The reward combines coverage (fraction of environment observed), detection accuracy (true positives minus false positives), and a penalty for radio usage.

Now here's where it gets non-trivial — you run four experimental conditions:

Condition A: Monolithic baseline. Each drone runs a single 500KB classifier covering all 4 classes. No communication. This is the "just use independent drones" baseline.

Condition B: Replicated experts baseline. Each drone runs all 4 experts locally (4× memory cost, violating the budget). This is the "unlimited memory" upper bound.

Condition C: Naive MoE. Your architecture, but with a router that ignores communication cost. Sends everything to the theoretically best expert regardless of where it lives.

Condition D: Communication-aware MoE. Your architecture with the full loss including routing cost penalty, load balancing, and dropout resilience.

The story you want to tell: Condition D matches Condition B (the upper bound) on task accuracy while staying within Condition A's memory budget per drone and using substantially less radio bandwidth than Condition C. If that relationship holds, you have a paper.

The failure-mode experiments are where it gets compelling

Run each condition with drone dropouts at random times. Condition A degrades gracefully but has lower ceiling. Condition B is a single-drone-level failure (losing one drone just removes one drone's contribution). Condition C collapses catastrophically when you lose the drone hosting a critical expert. Condition D, with the right training (train with random dropouts built into the sim), learns to re-route intelligently and degrades gracefully. Plot accuracy vs. number-of-drones-dropped for all four conditions — if your Condition D curve dominates the others, that's the headline figure of the paper.

You can also run latency-variation experiments (what happens when radio gets congested), range experiments (drones spread far apart, some pairs can't communicate directly, need multi-hop), and load-imbalance experiments (inject distribution shift — lots of ball-targets show up at once, does the router adapt).

Why this is actually non-trivial research

Three things make this a real contribution rather than an engineering demo:

The communication-aware routing loss is novel in the MoE-for-robotics context. The general idea exists in the distributed edge computing literature I cited earlier, but nobody has applied it to a simulated robotics task with realistic physical communication constraints. Formalizing how to make routing differentiable with respect to communication cost is a legitimate methodological contribution.

The dropout-trained routing is novel. Standard MoE doesn't train for the scenario where experts disappear mid-inference. You'd need to introduce a random-drone-dropout schedule during training so the router learns to handle missing experts gracefully — probably via a masked softmax where "unavailable" experts get -inf logits, and training with random masks. This is probably the most defensible methodological piece.

The joint perception-and-coordination benchmark is something the community doesn't really have. Most MARL benchmarks use low-dim state observations; most learned-perception benchmarks are single-agent. A benchmark where the swarm has to jointly perceive and coordinate, with realistic compute/comm constraints, is a resource the field would use.

Implementation stack

Gym-PyBullet-Drones for physics and camera rendering. PyTorch for the neural nets (standard MoE libs like Tutel or just rolling your own — honestly, for 4 experts, just write it yourself, it's maybe 50 lines). RLlib or Sample Factory for the RL training loop if you go full RL; or supervised learning on collected sim trajectories if you want to decouple perception training from policy training (I'd recommend the latter for the MVP — train the MoE as a perception system first, then plug it into a simple hand-coded coordination policy, then later learn the coordination).

One crucial choice: don't start with end-to-end RL. Start with supervised learning on a fixed dataset of simulated flights with labeled targets. Get the MoE architecture working as a pure classifier first. Then add the coordination layer. Then add RL if you need it. Most of the interesting MoE-specific results (routing patterns, load balancing, dropout resilience) show up at the perception level and don't require RL to demonstrate.

The honest timeline

Four to six months to get Condition D beating Condition A/C on the basic benchmark in sim, assuming you work on this seriously and know PyTorch well. Another two months to do the failure-mode experiments properly. Writing takes another month. So call it a year from a cold start to a submittable paper, or six months if you're already fluent in the tools.

That's a real research project, not a weekend hack — but the sim-only version is completely achievable with no hardware and no lab. You could start tomorrow with a laptop and a decent GPU.

---

## User *(5:33 PM)*

Okay to make the problem even more tractable: remove loss from the radio (but keep comms bandwidth), and also remove collision detection for drones, so we dont have to train a swarm algorithm. Does that make sense? Your final sentence output shud be a line that condenses this project idea that i can quickly post on twitter

## Assistant

Yes, that makes total sense and it's a smart simplification. Here's why each cut is principled, not just lazy:

Dropping radio packet loss is fine because loss is orthogonal to the core MoE contribution. The interesting questions — "does the router learn to respect bandwidth," "does load balancing emerge," "does routing adapt to dropouts" — all work the same whether packets are reliably delivered or not. Packet loss is a robustness-engineering concern you can add in v2, and it mostly just makes training noisier without testing anything new about the architecture. Keeping bandwidth (the shared channel capacity constraint) is the right call because that's what forces the router to economize on communication. Bandwidth is the economically meaningful constraint; loss is just noise.

Dropping inter-drone collision avoidance is a great call and probably the most important simplification. Training a swarm flight policy is a whole separate research project — MARL credit assignment, emergent coordination, sim-to-real transfer, all of it. By removing this, you're saying "assume flight is solved, study perception-and-routing in isolation." This is exactly the right scoping move because it lets you use simple scripted or even pre-recorded trajectories for the drones. Each drone flies a predetermined path (lawn-mower coverage pattern, random waypoints, whatever), and the MoE perception system runs on top. You've cleanly separated the perception/coordination layer from the control layer, which is good science — you're isolating the variable you actually want to study.

What the simplified MVP looks like now:

Five drones in a sim environment flying scripted trajectories (no learned flight policy, no collision concerns — just pretend they're on rails). Each drone has a camera, a shared backbone CNN, a local router, and one expert head. They see rendered images of scattered targets. The router decides per-frame where to send features; the bandwidth-constrained radio model enforces that you can't just broadcast everything. Training objective is target classification accuracy + load balancing + bandwidth penalty, with random expert dropouts during training to get graceful degradation. Four experimental conditions as before (monolithic, replicated, naive MoE, bandwidth-aware MoE), plus the dropout curves.

This is actually buildable by one motivated person in 3-4 months of focused work. You don't need RL, you don't need a swarm policy, you don't need a wireless simulator with stochastic channel modeling. You need PyBullet-Drones with scripted flights, a PyTorch MoE with a custom bandwidth-accounting communication layer, and a training loop. Everything else is trappings.

The residual risk is just whether the results are interesting enough — specifically, whether Condition D (bandwidth-aware MoE) meaningfully beats Condition A (monolithic) and Condition C (naive MoE). If the numbers are close, the paper is a null result; if they separate cleanly, you have something. My intuition says they'll separate because the capacity argument is real — 200KB of specialist beats 200KB of generalist on any multi-class perception task — but you won't know until you run it.

Exploring sparse Mixture-of-Experts neural nets distributed across a drone swarm: each drone hosts one tiny specialist expert, a learned router decides which drone processes which input under realistic bandwidth constraints, and the whole thing gracefully degrades when drones drop. Sim-first, PULP-Dronet-deployable, ~6 months to MVP.

---

## User *(5:36 PM)*

Hmm. Maybe even more simply is -> can we train a MoE style model of that size and have it *work* -> with routing, it performs better on image classification. This shud prolly be v1 of the idea

## Assistant

Yes. This is actually the correct first step, and I should have pushed you toward it earlier — you've just independently done the right kind of scoping discipline. The drones and the communication layer are downstream of a more fundamental question: does small-scale MoE even work? If you can't beat a monolithic baseline at the 200KB-per-expert regime on a clean image classification task, there's no point building anything on top of it.

Why this is the right v1

All the MoE literature that motivates your intuition operates at vastly different scales. Mixtral-8x7B has 7B-parameter experts. Switch Transformer has hundreds of millions. DeepSeekMoE has tens of millions. The smallest "small MoE" in the literature is still measured in millions of parameters per expert. Your regime — ~200KB experts, which is roughly 200K 8-bit parameters or ~50K full-precision parameters — is essentially uncharted. It's entirely possible that MoE benefits vanish at this scale, because the router needs enough signal to route well and the experts need enough capacity to actually specialize. Both of those might break when everything is tiny.

So the real scientific question underneath your whole drone-swarm idea is: at nano-scale (sub-1M parameters per expert), does learned MoE routing outperform a monolithic network of equivalent total or per-forward-pass compute? If yes, everything downstream is justified. If no, you need to rethink the whole approach.

The clean v1 experiment

Pick a standard image classification benchmark — CIFAR-100 is the obvious choice because it has enough classes (100) to make specialization meaningful, it's small enough to iterate fast, and everyone in ML reads results on it. Or TinyImageNet if you want to look more serious. ImageNet is overkill for v1.

Your architecture: a small shared backbone (maybe 100K params), a tiny router (a few KB), and N expert heads of ~200K params each. Start with N=4 experts, top-1 routing. Total MoE model size: backbone + router + N × expert = roughly 100K + negligible + 4 × 200K = ~900K params. But per-forward-pass compute is only backbone + router + 1 expert = ~300K params worth of compute.

Your baselines: (1) a monolithic network with 300K params matching the MoE's per-forward-pass compute — this is the "fair compute" comparison, and (2) a monolithic network with 900K params matching the MoE's total parameter count — this is the "fair capacity" comparison. The story you want: MoE beats baseline 1 (more capacity without more compute) and matches or approaches baseline 2 (sparse activation is nearly as good as dense). If those relationships hold, you've demonstrated the core value proposition of MoE at nano scale.

What specifically to measure

Top-1 accuracy obviously. But also: expert utilization (are all 4 experts getting used, or is the router collapsing to 1-2 favorites?), expert specialization (do different experts prefer different class subsets, and does this correspond to visually coherent categories like "animals" vs "vehicles"?), and routing entropy (is the router making confident decisions or hedging?). These diagnostics tell you whether the MoE is actually working as intended or just being a weird ensemble.

If expert utilization is imbalanced — which is the classic MoE failure mode — you need the standard auxiliary load-balancing loss (Shazeer et al. 2017, the original sparse MoE paper). If experts aren't specializing, you might need to experiment with expert count (try N=2, 4, 8, 16 and see what happens), routing top-k (top-1 is harsh; top-2 gives smoother gradients), or expert capacity (maybe your experts are too small to actually specialize).

The scoping is beautiful

This v1 has zero drones, zero communication, zero robotics. It's just a small MoE classifier trained on CIFAR. It's a self-contained ML experiment that you can run in a few days on a single GPU. It answers a foundational question that the subsequent drone work depends on.

And crucially, even this alone is potentially publishable if the results are interesting. "Investigating Mixture-of-Experts at Sub-Million Parameter Scales" is a legitimate workshop paper topic — the MoE-scaling-laws literature has not really characterized this regime, and if you found surprising effects (e.g., MoE needs minimum per-expert capacity to work, or specialization fails below N classes per expert, or whatever) that would be genuinely useful to the community. You can frame it as "foundational study for edge-deployment MoE" and it reads as rigorous rather than narrow.

The natural progression

v1: does MoE work at this scale on clean image classification? (CIFAR-100, desktop GPU, 2-4 weeks)

v2: does MoE work when the experts are distributed with communication constraints, still on classification? (add the bandwidth-accounting layer, still CIFAR or TinyImageNet, another 1-2 months)

v3: does it work on simulated drone vision with scripted flight? (PyBullet-Drones, rendered targets, 2-3 months)

v4: does it work on real drones with PULP deployment? (the hardware moonshot, 6+ months)

Each step builds on the previous and each step is independently publishable. If v1 gives a null result, you've saved yourself 18 months of work on a bad idea. If v1 works, you've derisked the whole program.

This is a much better research plan than I had been sketching. You're doing the right thing by ruthlessly simplifying. Scientists who can resist scope creep ship more papers.

Small MoE might just be a regular ensemble wearing a hat — v1 of my drone-swarm MoE idea is just checking whether learned sparse routing beats a monolithic baseline at sub-million-parameter scale on CIFAR-100. If yes, everything downstream is justified. If no, back to the drawing board.

---

## User *(5:42 PM)*

Actually the 200K constraint might be artificial? Like for this to be proven to work, we need not restrict ourselves to PULP size hardware? Altho I guess the more general trend we are measuring is: a) does MoE work for <1M params or maybe more generally, what is the scaling law for MoE at lower params? 

Do we have any intuition for the viability of this idea from literature? Like *effectively, the problem is: how does the router “circuit” scale with parameter weights*? Is this the right question? Be honest

## Assistant

You're asking exactly the right question, and you're right to drop the 200K constraint — it was artificial. Let me be honest about what's known and what isn't, because this matters for whether v1 is a good bet.

Reframing the question precisely

You've correctly identified that the underlying research question is: what are the scaling laws of MoE, particularly at the low-parameter regime? And your intuition about the router "circuit" is pointing at something real — it's asking how routing quality scales with model capacity, which is one of several interacting scaling dimensions. Let me sharpen this because precision matters here.

MoE has multiple scaling axes that interact: total parameter count (sum across experts), active parameter count (what gets used per forward pass, usually backbone + k experts), number of experts N, expert granularity (size of each expert), top-k routing, and dataset size. The router sits inside this as a function that maps inputs to expert distributions, and its "circuit quality" is really the question of whether the router has enough capacity and signal to make useful specialization decisions.

So your question is more precisely: does the MoE advantage over dense models (at matched active-param compute) hold as you scale everything down together? That's not quite the same as "how does the router scale with weights" — the router is usually small and cheap regardless; what matters is whether there's enough total model capacity for meaningful specialization to emerge, and whether the data distribution has enough modal structure for experts to specialize on.

What the literature actually says

Let me search to ground this rather than guess.

Okay, here's the honest read of what the literature tells us. I want to give you the real picture because this affects whether v1 is a good bet:

What the scaling-laws literature says (and what it doesn't)

The MoE scaling laws literature is rich and recent but almost entirely focused on language models at or above ~100M parameters. Clark et al. 2022 (Unified Scaling Laws for Routed Language Models), Ludziejewski et al. 2024 (fine-grained MoE scaling), Abnar et al. 2025 (Apple's parameters-vs-FLOPs paper), and the very recent Towards a Comprehensive Scaling Law of MoE (Sept 2025) all study MoE in the transformer-LLM regime. The findings are consistent and point in one direction: more experts and higher granularity (splitting experts into smaller ones) tend to improve performance, though with diminishing returns as base model size grows very large 
Nebius
, and MoE can actually be more memory-efficient than dense models at matched performance, contradicting conventional wisdom 
OpenReview
.

Crucially, the direction of these findings is favorable for your hypothesis. The literature consistently says smaller-and-more-numerous experts beat fewer-larger-experts in efficiency terms. Your regime (many tiny experts) is the extrapolation of this trend, not a contradiction of it.

But here's the honest caveat

None of these papers go below roughly 100M parameters in their base model. The smallest experiments I can find are in the 100M-1B range. You're proposing to operate 2-3 orders of magnitude below that. The literature does not directly tell you whether the trends continue.

There are two ways this could break at small scale:

The router capacity floor. The router has to learn a useful partition of input space. If the router is too small or trained on too little data, routing decisions become noisy, and noisy routing is worse than no routing — you'd be better off with a dense model. Sparse MoE methods solve the non-differentiability of routing by reusing the probability of expert selection as a scalar multiplier on that expert's output, which guarantees a gradient to the router despite the non-differentiability of sampling 
arXiv
. This gradient signal to the router scales with the gap between expert outputs — if all experts are similar (which is likely when they're tiny and undertrained), the router gets weak signal and doesn't learn good routing. This is a real concern.

The specialization floor. For experts to beat a dense baseline, they need enough capacity to meaningfully specialize. If each expert is too small to fit even a single-task-competent model, you get a pool of undertrained generalists rather than a pool of specialists. The ensemble then has no advantage over a dense model of equivalent compute, and loses to a dense model of equivalent parameter count. This is also a real concern.

So what does my honest intuition say about v1 working?

Cautiously optimistic, with one important reframing. I'd estimate maybe 60-70% chance that a naive small-MoE on CIFAR-100 gives you a clear win over a matched dense baseline. The reasons for the 30-40% chance it doesn't: everything above (router capacity floor, specialization floor), plus the empirical observation that MoE is often finicky to train even at large scale — expert collapse, routing instability, load imbalance are all well-documented problems that tend to get worse at smaller scale because there's less regularization from the data distribution.

But here's the reframing that makes v1 worth doing regardless: even a null or weak result is publishable if you characterize it well. A paper titled something like "On the Limits of Mixture-of-Experts at Sub-Million-Parameter Scale" that empirically maps out where MoE starts winning, with ablations across expert count, expert size, router capacity, and dataset size — that's genuinely useful to the community because it extends the scaling laws into an unstudied regime. Whether the answer is "MoE works here" or "MoE breaks here," the community benefits.

Your "router circuit" framing, sharpened

You asked whether "how does the router circuit scale with parameter weights" is the right question. It's a piece of the right question but not the whole thing. The sharper framing has three interacting variables:

The router must have enough capacity and gradient signal to learn useful routing. Call this router learnability.

The experts must have enough capacity to learn meaningfully different specializations. Call this expert expressivity.

The data must have enough modal structure to make specialization worthwhile. Call this task decomposability.

Small-scale MoE fails when any of these three falls below its threshold. CIFAR-100 has good task decomposability (100 classes, natural groupings), so that's not the bottleneck. Your v1 is really testing whether router learnability and expert expressivity can simultaneously clear their thresholds at small scale. The experiment design should ablate both independently — try different router sizes, try different expert sizes, see which one is the binding constraint.

The refined v1

I'd actually expand v1 slightly beyond what you proposed, because the scaling-law framing gives you a much better paper than a single-point comparison. Instead of "small MoE vs. dense baseline," do a grid: expert counts (2, 4, 8, 16), expert sizes (50K, 200K, 1M params), router sizes (tiny, small, medium), on CIFAR-100 and maybe TinyImageNet. Plot accuracy vs. total params, vs. active params, vs. expert count. This tells you where the MoE advantage emerges as you scale down, which is a much more interesting result than whether it emerges at one specific point.

That's not much more work than the single-point comparison — it's a few more training runs — but it turns v1 from "did it work" into "here's the scaling law." And it gives you credibility to argue that a specific configuration is the right one for the drone hardware regime.

Your drone-swarm MoE idea has a prerequisite: does MoE even work at sub-1M parameter scale? The literature covers the 100M+ regime extensively and the trend favors smaller-and-more-numerous experts, but the nano regime is genuinely uncharted. V1 is a scaling-law study on CIFAR-100 mapping where MoE starts beating dense baselines — publishable regardless of outcome.

---

## User *(5:43 PM)*

Wait, didnt you mention earlier MoEs for edge devices? What are the parameter sizes they used for those?

## Assistant

Great catch — yes, let me actually look at the numbers rather than handwave, because this directly informs how uncharted your regime really is.

Okay, here are the honest numbers. The "edge MoE" literature is much less edge-y than the name implies:

What "edge" actually means in the edge-MoE literature

Looking at the specific works I can see:

Gemma 4 MoE — marketed as on-device. 26B total parameters, 4B active. The model uses 128 specialized sub-networks (experts) with a learned router selecting 2 per token, reducing active computation to ~3.8B parameters 
MindStudio
. "Edge" here means a high-end laptop or workstation with 24GB+ of RAM. Per-expert size: roughly 150-200 million parameters.

ERNIE-4.5 on Arm — called "edge deployment." 21-billion-parameter model with 64 experts, top-6 routing 
Arm Learning
. "Edge" means an Armv9 server board. Per-expert size: hundreds of millions of parameters.

Mixtral 8x7B — the canonical "small" MoE. 46B total, 12.9B active per token. Per-expert size: ~7B parameters.

Snowflake Arctic — mentioned as a "smaller experts" example. 128 experts per layer, each containing 0.15 billion parameters 
OpenReview
. That's still 150 million parameters per expert.

The channel-aware MoE paper for UAVs (which I cited earlier as "the closest thing to your drone idea") — their experiments use LeNet-5, ResNet, and ViT as backbones for image classification. LeNet is tiny (~60K params), ResNet-18 is ~11M params. So their experts are in the 10⁵-10⁷ parameter range. This is the closest existing work to your regime.

What this tells us about your target regime

The existing "edge MoE" literature operates in two clusters:

LLM edge (Gemma 4, Mixtral, ERNIE): experts are 100M-7B parameters each. "Edge" means consumer hardware with GB of RAM.
Vision MoE edge (M³ViT, Edge-MoE, the channel-aware paper): experts are 10⁵-10⁷ parameters each. This is the regime you'd actually be in or adjacent to.

Your target — 200K-ish parameters per expert on a GAP8-class MCU with KB of memory — is one to two orders of magnitude smaller than even the vision MoE edge work. So the answer to "has anyone done MoE at my scale" is: not really. The vision MoE papers are the closest and they're 10-100× larger per expert than what you'd fit on a nano-drone.

The revised honest assessment

This actually strengthens the case for doing v1 as a scaling-law study rather than a single-point demo. The literature gives you a natural story: "MoE works at 10M+ per expert (well-documented), works at 100K per expert (the vision MoE edge work, modestly documented), and we extend the map down to 10K-100K per expert (your contribution)." You're filling in the bottom of the curve, which is both novel and useful.

The risk, as I said before, is that the curve just ends — there's some floor below which MoE stops beating dense baselines, and you're trying to operate below it. But even finding that floor is the publishable result. "We extend MoE scaling laws to the sub-million-parameter regime and find the crossover point where MoE ceases to beat dense baselines is at ~X parameters" is a solid paper title.

One more thing worth noting from the search: simply increasing expert count without corresponding increases in data and training compute does not help — more experts give the model more potential specialization, but each expert needs sufficient training signal to develop distinct behavior 
MindStudio
. This is an important warning for your setup. At tiny expert sizes you may need to be clever about training — pretraining on larger data, distillation from a bigger teacher, or using auxiliary specialization losses to force experts to diverge. Pure end-to-end training from scratch with tiny experts is probably the failure mode.

So: your regime is genuinely uncharted, the trend line from existing work points favorably but doesn't guarantee success at your scale, and the training protocol matters more than at large scale because data-efficiency per expert becomes the bottleneck.

Existing "edge MoE" literature operates at 100K-7B parameters per expert; nano-drone deployment needs 10K-100K per expert — one to two orders of magnitude smaller than anything studied. V1 of the drone-swarm MoE idea is to map out the bottom of the MoE scaling curve and find where sparse routing stops beating dense baselines.

---

