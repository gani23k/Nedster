# skills/counterfactual_replay.py
import json, difflib
from pathlib import Path
from skills.base import NedsterSkill

class CounterfactualReplay(NedsterSkill):
    name = "counterfactual_replay"
    description = "Fork a past job at a given step and re-run with a different instruction, then diff outcomes."
    parameters = {
        "type": "object",
        "properties": {
            "journal_path": {"type": "string"},
            "job_id": {"type": "string"},
            "fork_step": {"type": "integer"},
            "alternate_instruction": {"type": "string"},
        },
        "required": ["journal_path", "job_id", "fork_step", "alternate_instruction"],
    }

    def __init__(self, agent_runner_fn=None):
        self.agent_runner_fn = agent_runner_fn  # async (messages, new_input) -> response

    def _load_trace_up_to(self, journal_path: str, job_id: str, fork_step: int) -> list[dict]:
        messages = []
        with open(journal_path) as f:
            for line in f:
                entry = json.loads(line)
                if entry["job_id"] != job_id or entry["step_n"] > fork_step:
                    continue
                messages.append({"role": "user", "content": entry["user_input"]})
                messages.append({"role": "assistant", "content": entry["agent_response"]})
        return messages

    async def run(self, journal_path: str, job_id: str, fork_step: int, alternate_instruction: str) -> dict:
        history_up_to_fork = self._load_trace_up_to(journal_path, job_id, fork_step)
        original_outcome = self._load_trace_up_to(journal_path, job_id, fork_step + 1)
        original_response = original_outcome[-1]["content"] if original_outcome else ""

        new_response = await self.agent_runner_fn(history_up_to_fork, alternate_instruction)

        diff = "\n".join(difflib.unified_diff(
            original_response.splitlines(), new_response.splitlines(),
            fromfile="original_path", tofile="counterfactual_path", lineterm="",
        ))
        return {"original": original_response, "counterfactual": new_response, "diff": diff}
