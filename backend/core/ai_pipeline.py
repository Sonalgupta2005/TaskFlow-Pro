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

from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class DependencySuggestionItem(BaseModel):
    prerequisite_id: str = Field(description="The ID of the task that must be completed first")
    dependent_id: str = Field(description="The ID of the task that depends on the prerequisite")
    confidence: str = Field(description="Confidence level: High, Medium, or Low", pattern="^(High|Medium|Low)$")
    rationale: str = Field(description="A brief explanation of why this dependency exists")

def _call_llm_for_suggestions(prompt: str) -> List[Dict[str, Any]]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return []
        
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=list[DependencySuggestionItem],
            )
        )
        
        if response.text:
            return json.loads(response.text)
        return []
    except Exception as e:
        print(f"LLM Error: {e}")
        return []

def get_suggestions_for_draft(draft_title: str, draft_desc: str, draft_id: str, tasks: List[schemas.Task]) -> List[Dict[str, Any]]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # Fallback heuristic
        # return _heuristic_for_draft(draft_title, draft_desc, draft_id, tasks)
        return []
        
    prompt = f"""
    You are an expert technical project manager. A new task is being drafted.
    Draft Task ID: {draft_id}
    Draft Title: {draft_title}
    Draft Description: {draft_desc}
    
    Here are the existing tasks in the project:
    """
    for t in tasks:
        prompt += f"- [{t.id}] {t.title}: {t.description}\n"
        
    prompt += """
    Determine which of the existing tasks MUST be completed before this draft task can start (Draft is dependent),
    and which existing tasks CANNOT start until this draft task is completed (Draft is prerequisite).
    Return a JSON array of dependencies.
    """
    
    suggestions = _call_llm_for_suggestions(prompt)
    if not suggestions:
        # return _heuristic_for_draft(draft_title, draft_desc, draft_id, tasks)
        return []
    return suggestions

def get_suggestions(tasks: List[schemas.Task], edges: List[tuple]) -> List[Dict[str, Any]]:
    api_key = os.getenv("GEMINI_API_KEY")
    raw_suggestions = []
    
    if api_key:
        prompt = generate_llm_prompt(tasks)
        raw_suggestions = _call_llm_for_suggestions(prompt)
        # if not raw_suggestions:
        #     raw_suggestions = keyword_heuristic(tasks)
    else:
        # raw_suggestions = keyword_heuristic(tasks)
        pass
        
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

def _heuristic_for_draft(draft_title: str, draft_desc: str, draft_id: str, tasks: List[schemas.Task]) -> List[Dict[str, Any]]:
    suggestions = []
    title = draft_title.lower()
    desc = draft_desc.lower()
    
    if 'frontend' in title or 'frontend' in desc:
        for p in tasks:
            p_title = p.title.lower()
            if ('backend' in p_title or 'api' in p_title):
                suggestions.append({
                    "prerequisite_id": p.id,
                    "dependent_id": draft_id,
                    "confidence": "Medium",
                    "rationale": "Frontend tasks typically depend on backend or API definitions."
                })
    if 'test' in title:
        for p in tasks:
            p_title = p.title.lower()
            if 'implement' in p_title:
                suggestions.append({
                    "prerequisite_id": p.id,
                    "dependent_id": draft_id,
                    "confidence": "High",
                    "rationale": "Implementation should finish before testing begins."
                })
    if 'backend' in title or 'api' in title:
        for p in tasks:
            p_title = p.title.lower()
            if 'frontend' in p_title:
                suggestions.append({
                    "prerequisite_id": draft_id,
                    "dependent_id": p.id,
                    "confidence": "Medium",
                    "rationale": "Frontend tasks typically depend on backend or API definitions."
                })
    if 'implement' in title:
        for p in tasks:
            p_title = p.title.lower()
            if 'test' in p_title:
                suggestions.append({
                    "prerequisite_id": draft_id,
                    "dependent_id": p.id,
                    "confidence": "High",
                    "rationale": "Implementation should finish before testing begins."
                })
                
    return suggestions
