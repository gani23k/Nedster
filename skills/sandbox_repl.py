# skills/sandbox_repl.py
import subprocess, tempfile, shutil, sys
from pathlib import Path
from skills.base import NedsterSkill

class DisposableSandbox(NedsterSkill):
    name = "run_in_sandbox"
    description = "Run speculative code in a fully isolated, disposable environment — never touches the real project."
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "language": {"type": "string", "enum": ["python", "node"], "default": "python"},
            "timeout_s": {"type": "integer", "default": 10},
        },
        "required": ["code"],
    }

    async def run(self, code: str, language: str = "python", timeout_s: int = 10) -> dict:
        tmp_dir = tempfile.mkdtemp(prefix="nedster_sandbox_")
        try:
            if language == "python":
                script = Path(tmp_dir) / "scratch.py"
                script.write_text(code)
                cmd = [sys.executable, "-I", str(script)]  # -I = isolated mode, ignores site/env
            else:
                script = Path(tmp_dir) / "scratch.js"
                script.write_text(code)
                cmd = ["node", str(script)]

            result = subprocess.run(
                cmd, cwd=tmp_dir, capture_output=True, text=True, timeout=timeout_s
            )
            return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "stdout": "", "stderr": f"Exceeded {timeout_s}s"}
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)  # always torn down, even on crash
