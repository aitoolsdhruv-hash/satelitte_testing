# inference.py - Satellite Downlink Scheduler Baseline
# Strictly follows the OpenEnv mandatory logging format.

import json
import os
import sys
import textwrap
import time
from typing import List, Optional
from openai import OpenAI

# ── Imports (after path setup) ────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.envs.satellite_env.client import SatelliteEnv
from src.envs.satellite_env.models import SatelliteAction, SatelliteObservation

# ── Mandatory Environment Configuration ──────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:11434/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")
HF_TOKEN = os.getenv("HF_TOKEN", "ollama") 
ENV_URL = os.getenv("ENV_URL", "http://localhost:8000")

# ── Inference Parameters ─────────────────────────────────────
MAX_STEPS = 144
TEMPERATURE = 0.2
MAX_TOKENS = 512
BENCHMARK = "satellite_downlink_scheduler"

SYSTEM_PROMPT = textwrap.dedent("""
    You are an autonomous satellite mission planner. Your goal is to maximise priority-weighted bytes.
    
    PLANNING RULES:
    1. MULTI-STATION USAGE: You have multiple ground stations (usually 2, 4, or 6). Use as many as possible concurrently.
    2. CONCURRENCY: In the "schedules" array, provide windows for AS MANY STATIONS AS POSSIBLE if multiple satellites have valid windows.
    3. COVERAGE: Prioritise satellites with larger buffers and higher priority (p3, p5).
    4. NOOP: Use {"action_type": "noop"} ONLY if windows are empty for the CURRENT TICK or stations are down.
    5. WEATHER AWARENESS: Stations with 0.0 availability are OFFLINE. Do not schedule to them. Stations with < 0.5 are unstable; prefer HIGHER availability first.
    6. EMERGENCY TRIAGE: Priority p3 (Emergency) chunks marked [URGENT] are CRITICAL. They have a 60-minute deadline. You MUST schedule them immediately on the first available [ONLINE] station. Do NOT wait for a better window or link quality.
    7. BATCHING: Prefer multiple schedules in one tick to earn the 0.01 concurrency bonus.
    
    Example 1 (Nominal/Batching):
    Observation:
    CURRENT TIME: Step 1 | tick=0
    SATELLITES REMAINING/BUFFER: sat0=21878MB, sat1=21134MB
    STATION AVAILABILITY: {'0': 1.0, '1': 1.0}
    WINDOWS AVAILABLE: id=w1 sat=0 stn=0, id=w2 sat=1 stn=1
    Response:
    {"action_type": "schedule_multiple", "schedules": [{"sat_id": 0, "station_id": 0, "window_id": "w1"}, {"sat_id": 1, "station_id": 1, "window_id": "w2"}]}

    Example 2 (Priority Triage):
    Observation:
    CURRENT TIME: Step 20 | tick=2
    SATELLITES REMAINING/BUFFER: sat5=15000MB (p5), sat2=12000MB (p2)
    STATION AVAILABILITY: {'0': 1.0, '1': 1.0}
    WINDOWS AVAILABLE: id=w3 sat=5 stn=0, id=w4 sat=2 stn=0
    Response:
    {"action_type": "schedule_multiple", "schedules": [{"sat_id": 5, "station_id": 0, "window_id": "w3"}]}

    Example 3 (Emergency + Weather Dropout):
    Observation:
    CURRENT TIME: Step 50 | tick=24
    SATELLITES REMAINING/BUFFER: sat10=5000MB (p3), sat1=8000MB (p2)
    STATION AVAILABILITY: {'0': 0.0 [OFFLINE], '1': 1.0, '2': 0.1 [OFFLINE]}
    WINDOWS AVAILABLE AT TICK 24: 
      id=w_s10_g0_024 sat=10 stn=0 q=1.00 (STATION OFFLINE)
      id=w_s10_g1_024 sat=10 stn=1 q=1.00
      id=w_s1_g2_024 sat=1 stn=2 q=1.00 (STATION OFFLINE)
    Response:
    {"action_type": "schedule_multiple", "schedules": [{"sat_id": 10, "station_id": 1, "window_id": "w_s10_g1_024"}]}

    Example 4 (No-Op):
    Observation:
    SATELLITES REMAINING: sat4=3000MB
    STATION AVAILABILITY: {'0': 0.0 [OFFLINE]}
    WINDOWS AVAILABLE AT TICK 5: (none)
    Response:
    {"action_type": "noop"}

    Available actions (respond with EXACTLY ONE JSON object):
        {"action_type": "schedule_multiple", "schedules": [{"sat_id": int, "station_id": int, "window_id": str}, ...]}
        {"action_type": "noop"}

    Respond with ONLY valid JSON.
""").strip()

# ── Helper functions for the automated judge ─────────────────

def _format_action_tag(action: SatelliteAction) -> str:
    if action.action_type == "schedule_multiple" and action.schedules:
        items = [f"sat{s.get('sat_id')}->stn{s.get('station_id')}" for s in action.schedules]
        return f"schedule_multiple([{', '.join(items)}])"
    return f"{action.action_type}()"

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: SatelliteAction, reward: float, done: bool, info: dict) -> None:
    error_val = info.get("action_error") if info.get("action_error") else "null"
    done_val = str(done).lower()
    action_str = _format_action_tag(action)
    raw = info.get("bytes_this_tick", 0)
    norm = info.get("normalizer", 0)
    print(f"[STEP] step={step} action={action_str} reward={reward:.2f} done={done_val} error={error_val} raw={raw} norm={norm:.0f}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.4f} rewards={rewards_str}", flush=True)

def _obs_to_prompt(obs: SatelliteObservation, step: int) -> str:
    current_tick = obs.current_time_min // 10
    avail = obs.station_availability
    buf_bytes = obs.satellite_buffer_bytes
    active_sats = {sid for sid, buf in buf_bytes.items() if buf > 0}
    
    # Separate windows
    now_windows, future_windows = [], []
    for w in obs.pass_windows:
        sid_str = str(w.sat_id)
        if sid_str not in active_sats: continue
        if w.tick == current_tick:
            now_windows.append(w)
        elif w.tick > current_tick:
            future_windows.append(w)

    future_windows.sort(key=lambda x: (x.tick, -x.link_quality))
    
    now_text = "\n".join(
        f"  id={w.window_id} sat={w.sat_id} stn={w.station_id} q={w.link_quality:.2f} buf={buf_bytes.get(str(w.sat_id),0)//1_000_000}MB"
        for w in now_windows
    ) or "  (none available right now)"

    future_text = "\n".join(
        f"  tick={w.tick} sat={w.sat_id} stn={w.station_id} q={w.link_quality:.2f}"
        for w in future_windows[:12]
    ) or "  (none)"
    
    queues_text = []
    urgent_sats = set()
    for sid, chunks in obs.data_priority_queues.items():
        if chunks:
            top = max(chunks, key=lambda c: c.priority)
            deadline = f" deadline={top.deadline_min}min" if top.deadline_min else ""
            queues_text.append(f"  sat{sid}: p{top.priority}{deadline}")
            if top.priority == 3:
                urgent_sats.add(sid)
    
    remaining_sats = []
    for sid, buf in sorted(buf_bytes.items()):
        if buf > 0:
            prefix = "[URGENT] " if sid in urgent_sats else ""
            remaining_sats.append(f"{prefix}sat{sid}={buf//1_000_000}MB")
    
    remaining_summary = ", ".join(remaining_sats) if remaining_sats else "ALL EMPTY"

    avail_status = []
    for sid_str, a in sorted(avail.items()):
        status = " [OFFLINE]" if a < 0.5 else ""
        avail_status.append(f"'{sid_str}': {a}{status}")
    avail_text = "{" + ", ".join(avail_status) + "}"
    queues_summary = "\n".join(queues_text) if queues_text else "  (empty)"
    
    return textwrap.dedent(f"""
        CURRENT TIME: Step {step} | tick={current_tick}
        SATELLITES REMAINING/BUFFER: {remaining_summary}
        STATION AVAILABILITY: {avail_text}
        WINDOWS AVAILABLE AT TICK {current_tick} (SCHEDULE THESE NOW!):
        {now_text}
        FUTURE WINDOWS (WAIT FOR THESE):
        {future_text}
        PRIORITY QUEUES:
        {queues_summary}
        EMERGENCY: {obs.info.get('emergency_injection', False)}
    """).strip()

def get_action(client: OpenAI, obs: SatelliteObservation, step: int) -> SatelliteAction:
    user_prompt = _obs_to_prompt(obs, step)
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        text = (completion.choices[0].message.content or "").strip()
        if "{" in text and "}" in text:
            text = text[text.find("{"):text.rfind("}")+1]
        
        data = json.loads(text)
        return SatelliteAction(**data)
    except Exception:
        # Silently fail to noop to preserve [START][STEP][END] stdout cleanliness
        return SatelliteAction(action_type="noop")

def run_task(env: SatelliteEnv, client: OpenAI, task_name: str, max_steps: int) -> float:
    rewards_list, steps_taken, score, success = [], 0, 0.0, False
    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)
    try:
        obs = env.reset(task=task_name).observation
        for step in range(1, max_steps + 1):
            if obs.done: break
            action = get_action(client, obs, step)
            # Backend constraint: Deduplicate stations if LLM Hallucinates
            # Backend constraint: Deduplicate stations and satellites if LLM Hallucinates
            if action.action_type == "schedule_multiple" and action.schedules:
                unique, seen_stn, seen_sat = [], set(), set()
                for s in action.schedules:
                    stn, sat = s.get("station_id"), s.get("sat_id")
                    if stn not in seen_stn and sat not in seen_sat:
                        unique.append(s)
                        seen_stn.add(stn); seen_sat.add(sat)
                action.schedules = unique
            
            obs = env.step(action).observation
            reward = obs.info_dict.get("reward_last_tick", 0.0)
            rewards_list.append(reward)
            steps_taken = step
            log_step(step=step, action=action, reward=reward, done=obs.done, info=obs.info_dict)
            if obs.done: break
        
        score = env.state().final_score
        success = score >= 0.7
    except Exception:
        # Standard error handled by log_end caller or final scoring
        pass
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards_list)
        return score

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=str, default=None, help="Task to run (task1, task2, task3). If None, runs all.")
    parser.add_argument("--max-steps", type=int, default=144, help="Max steps per task.")
    args = parser.parse_args()

    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    with SatelliteEnv(base_url=ENV_URL).sync() as env:
        tasks = [args.task] if args.task else ["task1", "task2", "task3"]
        for t in tasks:
            run_task(env, client, t, args.max_steps)

if __name__ == '__main__':
    main()
