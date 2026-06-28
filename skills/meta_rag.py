# skills/meta_rag.py
import chromadb
from skills.base import NedsterSkill

class MetaPatternStore:
    def __init__(self, persist_dir: str = ".nedster/meta_rag"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection("meta_patterns")

    def record_pattern(self, problem_summary: str, resolution_summary: str, project_name: str):
        doc_id = f"{project_name}:{hash(problem_summary)}"
        self.collection.upsert(
            ids=[doc_id],
            documents=[f"PROBLEM: {problem_summary}\nRESOLUTION: {resolution_summary}"],
            metadatas=[{"source_project": project_name}],
        )

    def query_similar(self, current_problem: str, n_results: int = 3) -> list[dict]:
        results = self.collection.query(query_texts=[current_problem], n_results=n_results)
        return [
            {"text": doc, "source_project": meta["source_project"]}
            for doc, meta in zip(results["documents"][0], results["metadatas"][0])
        ]


class RecordCrossProjectPattern(NedsterSkill):
    name = "record_cross_project_pattern"
    description = "Save a confirmed bug-fix pattern into the global meta-RAG store, available to all future projects."
    parameters = {
        "type": "object",
        "properties": {
            "problem_summary": {"type": "string"}, "resolution_summary": {"type": "string"},
            "project_name": {"type": "string"},
        },
        "required": ["problem_summary", "resolution_summary", "project_name"],
    }

    def __init__(self):
        self.store = MetaPatternStore()

    async def run(self, problem_summary: str, resolution_summary: str, project_name: str) -> dict:
        self.store.record_pattern(problem_summary, resolution_summary, project_name)
        return {"status": "recorded"}


class QueryCrossProjectPatterns(NedsterSkill):
    name = "query_cross_project_patterns"
    description = "Search past fixes across ALL your projects for something similar to the current problem."
    parameters = {"type": "object", "properties": {"current_problem": {"type": "string"}}, "required": ["current_problem"]}

    def __init__(self):
        self.store = MetaPatternStore()

    async def run(self, current_problem: str) -> dict:
        return {"matches": self.store.query_similar(current_problem)}
