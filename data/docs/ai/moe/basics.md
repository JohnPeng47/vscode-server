# Mixture of Experts (MoE) — Basics

## The Problem

Dense neural networks activate **every parameter** for every input. A model with
100 billion parameters uses all 100B weights to process the sentence "hello world"
the same way it processes a complex physics derivation. This creates a brutal
tradeoff:

- **Want better quality?** → Add more parameters → training and inference cost
  grows linearly with model size.
- **Want lower cost?** → Use fewer parameters → quality degrades.

You're stuck on a single curve: *capability scales with compute*.

## The MoE Insight

What if most parameters exist but only a **small subset activates per input**?

The core idea: replace a single large feedforward layer with N smaller "expert"
sub-networks, and add a lightweight **gating network (router)** that decides which
experts to activate for each token. Typically only the top-k experts (k=1 or k=2)
fire per token.

This decouples **total model capacity** (all parameters) from **per-token compute**
(active parameters). You get the quality of a huge model at the inference cost of
a much smaller one.

## High-Level Architecture

```
                         ┌─────────────────────────────────────┐
                         │           Input Token (x)           │
                         └──────────────────┬──────────────────┘
                                            │
                                            ▼
                         ┌─────────────────────────────────────┐
                         │          Self-Attention Layer        │
                         │         (same as dense model)        │
                         └──────────────────┬──────────────────┘
                                            │
                      ┌─────────────────────┼─────────────────────┐
                      │                     │                     │
                      │                     ▼                     │
                      │  ┌─────────────────────────────────────┐  │
                      │  │         Router / Gating Network      │  │
                      │  │                                      │  │
                      │  │  G(x) = Softmax(W_g · x)            │  │
                      │  │  Select top-k experts by score       │  │
                      │  └──┬──────────┬──────────┬──────────┬─┘  │
                      │     │          │          │          │     │
                      │     ▼          ▼          ▼          ▼     │
                      │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  │
                      │  │Expert│  │Expert│  │Expert│  │Expert│  │  MoE
                      │  │  1   │  │  2   │  │  3   │  │  N   │  │  Block
                      │  │(FFN) │  │(FFN) │  │(FFN) │  │(FFN) │  │  (replaces
                      │  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘  │  dense FFN)
                      │     │          │          │          │     │
                      │     │    ┌─────┘          │          │     │
                      │     │    │   (only top-k  │          │     │
                      │     │    │    activate)    │          │     │
                      │     ▼    ▼                 ▼          ▼     │
                      │  ┌─────────────────────────────────────┐  │
                      │  │   Weighted Sum of Active Experts     │  │
                      │  │   y = Σ g_i(x) · Expert_i(x)        │  │
                      │  └─────────────────────────────────────┘  │
                      └─────────────────────┬─────────────────────┘
                                            │
                                            ▼
                         ┌─────────────────────────────────────┐
                         │       Layer Norm + Residual          │
                         └──────────────────┬──────────────────┘
                                            │
                                            ▼
                                   (next layer ...)
```

## How the Router Works

The gating network is a simple linear projection + softmax:

1. Each token embedding `x` is projected to N scores (one per expert)
2. Top-k scores are kept; the rest are zeroed out
3. The kept scores are re-normalized into weights that sum to 1
4. Output = weighted combination of only the active experts' outputs

## Key Numbers (typical)

| Property              | Dense Model        | MoE Model                  |
|-----------------------|--------------------|----------------------------|
| Total parameters      | 70B                | 140B (8 experts)           |
| Active params/token   | 70B                | ~12-18B (top-2 routing)    |
| Inference FLOPS       | Proportional to 70B| Proportional to ~18B       |
| Quality               | Baseline           | ≈ matches or beats dense   |
| Memory (weights)      | 70B                | 140B (must store all)      |

The tradeoff: MoE models need more **memory** (all experts must be loaded) but
use far less **compute** per token. This is why MoE shines on hardware with large
memory but where FLOPS are the bottleneck.

## The Load Balancing Problem

If the router keeps sending tokens to the same few experts, the others are wasted.
This is called **expert collapse**. Solutions:

- **Auxiliary load-balancing loss**: penalize uneven expert utilization during training
- **Expert capacity limits**: cap how many tokens each expert can handle per batch
- **Noisy gating**: add noise to router scores during training to encourage exploration

## Notable MoE Models

- **Switch Transformer** (Google, 2021) — showed k=1 routing works, simplified MoE
- **Mixtral 8x7B** (Mistral, 2023) — 8 experts, 2 active; matched Llama 2 70B at
  ~13B active params
- **DeepSeek-V2/V3** (DeepSeek, 2024) — fine-grained experts with shared experts,
  pushed MoE efficiency further
- **GPT-4** — widely reported to use MoE (unconfirmed by OpenAI)

## TL;DR

MoE solves *"bigger models are better but cost more"* by making models **sparsely
activated** — large total capacity, small per-token cost. The router learns which
experts are relevant for each input, giving you the quality of a dense giant at a
fraction of the compute.
