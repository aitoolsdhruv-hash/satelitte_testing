import pytest
from src.envs.satellite_env.server.graders import grade
from src.envs.satellite_env.server.scheduler import DownlinkResult, ActionResult
from src.envs.satellite_env.models import DataChunkModel

def test_task1_perfect_score():
    """Verify that downloading all available bytes results in a 1.0 (Task 1)."""
    # 100MB available
    total_avail = 100 * 1024 * 1024
    all_chunks = [{"chunk_id": "c1", "priority": 1, "size_bytes": total_avail, "injected_at_min": 0}]
    
    # 100MB downloaded
    log = [DownlinkResult(schedule_id="s1", sat_id=0, station_id=0, tick=1, 
                          bytes_downloaded=total_avail, chunks_downloaded=[], availability=1.0)]
    
    score = grade(task="task1", download_log=log, all_chunks=all_chunks, emergency_injections=[])
    assert score == pytest.approx(0.999, abs=0.001)

def test_priority_weighting_task2():
    """Verify that a Priority 3 chunk is worth 100x more than a Priority 1 chunk."""
    # Two scenarios: 1MB P1 vs 1MB P3
    chunk_size = 1024*1024
    all_chunks = [
        {"chunk_id": "p1", "priority": 1, "size_bytes": chunk_size, "injected_at_min": 0},
        {"chunk_id": "p3", "priority": 3, "size_bytes": chunk_size, "injected_at_min": 0}
    ]
    
    # Download 1MB of P1
    log_p1 = [DownlinkResult(schedule_id="s1", sat_id=0, station_id=0, tick=1, 
                             bytes_downloaded=chunk_size, 
                             chunks_downloaded=[{"chunk_id": "p1", "priority": 1, "bytes_taken": chunk_size}], 
                             availability=1.0)]
    score_p1 = grade(task="task2", download_log=log_p1, all_chunks=all_chunks, emergency_injections=[])
    
    # Download 1MB of P3
    log_p3 = [DownlinkResult(schedule_id="s2", sat_id=0, station_id=0, tick=1, 
                             bytes_downloaded=chunk_size, 
                             chunks_downloaded=[{"chunk_id": "p3", "priority": 3, "bytes_taken": chunk_size}], 
                             availability=1.0)]
    score_p3 = grade(task="task2", download_log=log_p3, all_chunks=all_chunks, emergency_injections=[])
    
    # P3 score should be significantly higher due to weighting (100 vs 1)
    assert score_p3 > score_p1

def test_emergency_penalty_task3():
    """Verify that late delivery in Task 3 reduces the score."""
    total_emerg = 1024 * 1024
    # Chunk with 60min deadline
    chunk = {"chunk_id": "e1", "priority": 3, "size_bytes": total_emerg, 
              "injected_at_min": 0, "deadline_min": 60}
    
    # Grader needs this to track deadlines
    injections = [{"tick": 0, "chunks": [chunk]}]
    
    # Scenario A: Downloaded at tick 2 (20 mins) -> ON TIME
    log_on_time = [DownlinkResult(schedule_id="s1", sat_id=0, station_id=0, tick=2, 
                                 bytes_downloaded=total_emerg, 
                                 chunks_downloaded=[{"chunk_id": "e1", "priority": 3, "bytes_taken": total_emerg}], 
                                 availability=1.0)]
    score_on_time = grade(task="task3", download_log=log_on_time, all_chunks=[chunk], emergency_injections=injections)

    # Scenario B: Downloaded at tick 10 (100 mins) -> LATE
    log_late = [DownlinkResult(schedule_id="s1", sat_id=0, station_id=0, tick=10, 
                              bytes_downloaded=total_emerg, 
                              chunks_downloaded=[{"chunk_id": "e1", "priority": 3, "bytes_taken": total_emerg}], 
                              availability=1.0)]
    score_late = grade(task="task3", download_log=log_late, all_chunks=[chunk], emergency_injections=injections)

    assert score_on_time > score_late
