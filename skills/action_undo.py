# skills/action_undo.py
import difflib, json, time, hashlib
from pathlib import Path
from skills.base import NedsterSkill

SNAPSHOT_DIR = Path(".nedster/snapshots")

class SnapshotManager:
    def snapshot_before_write(self, job_id: str, step_n: int, file_path: str) -> str:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        content = Path(file_path).read_text() if Path(file_path).exists() else ""
        key = hashlib.sha1(f"{job_id}:{step_n}:{file_path}".encode()).hexdigest()
        snap_path = SNAPSHOT_DIR / f"{key}.snap"
        snap_path.write_text(json.dumps({
            "job_id": job_id, "step_n": step_n, "file_path": file_path,
            "content": content, "ts": time.time(),
        }))
        return str(snap_path)

    def rollback_to(self, job_id: str, target_step: int) -> list[str]:
        restored = []
        snaps = sorted(SNAPSHOT_DIR.glob("*.snap"), key=lambda p: json.loads(p.read_text())["ts"])
        for snap in reversed(snaps):
            data = json.loads(snap.read_text())
            if data["job_id"] == job_id and data["step_n"] >= target_step:
                Path(data["file_path"]).write_text(data["content"])
                restored.append(data["file_path"])
        return restored


class GhostDiff(NedsterSkill):
    name = "ghost_diff"
    description = "Compute the diff a write WOULD produce, without writing anything to disk."
    parameters = {
        "type": "object",
        "properties": {"file_path": {"type": "string"}, "new_content": {"type": "string"}},
        "required": ["file_path", "new_content"],
    }

    async def run(self, file_path: str, new_content: str) -> dict:
        old = Path(file_path).read_text() if Path(file_path).exists() else ""
        diff = "\n".join(difflib.unified_diff(
            old.splitlines(), new_content.splitlines(),
            fromfile=f"a/{file_path}", tofile=f"b/{file_path}", lineterm="",
        ))
        return {"diff": diff, "lines_added": diff.count("\n+"), "lines_removed": diff.count("\n-")}


class RollbackToStep(NedsterSkill):
    name = "rollback_to_step"
    description = "Restore all files to their state at or before a given step in a job, undoing later edits."
    parameters = {
        "type": "object",
        "properties": {"job_id": {"type": "string"}, "target_step": {"type": "integer"}},
        "required": ["job_id", "target_step"],
    }

    def __init__(self):
        self.manager = SnapshotManager()

    async def run(self, job_id: str, target_step: int) -> dict:
        restored = self.manager.rollback_to(job_id, target_step)
        return {"restored_files": restored, "rolled_back_to_step": target_step}
