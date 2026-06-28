"""AFTER_WRITE hook that runs your EXISTING mutation tester and persona reviewer
before a change is considered done. No new review logic — just sequencing."""
from core.event_bus import EventBus

class CriticLoop:
    def __init__(self, mutation_tester, persona_router, max_fix_attempts: int = 2):
        self.mutation_tester = mutation_tester       # your skills/mutation_test.py MutationTestFile
        self.persona_router = persona_router         # your skills/persona_review.py PersonaRouter
        self.max_fix_attempts = max_fix_attempts
        EventBus.subscribe("AFTER_WRITE", self.on_after_write)

    async def on_after_write(self, payload: dict):
        file_path = payload["path"]
        diff_text = payload.get("diff", "")

        verdicts = await self.persona_router.review_all(diff_text)
        flags = [v for v in verdicts if not v.passed]
        if flags:
            await EventBus.emit("ON_ERROR", {"stage": "persona_review", "flags": flags})
            return {"status": "needs_fix", "flags": flags}

        if payload.get("test_command"):
            result = await self.mutation_tester.run(file_path, payload["test_command"])
            if result.get("survivors"):
                await EventBus.emit("ON_ERROR", {"stage": "mutation_test", "survivors": result["survivors"]})
                return {"status": "test_gap_detected", "result": result}

        await EventBus.emit("ON_SUCCESS", {"path": file_path})
        return {"status": "passed"}
