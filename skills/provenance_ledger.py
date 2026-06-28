# skills/provenance_ledger.py
import hashlib, json, time
from pathlib import Path
from skills.base import NedsterSkill

GENESIS_HASH = "0" * 64

def _hash_entry(entry: dict) -> str:
    payload = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

class AppendLedgerEntry(NedsterSkill):
    name = "append_ledger_entry"
    description = "Append a tamper-evident record of an AI-made change to the provenance ledger."
    parameters = {
        "type": "object",
        "properties": {
            "ledger_path": {"type": "string"},
            "tool_name": {"type": "string"},
            "args_summary": {"type": "string"},
            "diff_hash": {"type": "string"},
            "job_id": {"type": "string"},
        },
        "required": ["ledger_path", "tool_name", "diff_hash"],
    }

    async def run(self, ledger_path: str, tool_name: str, diff_hash: str,
                  args_summary: str = "", job_id: str = "") -> dict:
        path = Path(ledger_path)
        prev_hash = GENESIS_HASH
        if path.exists() and path.stat().st_size > 0:
            with open(path, "rb") as f:
                f.seek(-2, 2)
                while f.read(1) != b"\n":
                    f.seek(-2, 1)
                last_line = f.readline().decode()
            prev_hash = json.loads(last_line)["hash"]

        entry = {
            "ts": time.time(), "tool_name": tool_name, "args_summary": args_summary,
            "diff_hash": diff_hash, "job_id": job_id, "prev_hash": prev_hash,
        }
        entry["hash"] = _hash_entry(entry)
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return {"status": "appended", "hash": entry["hash"]}


class VerifyLedgerChain(NedsterSkill):
    name = "verify_ledger_chain"
    description = "Walk the provenance ledger and confirm no entry has been tampered with."
    parameters = {"type": "object", "properties": {"ledger_path": {"type": "string"}}, "required": ["ledger_path"]}

    async def run(self, ledger_path: str) -> dict:
        expected_prev = GENESIS_HASH
        with open(ledger_path) as f:
            for i, line in enumerate(f):
                entry = json.loads(line)
                if entry["prev_hash"] != expected_prev:
                    return {"valid": False, "broken_at_line": i, "reason": "prev_hash mismatch"}
                recomputed = _hash_entry(entry)
                if recomputed != entry["hash"]:
                    return {"valid": False, "broken_at_line": i, "reason": "hash mismatch — entry was edited"}
                expected_prev = entry["hash"]
        return {"valid": True, "entries_checked": i + 1 if 'i' in dir() else 0}
