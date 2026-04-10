"""
Priority-Aware Rule Agent - High-Performance Heuristic

Strategy:
1. Identify satellites with the most urgent data (Emergency > Important > Routine).
2. For Task 3, prioritize chunks closest to their deadline.
3. Factor in station link quality to avoid wasting windows on degraded links.
4. Batch-schedule optimal non-conflicting assignments.

This represents a "smart" baseline that should significantly outperform greedy/random.
"""

import argparse
import os
from typing import List, Dict

from src.envs.satellite_env.client import SatelliteEnv
from src.envs.satellite_env.models import SatelliteAction, PassWindowModel


PRIORITY_WEIGHTS = {1: 1.0, 2: 10.0, 3: 100.0}

def score_satellite_urgency(sat_id: str, observation) -> float:
    """
    Calculates an urgency score for a satellite based on its top priority chunks
    and impending deadlines.
    """
    queues = observation.data_priority_queues.get(sat_id, [])
    if not queues:
        return 0.0

    # Base urgency is the max priority in the queue
    max_p = max(q.priority for q in queues)
    score = PRIORITY_WEIGHTS.get(max_p, 1.0)

    # Deadline pressure (Task 3)
    # If a p3 chunk is close to deadline, boost score significantly
    current_min = observation.current_time_min
    for q in queues:
        if q.priority == 3 and q.deadline_min is not None:
            time_left = q.deadline_min - current_min
            if time_left <= 60: # 1 hour remains
                score += 500.0
            elif time_left <= 120: # 2 hours remain
                score += 200.0
    
    return score


def rule_agent_step(observation) -> SatelliteAction:
    """
    Rule-based triage:
    1. Score satellites by weighted urgency.
    2. Map high-urgency satellites to their best available clear-sky stations.
    3. Maximize throughput while respecting physical constraints.
    """
    current_tick = observation.current_time_min // 10
    
    # Filter current windows
    windows = [w for w in observation.pass_windows if w.tick == current_tick]
    if not windows:
        return SatelliteAction(action_type="noop")

    # 1. Score all satellites
    sat_scores = {
        sat_id: score_satellite_urgency(sat_id, observation)
        for sat_id in observation.satellite_buffer_bytes.keys()
    }

    # 2. Group windows by satellite
    sat_to_windows = {}
    for w in windows:
        if w.sat_id not in sat_to_windows:
            sat_to_windows[w.sat_id] = []
        sat_to_windows[w.sat_id].append(w)

    # 3. Sort satellites by urgency score (descending)
    sorted_sats = sorted(sat_scores.keys(), key=lambda s: sat_scores[s], reverse=True)

    schedules = []
    used_stations = set()
    used_sats = set()

    # 4. Greedy Assignment by Urgency
    for sat_id_str in sorted_sats:
        sat_id = int(sat_id_str)
        if sat_scores[sat_id_str] <= 0:
            continue
            
        sat_windows = sat_to_windows.get(sat_id, [])
        if not sat_windows:
            continue

        # Sort windows for this sat by link quality
        sat_windows.sort(key=lambda w: w.link_quality, reverse=True)

        for w in sat_windows:
            if w.station_id in used_stations:
                continue
            
            # Weather check: prefer links with > 50% quality for high priority
            # But take anything if deadline is tight
            avail = observation.station_availability.get(str(w.station_id), 1.0)
            if avail < 0.2: # Hard offline
                continue
            
            # If it's a routine task and link is bad, maybe wait? 
            # (Simplified: just take the best quality one)
            schedules.append({
                "sat_id": w.sat_id,
                "station_id": w.station_id,
                "window_id": w.window_id
            })
            used_stations.add(w.station_id)
            used_sats.add(w.sat_id)
            break # Assigned this sat, move to next most urgent

    if not schedules:
        return SatelliteAction(action_type="noop")

    return SatelliteAction(action_type="schedule_multiple", schedules=schedules)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=str, default="task3", choices=["task1", "task2", "task3"])
    parser.add_argument("--url", type=str, default=os.getenv("ENV_URL", "http://localhost:7860"))
    args = parser.parse_args()

    print(f"🧠 Starting Priority-Aware Rule Agent for {args.task}...")
    
    with SatelliteEnv(base_url=args.url).sync() as env:
        obs = env.reset(task=args.task).observation
        
        step = 0
        while not obs.done:
            step += 1
            action = rule_agent_step(obs)
            obs = env.step(action).observation
            
            if step % 20 == 0:
                print(f"Step {step}: Last Tick Reward = {obs.reward:.4f}")

        state = env.state()
        print(f"\n✅ Mission Complete!")
        print(f"Final Score: {state.final_score:.4f}")
        print(f"Breakdown: {obs.reward_obj.breakdown}")


if __name__ == "__main__":
    main()
