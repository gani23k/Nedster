import asyncio
import subprocess
import httpx
from skills.base import NedsterSkill

class DeployGitHubPages(NedsterSkill):
    name = "deploy_github_pages"
    description = "Commit, push, and confirm a GitHub Pages deployment via the Actions API (not CDN polling)."
    parameters = {
        "type": "object",
        "properties": {
            "repo_dir": {"type": "string"},
            "repo_slug": {"type": "string", "description": "owner/repo, e.g. unrealumanga/vfx-studio"},
            "commit_message": {"type": "string", "default": "Nedster autonomous update"},
        },
        "required": ["repo_dir", "repo_slug"],
    }

    async def run(self, repo_dir: str, repo_slug: str, commit_message: str = "Nedster autonomous update") -> dict:
        def _git(args: list) -> str:
            return subprocess.run(["git"] + args, cwd=repo_dir, capture_output=True, text=True, check=True).stdout.strip()

        try:
            await asyncio.to_thread(_git, ["add", "."])
            await asyncio.to_thread(_git, ["commit", "-m", commit_message])
            await asyncio.to_thread(_git, ["push", "origin", "main"])
        except subprocess.CalledProcessError as e:
            return {"status": "error", "stage": "git", "msg": e.stderr}

        # Poll the Actions run status API instead of hammering the live URL
        headers = {"Accept": "application/vnd.github+json"}
        url = f"https://api.github.com/repos/{repo_slug}/actions/runs?branch=main&per_page=1"
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            for _ in range(18):  # up to ~3 min
                resp = await client.get(url)
                runs = resp.json().get("workflow_runs", [])
                if runs and runs[0]["status"] == "completed":
                    success = runs[0]["conclusion"] == "success"
                    return {"status": "success" if success else "failed", "run_url": runs[0]["html_url"]}
                await asyncio.sleep(10)
        return {"status": "timeout", "msg": "Actions run did not complete within 3 minutes."}
