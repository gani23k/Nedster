"""Loads event-driven plugins from plugins/, AND wraps existing skills/
NedsterSkill instances so they're event-subscribable without rewriting them."""
import json, importlib, sys
from pathlib import Path
from typing import Dict, Any
from core.event_bus import EventBus

class PluginManager:
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins: Dict[str, Any] = {}

    def discover(self):
        """Load new-style plugins/*/plugin.json + hooks.py."""
        if not self.plugins_dir.exists():
            return
        for pkg_dir in self.plugins_dir.iterdir():
            manifest = pkg_dir / "plugin.json"
            hooks_path = pkg_dir / "hooks.py"
            if not (pkg_dir.is_dir() and manifest.exists() and hooks_path.exists()):
                continue
            name = json.loads(manifest.read_text()).get("name", pkg_dir.name)
            sys.path.insert(0, str(pkg_dir.parent))
            try:
                mod = importlib.import_module(f"{pkg_dir.name}.hooks")
                if hasattr(mod, "Plugin"):
                    instance = mod.Plugin()
                    self.plugins[name] = instance
                    for attr in dir(instance):
                        if attr.startswith("on_"):
                            EventBus.subscribe(attr[3:].upper(), getattr(instance, attr))
            except Exception as e:
                print(f"[PluginManager] failed loading {name}: {e}")
            finally:
                sys.path.pop(0)

    def wrap_existing_skills(self, skill_registry: dict):
        """Existing NedsterSkill instances (mutation_test, persona_review, ledger, etc.)
        keep working exactly as before AND get an AFTER_TOOL hook for free —
        no rewrite required."""
        async def log_skill_use(payload):
            if payload["name"] in skill_registry:
                print(f"[Skill] {payload['name']} ran via legacy registry, result logged.")
        EventBus.subscribe("AFTER_TOOL", log_skill_use)
