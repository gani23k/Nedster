# skills/persona_review.py
import asyncio
from dataclasses import dataclass
from skills.base import NedsterSkill

PERSONAS = {
    "security":    {"temp": 0.1, "prompt": "You ONLY flag security issues: injection, secrets, unsafe subprocess/eval. Output PASS or FLAG: <reason>."},
    "performance": {"temp": 0.2, "prompt": "You ONLY flag performance issues: O(n^2)+, N+1 queries, unbounded loops. Output PASS or FLAG: <reason>."},
    "docs":        {"temp": 0.3, "prompt": "You ONLY check whether docstrings/README match this diff. Output PASS or FLAG: <reason>."},
    "tests":       {"temp": 0.2, "prompt": "You ONLY check whether this diff has adequate test coverage. Output PASS or FLAG: <reason>."},
}

@dataclass
class Verdict:
    persona: str
    passed: bool
    reason: str

class PersonaRouter:
    def __init__(self, llm_call_fn):
        self.llm_call_fn = llm_call_fn  # async (prompt, system, temp) -> str

    async def _run_one(self, persona_name: str, diff_text: str) -> Verdict:
        cfg = PERSONAS[persona_name]
        raw = await self.llm_call_fn(diff_text, cfg["prompt"], cfg["temp"])
        passed = raw.strip().upper().startswith("PASS")
        reason = raw.split(":", 1)[1].strip() if ":" in raw else raw.strip()
        return Verdict(persona_name, passed, reason)

    async def review_all(self, diff_text: str) -> list[Verdict]:
        # All personas run concurrently — same hardware, no extra API cost
        return await asyncio.gather(*(self._run_one(p, diff_text) for p in PERSONAS))


class PersonaReviewDiff(NedsterSkill):
    name = "persona_review_diff"
    description = "Run the full specialist persona panel (security/performance/docs/tests) against a pending diff."
    parameters = {"type": "object", "properties": {"diff_text": {"type": "string"}}, "required": ["diff_text"]}

    def __init__(self, llm_call_fn=None):
        self.router = PersonaRouter(llm_call_fn)

    async def run(self, diff_text: str) -> dict:
        verdicts = await self.router.review_all(diff_text)
        flags = [v for v in verdicts if not v.passed]
        return {
            "all_passed": len(flags) == 0,
            "flags": [{"persona": v.persona, "reason": v.reason} for v in flags],
        }
