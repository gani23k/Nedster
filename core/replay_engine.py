"""Stores successful task DAGs and SUGGESTS them — the planner LLM still decides."""
import json, time, hashlib
from pathlib import Path
from typing import List, Optional

REPLAY_DIR = Path(".nedster/replays")

class ReplayEngine:
    def store(self, user_input: str, steps: List[dict], outcome: str, metrics: dict):
        REPLAY_DIR.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha1(user_input.encode()).hexdigest()[:12]
        (REPLAY_DIR / f"{key}.json").write_text(json.dumps({
            "user_input": user_input, "steps": steps, "outcome": outcome,
            "metrics": metrics, "ts": time.time(),
        }))

    def suggest_for(self, new_request: str, similarity_fn) -> Optional[dict]:
        """Returns the closest past workflow as a SUGGESTION for the planner prompt —
        never executed directly. similarity_fn(a, b) -> float, e.g. embedding cosine sim."""
        best, best_score = None, 0.0
        for f in REPLAY_DIR.glob("*.json"):
            data = json.loads(f.read_text())
            score = similarity_fn(new_request, data["user_input"])
            if score > best_score:
                best, best_score = data, score
        if best and best_score > 0.75:
            return {"suggested_steps": best["steps"], "confidence": best_score, "from": best["user_input"]}
        return None
