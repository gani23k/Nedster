"""Watch the project, update World Graph + RAG only for the changed file."""
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

class IncrementalIndexer(FileSystemEventHandler):
    def __init__(self, project_root: str, world_graph, rag_engine=None):
        self.root = Path(project_root)
        self.world_graph = world_graph
        self.rag_engine = rag_engine
        self.observer = Observer()

    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith(".py"):
            return
        rel = str(Path(event.src_path).relative_to(self.root))
        self.world_graph.update_file(rel)
        if self.rag_engine:
            self.rag_engine.reembed_file(rel)  # your existing rag_engine, one file only

    def start(self):
        self.observer.schedule(self, str(self.root), recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
