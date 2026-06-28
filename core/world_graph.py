"""Minimal live project graph: imports, functions, git history. No claims beyond that."""
import ast
from pathlib import Path
from typing import Dict, List

class WorldGraph:
    def __init__(self, project_root: str):
        self.root = Path(project_root).resolve()
        self.nodes: Dict[str, Dict] = {}
        try:
            import git
            self.repo = git.Repo(self.root)
        except Exception:
            self.repo = None

    def update_file(self, rel_path: str):
        full = self.root / rel_path
        if not full.exists() or full.suffix != ".py":
            return
        try:
            tree = ast.parse(full.read_text())
        except SyntaxError:
            return  # don't crash the graph on a file mid-edit
        imports, functions = [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
        self.nodes[rel_path] = {"imports": imports, "functions": functions}

    def get_dependents(self, rel_path: str) -> List[str]:
        module_guess = rel_path.replace("/", ".").rstrip(".py")
        return [f for f, d in self.nodes.items() if module_guess in d.get("imports", [])]

    def get_history(self, rel_path: str, limit: int = 5) -> List[dict]:
        if not self.repo:
            return []
        return [{"hash": c.hexsha[:8], "message": c.message.strip()}
                 for c in self.repo.iter_commits(paths=rel_path, max_count=limit)]
