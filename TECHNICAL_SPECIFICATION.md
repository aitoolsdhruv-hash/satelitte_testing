# Technical Specification - Action & State Spaces

This document defines the interface for the **Satellite Downlink Scheduling** environment, including the schemas for observations (state) and actions.

---

## Observation Space (State)

The agent receives a `SatelliteObservation` Pydantic model at each step.

### High-Level Structure
```python
class SatelliteObservation(BaseModel):
    current_time_min: int            # [0, 1440]
    reward_obj: RewardModel          # Current reward + breakdown
    pass_windows: List[PassWindow]   # Available windows this episode
    station_availability: Dict       # Weather status per station
    satellite_buffer_bytes: Dict     # Data remaining per satellite
    data_priority_queues: Dict       # Chunks waiting per satellite
    downlink_rates_bps: Dict         # Hardware capacity
    current_schedule: List           # Active assignments
    done: bool                       # Episode terminal flag
    reward: float                    # Step reward
```

### Detailed Fields

#### 1. `pass_windows: List[PassWindowModel]`
This is the core of the state. It lists all scheduling opportunities available in the current episode.
- **Actionable**: Only windows where `tick == current_tick` can be scheduled in the current step.
- **Informational**: Future windows are provided to allow for lookahead/planning.
- **Fields**:
    - `window_id`: Unique identifier (e.g., `w_s3_g1_024`).
    - `sat_id`: Satellite [0-14].
    - `station_id`: Ground station [0-5].
    - `link_quality`: Weather-adjusted multiplier [0.0, 1.0].
    - `max_bytes`: Theoretical max transfer for this window.

#### 2. `data_priority_queues: Dict[str, List[DataChunkModel]]`
Lists the specific data chunks on each satellite.
- **Priority**: 1 (Routine), 2 (Important), 3 (Emergency).
- **Deadline**: `deadline_min` (Absolute time). If missed, Task 3 penalties apply.

#### 3. `station_availability: Dict[str, float]`
Dynamic weather status.
- `1.0`: Perfect clear sky.
- `0.0`: Complete outage (downlink impossible).

---

## Action Space

The agent must return a `SatelliteAction` object.

### Action Types
- **`schedule_multiple`**: The primary interaction. Assigns satellites to ground stations.
- **`noop`**: No operation. Skips the current tick (useful during bad weather or lack of windows).

### `schedule_multiple` Schema
```json
{
    "action_type": "schedule_multiple",
    "schedules": [
        {
            "sat_id": 3,
            "station_id": 1,
            "window_id": "w_s3_g1_024"
        }
    ]
}
```

### Operational Constraints
1. **Satellite Uniqueness**: A single satellite can only be assigned to **one** ground station per tick.
2. **Station Uniqueness**: A single ground station can only handle **one** satellite downlink per tick.
3. **Internal De-confliction**: If the agent submits conflicting assignments, the scheduler executes the **first** valid one and ignores the rest (silent conflict resolution).
4. **Temporal Consistency**: Agents can only schedule windows where `window.tick == current_tick`. Attempting to schedule future windows results in an error.

---

## State Vectorization Suggestion (for RL)

For neural network agents, we recommend flattening the observation into a fixed-size vector:
- **Global**: `[time_normalized, station_availabilities]` (7 values).
- **Per Satellite**: `[buffer_bytes, top_priority_in_queue, deadline_of_top]` (15 x 3 = 45 values).
- **Available Windows**: Top 10 windows sorted by link quality: `[window_fields]` (10 x 8 = 80 values).
- **Total Vector**: ~132-150 scalars.
