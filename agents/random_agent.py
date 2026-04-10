"""
Random Agent - Reference Baseline

Strategy: Randomly select a subset of valid current-tick windows to schedule.
Demonstrates the environment structure and provides an absolute baseline score.
"""

import argparse
import os
import random
from typing import List

from src.envs.satellite_env.client import SatelliteEnv
from src.envs.satellite_env.models import SatelliteAction, PassWindowModel


def random_agent_step(observation) -> SatelliteAction:
    """
    Selects 1-4 random windows from the current tick's opportunities.
    """
    # Filter for windows that occur in the current tick
    # The client/server might provide a broader window list for lookahead
    current_windows = [
        w for w in observation.pass_windows 
        if w.tick == (observation.current_time_min // 10)
    ]

    if not current_windows or random.random() < 0.2:
        return SatelliteAction(action_type="noop")

    # Sample a manageable number of schedules
    num_to_try = random.randint(1, min(5, len(current_windows)))
    sampled = random.sample(current_windows, num_to_try)

    schedules = []
    used_sats = set()
    used_stations = set()

    for w in sampled:
        # Constraint check: 1 sat per station, 1 station per sat
        if w.sat_id in used_sats or w.station_id in used_stations:
            continue
        
        # Availability check (Weather simulation)
        avail = observation.station_availability.get(str(w.station_id), 1.0)
        if avail < 0.1: # Skip offline stations
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

    print(f"🚀 Starting Random Agent for {args.task}...")
    
    with SatelliteEnv(base_url=args.url).sync() as env:
        obs = env.reset(task=args.task).observation
        
        step = 0
        while not obs.done:
            step += 1
            action = random_agent_step(obs)
            obs = env.step(action).observation
            
            if step % 20 == 0:
                print(f"Step {step}: Last Reward = {obs.reward:.4f}")

        state = env.state()
        print(f"\n✅ Mission Complete!")
        print(f"Final Score: {state.final_score:.4f}")
        print(f"Breakdown: {obs.reward_obj.breakdown}")


if __name__ == "__main__":
    main()
