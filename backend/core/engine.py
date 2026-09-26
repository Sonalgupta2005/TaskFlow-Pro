from datetime import date, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"

@dataclass
class Task:
    id: str
    status: TaskStatus
    duration_days: int
    planned_start: date
    start_date: date
    end_date: date
    blocked: bool
    is_critical: bool = False

class CycleDetectedError(Exception):
    def __init__(self, path: List[str]):
        self.path = path
        super().__init__(f"Dependency cycle detected: {' -> '.join(path)}")

def check_cycles(edges: List[Tuple[str, str]], new_edge: Tuple[str, str]) -> None:
    """
    Raises CycleDetectedError if adding new_edge (prerequisite -> dependent) 
    would create a cycle.
    """
    prereq, dependent = new_edge
    
    if prereq == dependent:
        raise CycleDetectedError([prereq, prereq])
    
    # Build adjacency list
    adj: Dict[str, List[str]] = {}
    for p, d in edges:
        adj.setdefault(p, []).append(d)
        
    visited = set()
    path = []
    
    def dfs(node: str) -> bool:
        if node == prereq:
            path.append(node)
            return True
        if node in visited:
            return False
        visited.add(node)
        path.append(node)
        for neighbor in adj.get(node, []):
            if dfs(neighbor):
                return True
        path.pop()
        return False
        
    if dfs(dependent):
        raise CycleDetectedError(path)

def topological_sort(tasks: Dict[str, Task], edges: List[Tuple[str, str]]) -> List[str]:
    in_degree = {t_id: 0 for t_id in tasks}
    adj = {t_id: [] for t_id in tasks}
    
    for p, d in edges:
        if p in tasks and d in tasks:
            adj[p].append(d)
            in_degree[d] += 1
            
    queue = [t_id for t_id, deg in in_degree.items() if deg == 0]
    sorted_nodes = []
    
    while queue:
        node = queue.pop(0)
        sorted_nodes.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
                
    if len(sorted_nodes) != len(tasks):
        raise ValueError("Graph contains a cycle")
        
    return sorted_nodes

def compute_schedule(tasks: Dict[str, Task], edges: List[Tuple[str, str]]) -> None:
    """
    Computes start_date, end_date, and blocked status for all tasks.
    Mutates the tasks dictionary in place.
    """
    prereqs_map: Dict[str, List[str]] = {t_id: [] for t_id in tasks}
    for p, d in edges:
        if p in tasks and d in tasks:
            prereqs_map[d].append(p)
            
    sorted_nodes = topological_sort(tasks, edges)
    
    for node_id in sorted_nodes:
        task = tasks[node_id]
        
        is_blocked = False
        max_prereq_end = None
        
        for p_id in prereqs_map[node_id]:
            p_task = tasks[p_id]
            if p_task.status != TaskStatus.DONE:
                is_blocked = True
            
            if max_prereq_end is None or p_task.end_date > max_prereq_end:
                max_prereq_end = p_task.end_date
                
        task.blocked = is_blocked
        
        if task.status == TaskStatus.DONE:
            continue
        
        if max_prereq_end is not None:
            task.start_date = max(task.planned_start, max_prereq_end)
        else:
            task.start_date = task.planned_start
            
        task.end_date = task.start_date + timedelta(days=task.duration_days)

    # Compute Critical Path (Backward Pass)
    # late_finish = min of late_start of all successors
    # late_start = late_finish - duration
    
    # We need successors_map
    succs_map: Dict[str, List[str]] = {t_id: [] for t_id in tasks}
    for p, d in edges:
        if p in tasks and d in tasks:
            succs_map[p].append(d)
            
    # Max end_date in the whole project
    project_end = max((t.end_date for t in tasks.values()), default=None)
    if not project_end:
        return
        
    late_finish: Dict[str, date] = {}
    late_start: Dict[str, date] = {}
    
    for node_id in reversed(sorted_nodes):
        task = tasks[node_id]
        if not succs_map[node_id]:
            late_finish[node_id] = project_end
        else:
            late_finish[node_id] = min(late_start[s] for s in succs_map[node_id])
            
        late_start[node_id] = late_finish[node_id] - timedelta(days=task.duration_days)
        
        slack = (late_finish[node_id] - task.end_date).days
        task.is_critical = (slack == 0)
