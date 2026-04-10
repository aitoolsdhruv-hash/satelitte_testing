# Submission Verification Checklist

This checklist provides a clear audit path for judges to verify the technical compliance and performance benchmarks of the **Satellite Downlink Scheduler** submission.

---

## 🏗️ Phase 1: Structural & API Integrity

- [ ] **Docker Build**: `docker build -t satellite-scheduler .` builds successfully.
- [ ] **Entry Point**: `inference.py` exists in the root directory and is executable.
- [ ] **Standard Logging**: Script emits `[START]`, `[STEP]`, and `[END]` markers to stdout.
- [ ] **OpenEnv Compliance**: `openenv.yaml` manifest is present and correctly maps tasks.
- [ ] **Core Endpoints**: Environment server responds to `/reset`, `/step`, `/state`, and `/health` on port 7860.

---

## 📈 Phase 2: Scoring & Determinism

- [ ] **Deterministic Results**: Running the same task twice with the `Priority Agent` produces identical rewards and scores.
- [ ] **Range Check**: All task graders output values strictly within the `[0.0, 1.0]` range.
- [ ] **Difficulty Progression**: Benchmarks show Task 1 (Baseline) ≥ Task 2 (Weather) ≥ Task 3 (Crisis).
- [ ] **Reward Transparency**: Final scores align with the mathematical models defined in `REWARD_FUNCTION.md`.

---

## 📝 Phase 3: Documentation & Reproducibility

- [ ] **Technical Specification**: Observation and Action spaces are formally defined.
- [ ] **Reward Guide**: Task-specific scoring math is explained with examples.
- [ ] **Reference Agents**: Baseline agents (Random, Greedy, Priority) are provided in the `agents/` directory for verification.
- [ ] **RL Guidance**: Training strategies and vectorization tips are provided for developers.
- [ ] **Hallucination Defense**: Agent logic in `inference.py` includes recovery and filtering for protocol robustness.

---

## 🚀 Quick Verification via Reference Agents

Run these commands to verify the environment handles different logic complexities correctly:

```bash
# Verify baseline throughput
uv run python agents/greedy_agent.py --task task1

# Verify priority-weighting logic
uv run python agents/rule_agent.py --task task2

# Verify deadline-sensitive crisis management (Task 3)
uv run python agents/rule_agent.py --task task3

# Verify Hardened LLM Inference (Task 3)
uv run python inference.py --task task3
```

**Expected results match the "Consolidated Benchmark Table" in the root README.**
