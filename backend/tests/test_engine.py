from datetime import date, timedelta
import pytest
from core.engine import Task, TaskStatus, check_cycles, compute_schedule, CycleDetectedError

def test_cycle_detection():
    edges = [("A", "B"), ("B", "C")]
    
    # Adding C -> A should raise
    with pytest.raises(CycleDetectedError) as excinfo:
        check_cycles(edges, ("C", "A"))
    
    # Path should be from dependent (A) to prereq (C) and back to dependent (A)
    # The dfs starts at A, visits B, C. So path is ['A', 'B', 'C']
    assert set(excinfo.value.path).issuperset({"A", "B", "C"})
    
    # Adding A -> C is fine
    check_cycles(edges, ("A", "C"))

def test_self_dependency():
    with pytest.raises(CycleDetectedError):
        check_cycles([], ("A", "A"))

def test_diamond_convergence():
    base_date = date(2026, 1, 1)
    tasks = {
        "A": Task("A", TaskStatus.BACKLOG, 2, base_date, base_date, base_date, False),
        "B": Task("B", TaskStatus.BACKLOG, 2, base_date, base_date, base_date, False),
        "C": Task("C", TaskStatus.BACKLOG, 2, base_date, base_date, base_date, False),
        "D": Task("D", TaskStatus.BACKLOG, 2, base_date, base_date, base_date, False),
    }
    edges = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
    
    compute_schedule(tasks, edges)
    
    # A ends on 1/3
    # B and C start 1/3, end 1/5
    # D starts 1/5, ends 1/7
    assert tasks["D"].start_date == date(2026, 1, 5)
    assert tasks["D"].end_date == date(2026, 1, 7)
    
    # A slips by 3 days
    tasks["A"].planned_start = date(2026, 1, 4)
    compute_schedule(tasks, edges)
    
    # D should shift by 3 days, not 6
    assert tasks["D"].start_date == date(2026, 1, 8)
    assert tasks["D"].end_date == date(2026, 1, 10)

def test_rollback_status():
    base_date = date(2026, 1, 1)
    tasks = {
        "A": Task("A", TaskStatus.DONE, 2, base_date, base_date, base_date + timedelta(days=2), False),
        "B": Task("B", TaskStatus.BACKLOG, 2, base_date, base_date, base_date, False),
    }
    edges = [("A", "B")]
    
    compute_schedule(tasks, edges)
    assert tasks["B"].blocked == False
    
    # Rollback A
    tasks["A"].status = TaskStatus.IN_PROGRESS
    compute_schedule(tasks, edges)
    
    assert tasks["B"].blocked == True

def test_multi_level_propagation():
    base_date = date(2026, 1, 1)
    tasks = {
        "A": Task("A", TaskStatus.BACKLOG, 1, base_date, base_date, base_date, False),
        "B": Task("B", TaskStatus.BACKLOG, 1, base_date, base_date, base_date, False),
        "C": Task("C", TaskStatus.BACKLOG, 1, base_date, base_date, base_date, False),
        "D": Task("D", TaskStatus.BACKLOG, 1, base_date, base_date, base_date, False),
    }
    edges = [("A", "B"), ("B", "C"), ("C", "D")]
    compute_schedule(tasks, edges)
    
    assert tasks["D"].start_date == date(2026, 1, 4)
    assert tasks["D"].end_date == date(2026, 1, 5)
