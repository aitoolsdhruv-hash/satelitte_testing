"""
Greedy Agent - Heuristic Baseline

Strategy: Maximize raw throughput by selecting windows with the best link quality.
Ignores priority weighting — useful for measuring Task 1 efficiency ceiling.
"""

import argparse
import os
from typing import List

from src.envs.satellite_env.client import SatelliteEnv
from src.envs.satellite_env.models import SatelliteAction, PassWindowModel


def greedy_agent_step(observation) -> SatelliteAction:
    """
    Schedules all non-conflicting windows for the current tick, 
    sorted by theoretical max transfer (link_quality * duration).
    """
    current_tick = observation.current_time_min // 10
    
    # 1. Gather all windows for the current tick
    windows = [w for w in observation.pass_windows if w.tick == current_tick]
    
    if not windows:
        return SatelliteAction(action_type="noop")

    # 2. Sort by "Best Pipe" (Link Quality * Duration)
    # This ignores the 'Priority' of the data in the queue
    windows.sort(key=lambda w: (w.link_quality * w.duration_s), reverse=True)

    schedules = []
    used_sats = set()
    used_stations = set()

    # 3. Commit non-conflicting windows
    for w in windows:
        if w.sat_id in used_sats or w.station_id in used_stations:
            continue
            
        # Weather check: if station is offline or severely degraded, skip
        avail = observation.station_availability.get(str(w.station_id), 1.0)
        if avail < 0.3:
            continue

        schedules.append({
            "sat_id": w.sat_id,
            "station_id": w.station_id,
            "window_id": w.window_id
        })
        used_sats.add(w.sat_id)
        used_stations.add(w.station_id)

    if not schedules:
        return SatelliteAction(action_type="noop")

    return SatelliteAction(action_type="schedule_multiple", schedules=schedules)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=str, default="task1", choices=["task1", "task2", "task3"])
    parser.add_argument("--url", type=str, default=os.getenv("ENV_URL", "http://localhost:7860"))
    args = parser.parse_args()

    print(f"📊 Starting Greedy Throughput Agent for {args.task}...")
    
    with SatelliteEnv(base_url=args.url).sync() as env:
        obs = env.reset(task=args.task).observation
        
        step = 0
        while not obs.done:
            step += 1
            action = greedy_agent_step(obs)
            obs = env.step(action).observation
            
            if step % 20 == 0:
                print(f"Step {step}: Total Score Progress = {env.state().final_score:.4f}")

        state = env.state()
        print(f"\n✅ Mission Complete!")
        print(f"Final Score: {state.final_score:.4f}")


if __name__ == "__main__":
    main()
