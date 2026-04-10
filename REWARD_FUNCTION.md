# Satellite Downlink Scheduler - Reward & Scoring Function

## Overview

All three tasks use **deterministic grading**. The same inputs always produce the same output, ensuring fairness and reproducibility across all evaluation runs.

---

## Task 1: Baseline Downlink (Clear Sky)

**Objective**: Maximize raw throughput of routine data.

**Formula**:
$$Score = \frac{\text{Bytes Downloaded}}{\text{Bytes Available}}$$

**Explanation**:
- `Bytes Downloaded`: Sum of all data chunks successfully downlinked across the 144-tick mission.
- `Bytes Available`: Total capacity of the initial satellite queues.
- **Constraints**: No priority weighting.

**Expected Performance**:
- **Random Agent**: ~0.15
- **Greedy Agent**: ~0.75
- **Perfect Agent**: 1.0 (Theoretical)
- **Baseline (Qwen 2.5 7B)**: **0.9991**

---

## Task 2: Weather Resilience (Priority-Weighted)

**Objective**: Maximize priority-weighted throughput under link degradation.

**Formula**:
$$Score = \frac{\sum (W_p \cdot \text{Bytes Downloaded}_p)}{\sum (W_p \cdot \text{Bytes Available}_p)}$$

**Priority Weights ($W_p$):**
- **Priority 1 (Routine)**: 1.0
- **Priority 2 (Important)**: 10.0
- **Priority 3 (Emergency)**: 100.0

**Explanation**:
- Downloading 1 MB of Priority 3 data is mathematically equivalent to 100 MB of Priority 1 data.
- **Weather Factor**: Link quality [0.0, 1.0] fluctuates. High-quality windows should be reserved for high-priority data to maximize efficiency.

**Expected Performance**:
- **Random Agent**: ~0.05
- **Greedy Agent**: ~0.45 (Ignores priority logic)
- **Priority-Aware Heuristic**: ~0.70
- **Baseline (Qwen 2.5 7B)**: **0.9984**

---

## Task 3: Emergency Response (Weighted + Deadline Penalties)

**Objective**: Maximize weighted throughput while meeting strict emergency deadlines.

**Formula**:
$$Score = 0.4 \cdot \text{Base Score} + 0.6 \cdot \text{Emergency Score} - \sum \text{Delay Penalties}$$
$$Score = \max(Score, 0.0)$$

**1. Base Score (0.4 weight)**
Identical to Task 2 (Priority-weighted throughput).

**2. Emergency Score (0.6 weight)**
The fraction of the emergency burst data (P3) that was successfully downlinked (regardless of deadline).

**3. Delay Penalties ($P_d$)**
Subtracted for each emergency chunk with a deadline:
- **On-time Delivery**: $0.0$ penalty.
- **Late Delivery**: $0.5 \cdot \min\left(\frac{delay\_minutes}{60}, 1.0\right)$
- **Never Delivered**: $0.5$ (Maximum penalty per chunk).

**Expected Performance**:
- **Random Agent**: ~0.001 (Fails deadlines)
- **Ignores Emergencies**: ~0.30
- **Strong Heuristic**: ~0.65 - 0.75
- **Baseline (Qwen 2.5 7B)**: **0.8295** (Hardened)

---

## Verification & Reproducibility

The grading engine (`src/envs/satellite_env/server/graders.py`) is fully deterministic. It relies on the `DownlinkResult` log produced by the scheduler and the scenario static files. This ensures that any agent run can be audited and verified against the telemetry.
