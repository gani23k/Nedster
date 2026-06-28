import os
import sys
import importlib
import pkgutil
from pathlib import Path

SKILLS_DIR = Path(__file__).parent / "skills"
TOOL_REGISTRY = {}

def discover_skills(package="skills") -> dict:
    registry = {}
    if not SKILLS_DIR.exists():
        return registry

    # Temporarily add the project root to sys.path so we can import 'skills'
    proj_root = str(SKILLS_DIR.parent)
    if proj_root not in sys.path:
        sys.path.insert(0, proj_root)
        
    try:
        pkg = importlib.import_module(package)
    except ModuleNotFoundError:
        print(f"Could not load module {package}")
        return registry

    # We iterate through every file in the skills directory
    for _, modname, _ in pkgutil.iter_modules(pkg.__path__):
        try:
            mod = importlib.import_module(f"{package}.{modname}")
            # Look for classes that inherit from NedsterSkill
            from skills.base import NedsterSkill
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, NedsterSkill) and attr is not NedsterSkill:
                    instance = attr()
                    registry[instance.name] = instance
        except Exception as e:
            print(f"[Skills] Error loading skill module {modname}: {e}")

    return registry

def load_skills():
    global TOOL_REGISTRY
    skills = discover_skills()
    for name, skill_instance in skills.items():
        TOOL_REGISTRY[name] = skill_instance
        print(f"[Skills] Registered tool: {name}")

load_skills()
