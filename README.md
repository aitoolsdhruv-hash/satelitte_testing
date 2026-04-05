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
short_description: OpenEnv environment — LEO satellite downlink scheduling
---

# Satellite Downlink Scheduler 🛰️

This project simulates a real-world operational challenge: scheduling contact windows for a constellation of satellites to maximize data download. It is built for the *Meta-OpenEnv Hackathon*.

---

## 1. Project Overview

The simulation is a clock-driven environment where time moves in 10-minute ticks. A full episode represents a 24-hour planning horizon (144 ticks).

### The Physical Model

* **Satellites (8 total)**: Low-Earth-Orbit satellites with onboard data buffers.
* **Ground Stations (4 total)**: Svalbard, McMurdo, Bangalore, Fairbanks. Each can serve only ONE satellite at a time.
* **Pass Windows**: Precomputed visibility windows stored in `data/scenarios/`.

### The Challenges

* **Resource Contention**: Multiple satellites competing for the same station.
* **Weather (Tasks 2 & 3)**: Degrades link quality dynamically.
* **Priority**: Higher-priority data yields higher reward.
* **Emergencies (Task 3)**: Deadline-based urgent data with penalties.

---

## 2. Project Structure (Submission-Ready)

```text
Satellite/
├── Dockerfile                # REQUIRED (root-level)
├── requirements.txt          # REQUIRED (dependencies for Docker)
├── pyproject.toml
├── inference.py              # REQUIRED (entry for evaluation)
├── openenv.yaml              # REQUIRED (OpenEnv manifest)
├── README.md
├── .dockerignore
├── .gitignore
├── data/                     # REQUIRED (precomputed scenarios)
└── src/
    └── envs/
        └── satellite_env/
            ├── models.py     # Shared Pydantic models
            ├── client.py     # OpenEnv client implementation
            └── server/
                ├── app.py           # FastAPI entrypoint
                ├── environment.py   # Core logic
                ├── graders.py       # Scoring functions
                ├── scheduler.py     # Conflict detection
                └── weather.py       # Weather simulation
```

---

## 3. API Requirements (MANDATORY FOR VALIDATION)

The server MUST expose the following REST endpoints:

* **POST /reset** → Initialize environment
* **POST /step** → Execute action
* **GET /state** → Return current state
* **GET /health** → Docker health check

⚠️ WebSocket (`/ws`) support is available but does NOT replace REST endpoints.

---

## 4. Installation & Setup

### Prerequisites

* Python 3.11+
* Docker
* (Optional) Ollama for local LLM testing

### Local Setup

```bash
git clone <your-repo>
cd Satellite
pip install -e .
python scripts/generate_windows.py
```

---

## 5. Running Locally

### Terminal 1: Environment Server

```bash
export SATELLITE_TASK=task1
python -m uvicorn src.envs.satellite_env.server.app:app --host 0.0.0.0 --port 7860
```

### Terminal 2: Inference Agent

```bash
export API_BASE_URL=http://localhost:11434/v1   # LLM endpoint (NOT env server)
export MODEL_NAME=qwen2.5:7b-instruct-q4_k_m
export HF_TOKEN=ollama

python inference.py
```

---

## 6. Environment Variables

| Variable | Purpose |
| :--- | :--- |
| `API_BASE_URL` | LLM endpoint (Ollama or HF router) |
| `MODEL_NAME` | Model used for inference |
| `HF_TOKEN` | Authentication token |
| `SATELLITE_TASK` | Task to run (task1, task2, task3) |

---

## 11. Mandatory Logging Format

Your `inference.py` MUST emit EXACTLY:

```text
[START] task=<task_name> env=<benchmark> model=<model_name>
[STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
[END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
```

⚠️ Any deviation will cause evaluation failure.