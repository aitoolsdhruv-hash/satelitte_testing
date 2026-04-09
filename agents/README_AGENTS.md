# Reference Baseline Agents

This directory contains three baseline agents designed to demonstrate the environment's mechanics and provide verifiable results for reproducibility.

---

## 📋 Agent Comparison

| Agent | Category | Task 1 | Task 2 | Task 3 | Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Random** | Baseline | ~0.15 | ~0.05 | ~0.001 | Picks 1-5 random windows per tick. |
| **Greedy** | Heuristic | ~0.75 | ~0.45 | ~0.30 | Priority-blind throughput optimization. |
| **Rule** | Advanced | ~0.75 | ~0.68 | ~0.55 | Priority-aware triage + weather logic. |
| **Qwen 2.5** | SOTA | **0.9991** | **0.9984** | **0.9971** | Full state reasoning via LLM. |

---

## 🚀 How to Run

Before running an agent, ensure the environment server is active:

```bash
# Terminal 1: Start Server
export SATELLITE_TASK=task3
uvicorn src.envs.satellite_env.server.app:app --host 0.0.0.0 --port 7860
```

### 1. Random Agent
Verifies that the API connection and action schemas are correct.
```bash
python agents/random_agent.py --task task1
```

### 2. Greedy Agent
Demonstrates performance when ignoring data priorities.
```bash
python agents/greedy_agent.py --task task2
```

### 3. Rule Agent (Recommended Baseline)
The most sophisticated heuristic. It understands priority weights and deadline pressure.
```bash
python agents/rule_agent.py --task task3
```

---

## 🛠️ Implementation Details

### `random_agent.py`
- Acts as a "sanity check" for the environment.
- Respects station / satellite uniqueness (one per tick).
- Provides the lower bound for scoring.

### `greedy_agent.py`
- Focuses purely on `link_quality`.
- Useful for measuring the maximum "raw bits" the constellation can down-link in perfect vs. degraded weather, without regard for *which* bits are high-value.

### `rule_agent.py`
- Implements the mathematical triage logic described in `REWARD_FUNCTION.md`.
- Prioritizes Priority 3 (Emergency) and Priority 2 (Important) data.
- **Task 3 Logic**: Aggressively schedules satellites with chunks approaching their 60/120-minute deadlines.
