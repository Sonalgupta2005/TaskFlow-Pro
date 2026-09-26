import os
import json
from typing import List, Dict, Any
from core import schemas, engine

def generate_llm_prompt(tasks: List[schemas.Task]) -> str:
    prompt = "Given the following tasks, suggest plausible Finish-to-Start dependencies.\n"
    prompt += "Respond ONLY with a JSON array of objects with keys: prerequisite_id, dependent_id, confidence (High/Medium/Low), rationale.\n\nTasks:\n"
    for t in tasks:
        prompt += f"- [{t.id}] {t.title}: {t.description}\n"
    return prompt

def keyword_heuristic(tasks: List[schemas.Task]) -> List[Dict[str, Any]]:
    suggestions = []
    for t in tasks:
        title = t.title.lower()
        desc = t.description.lower()
        
        # Example heuristic: if a task is about 'frontend', it might depend on 'backend' or 'api'
        if 'frontend' in title or 'frontend' in desc:
            for p in tasks:
                p_title = p.title.lower()
                if ('backend' in p_title or 'api' in p_title) and p.id != t.id:
                    suggestions.append({
                        "prerequisite_id": p.id,
                        "dependent_id": t.id,
                        "confidence": "Medium",
                        "rationale": "Frontend tasks typically depend on backend or API definitions being completed first."
                    })
                    
        # Testing heuristic
        if 'test' in title:
            for p in tasks:
                p_title = p.title.lower()
                if 'implement' in p_title and p.id != t.id:
                    suggestions.append({
                        "prerequisite_id": p.id,
                        "dependent_id": t.id,
                        "confidence": "High",
                        "rationale": "Implementation should finish before testing begins."
                    })
    return suggestions

def get_suggestions(tasks: List[schemas.Task], edges: List[tuple]) -> List[Dict[str, Any]]:
    api_key = os.getenv("LLM_API_KEY")
    raw_suggestions = []
    
    if api_key:
        try:
            # Here we would call the LLM API using google-genai or similar.
            # For demonstration, we fall back to the heuristic if the key is invalid or request fails.
            raw_suggestions = keyword_heuristic(tasks)
        except Exception:
            raw_suggestions = keyword_heuristic(tasks)
    else:
        raw_suggestions = keyword_heuristic(tasks)
        
    # Guardrails: validate IDs, remove duplicates, check cycles
    valid = []
    seen = set()
    task_ids = {t.id for t in tasks}
    
    for s in raw_suggestions:
        p = s.get("prerequisite_id")
        d = s.get("dependent_id")
        
        if not p or not d or p not in task_ids or d not in task_ids:
            continue
        if p == d:
            continue
            
        edge = (p, d)
        if edge in edges or edge in seen:
            continue
            
        try:
            engine.check_cycles(edges, edge)
            valid.append(s)
            seen.add(edge)
        except engine.CycleDetectedError:
            continue
            
    return valid
