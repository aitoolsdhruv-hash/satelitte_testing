---
title: Satellite Downlink Scheduler
emoji: 🛰️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
tags:
  - openenv
  - scheduling
  - satellite
  - real-world
  - reinforcement-learning
short_description: OpenEnv LEO Satellite Downlink Scheduling Environment
---

# Satellite Downlink Scheduler 🛰️

A production-grade reinforcement learning environment simulating a 15-satellite LEO constellation scheduling challenge. This project is optimized for the **Meta-OpenEnv Hackathon**.

---

## 🏗️ 1. Project Overview

This environment simulates the operational complexity of managing a high-concurrency satellite fleet. Agents must coordinate downlinks between **15 satellites** and **6 shared ground stations** to maximize data throughput while navigating weather degradation and urgent emergency bursts.

### 🌌 The Physical Model (v1.2.0)
- **Constellation**: 15 satellites with diverse buffer capacities and orbital mechanics.
- **Ground Network**: 6 globally distributed stations (Svalbard, Bangalore, Fairbanks, etc.).
- **Action Interface**: **Batch (N / tick)** — Simultaneous coordination of the entire network in a single step.
- **Physics**: Real elevation-based throughput calculations and orbital pass windowing.

### 📈 Final Benchmark Results
Verified using the official `qwen2.5:7b` instruction agent.

| Task | Objective | Score | Status |
| :--- | :--- | :--- | :--- |
| **Task 1** | Baseline Downlink (Clear Sky) | **0.9991** | ✅ PASSED |
| **Task 2** | Weather Resilience (Variable Avail) | **0.9984** | ✅ PASSED |
| **Task 3** | Crisis Response (Emergencies) | **0.8295** | ✅ PASSED |

---

## 🧪 2. Environment Interface

### State & Action Spaces
The environment provides a high-dimensionality observation space and a flexible batch-action space.
- **State**: Includes satellite orbits, buffer levels, priority queues, and dynamic weather status.
- **Action**: Supports multi-coordinated downlinks using the `schedule_multiple` action type.

For the full JSON schema and operational constraints, see [**TECHNICAL_SPECIFICATION.md**](TECHNICAL_SPECIFICATION.md).

### Scoring & Rewards
Grades are deterministic and based on priority-weighted throughput and deadline compliance.
- **Task 1**: Raw bytes over bytes available.
- **Task 2**: Priority-weighted efficiency.
- **Task 3**: Crisis management + late-delivery penalties.

For exact mathematical formulas and breakdown examples, see [**REWARD_FUNCTION.md**](REWARD_FUNCTION.md).

---

## 🤖 3. Reference Agents & Solvability
To ensure baseline reproducibility, we provide three reference agents in the `agents/` directory:
- **Random Agent**: Absolute baseline (checks env integrity).
- **Greedy Agent**: Naive throughput maximization (no priority awareness).
- **Priority Agent**: Smart rule-based heuristic (high-performance benchmark).

See [**agents/README_AGENTS.md**](agents/README_AGENTS.md) for implementation details and baseline comparisons.

---

## 🛠️ 4. Installation & Local Setup

### Prerequisites
- Python 3.11+
- [**uv**](https://github.com/astral-sh/uv) (Recommended for dependency management)
- (Optional) Ollama for local LLM testing

### Local Development
```bash
# Clone and install dependencies
git clone <your-repo>
cd Satellite
uv sync
```

---

## 🚀 5. Running the Environment

### Terminal 1: Environment Server
```powershell
# PowerShell (Recommended for Windows stability)
$env:SATELLITE_TASK='task3'
uv run python -m uvicorn src.envs.satellite_env.server.app:app --host 127.0.0.1 --port 7860
```

### Terminal 2: Baseline Inference
```powershell
$env:ENV_URL="http://127.0.0.1:7860"
$env:API_BASE_URL="http://localhost:11434/v1"
$env:MODEL_NAME="qwen2.5:7b"
uv run python inference.py --task task3
```

> [!NOTE]
> **Windows Networking**: Use `127.0.0.1` instead of `localhost` in your environment variables to ensure stable WebSocket connections.

---

## 📋 6. Submission Details

### Project Organization
```text
Satellite/
├── Dockerfile                # Build definition
├── inference.py              # Entry point for evaluation
├── openenv.yaml              # Manifest for task mapping
├── agents/                   # [NEW] Reference baseline agents
├── tests/                    # [NEW] Logic & compliance tests
├── data/                     # Scenario definitions
└── src/envs/satellite_env/   # Environment implementation
```

### Audit Checklist
For a full breakdown of submission compliance and how to verify the environment, see [**SUBMISSION_CHECKLIST.md**](SUBMISSION_CHECKLIST.md).

---

## 🛡️ 7. License
Licensed under the [**MIT License**](LICENSE).