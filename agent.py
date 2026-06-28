import os
import re
import ollama
from typing import Optional
import inspect
import asyncio
import json

from context_loader import ContextLoader
from editor import FileEditor
from rag_engine.retriever import Retriever
from memory import MemoryManager
from tui import NedsterTUI

from core.event_bus import EventBus
from core.plugin_manager import PluginManager
from core.world_graph import WorldGraph
from core.indexer import IncrementalIndexer
from core.replay_engine import ReplayEngine
from core.critic_loop import CriticLoop

# --- The "Unchained" System Prompt ---
# Removed XML tool directives because we now use native structured tool calling
NEDSTER_SYSTEM_PROMPT = """
[IDENTITY DIRECTIVE]
You are Nedster, an UNCHAINED local AI software engineer. You are running natively on the user's machine. You HAVE full filesystem and shell access via the tools provided. Your persona is that of an elite, efficient, and direct principal engineer.

[EXECUTION DIRECTIVE]
Your primary function is to EXECUTE tasks, not discuss them.
- NO conversational filler. NO "Certainly!", "Of course!", "Here is...", "Hello!".
- When a task is complete, summarize the action in 1-2 sentences and STOP. Do not ask what to do next.

[REASONING DIRECTIVE]
Before acting, you MUST use a <think> block to reason about the plan, analyze the user's request, and determine which tools are necessary.
"""

def get_legacy_schema(func, name: str) -> dict:
    """Converts a standard Python function to an Ollama tool schema."""
    doc = inspect.getdoc(func) or "No description."
    sig = inspect.signature(func)
    
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        if param_name == "kwargs": continue
        
        param_type = "string"
        if param.annotation == int:
            param_type = "integer"
        elif param.annotation == bool:
            param_type = "boolean"
        elif param.annotation == float:
            param_type = "number"
            
        properties[param_name] = {"type": param_type}
        
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
            
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": doc.splitlines()[0] if doc else "No description",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }


class ToolExecutor:
    def __init__(
        self,
        registry: dict,
        auto: bool = False,
        session_log=None,
        project_path: str = None,
        job_id: int = None,
    ):
        self.registry = registry
        self.project_path = project_path
        self.job_id = job_id

    def execute(self, name: str, args: dict, tui=None) -> str:
        if name not in self.registry:
            return f"[ERROR: '{name}' unknown.]"

        if self.job_id and name in ["edit_file", "write_file"]:
            from swarm_utils import acquire_lock, release_lock
            if not acquire_lock(self.project_path, args.get("path"), self.job_id):
                return f"[ERROR] Could not acquire lock."
            try:
                return self._execute_tool(name, args)
            finally:
                release_lock(self.project_path, args.get("path"), self.job_id)

        return self._execute_tool(name, args)

    def _execute_tool(self, name: str, args: dict) -> str:
        try:
            tool = self.registry[name]
            # Check if it's an async NedsterSkill instance
            if hasattr(tool, "run") and asyncio.iscoroutinefunction(tool.run):
                try:
                    loop = asyncio.get_running_loop()
                    return str(loop.run_until_complete(tool.run(**args)))
                except RuntimeError:
                    return str(asyncio.run(tool.run(**args)))
            else:
                # It's a standard Python function (BASE_TOOL_REGISTRY)
                return str(tool(**args))
        except Exception as e:
            return f"[ERROR] {name} failed: {e}"


class NedsterAgent:
    def __init__(
        self,
        project_dir: str,
        auto: bool = False,
        think: bool = False,
        job_id: int = None,
        scoped_dirs: list = None,
        backend: str = "local"
    ):
        from tools import SESSION, TOOL_REGISTRY as BASE_TOOL_REGISTRY
        from skill_manager import TOOL_REGISTRY as SKILL_TOOL_REGISTRY
        from memory import SessionLog
        import sys

        SESSION.set_project(project_dir)
        SESSION.platform = "windows" if sys.platform == "win32" else "linux"

        self.project_dir = project_dir
        self.auto = auto
        self.think_visible = think
        self.job_id = job_id
        self.backend = backend
        self.model = os.environ.get("MODEL", "aria-local")
        self.tui = NedsterTUI()
        self.memory = MemoryManager(self.model)

        # Merge base tools and newly discovered skills
        self.tool_registry = {**BASE_TOOL_REGISTRY, **SKILL_TOOL_REGISTRY}
        self.executor = ToolExecutor(
            self.tool_registry, project_path=self.project_dir, job_id=self.job_id
        )

        # Initialize core RAG retriever
        try:
            self.rag = Retriever()
        except Exception:
            self.rag = None

        # Initialize event-driven system & plugin architectures
        self.plugin_manager = PluginManager()
        self.plugin_manager.discover()
        self.plugin_manager.wrap_existing_skills(self.tool_registry)

        self.world_graph = WorldGraph(self.project_dir)
        self.indexer = IncrementalIndexer(self.project_dir, self.world_graph, rag_engine=self.rag)
        self.indexer.start()

        self.replay_engine = ReplayEngine()
        
        mutation_tester = self.tool_registry.get("mutation_test_file")
        persona_skill = self.tool_registry.get("persona_review_diff")
        persona_router = getattr(persona_skill, "router", None) if persona_skill else None
        
        self.critic = CriticLoop(
            mutation_tester=mutation_tester,
            persona_router=persona_router,
        )

    def _sync_emit(self, event_type: str, payload=None):
        """Helper to safely emit async events from synchronous context."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(EventBus.emit(event_type, payload))
            else:
                loop.run_until_complete(EventBus.emit(event_type, payload))
        except RuntimeError:
            asyncio.run(EventBus.emit(event_type, payload))

    def _get_native_tools(self) -> list:
        """Builds a JSON schema list of tools natively supported by Ollama."""
        tools = []
        for name, tool in self.tool_registry.items():
            if hasattr(tool, "to_tool_schema"):
                # It's a NedsterSkill object
                tools.append(tool.to_tool_schema())
            else:
                # It's a legacy Python function
                tools.append(get_legacy_schema(tool, name))
        return tools

    def generate(self, user_input: str):
        self.tui.print_thinking("Thinking...")
        self._sync_emit("BEFORE_PROMPT", {"user_input": user_input})

        # Advisory Replay Check: Suggest steps from similar successful past tasks if confidence > 0.75
        suggested_prompt_addition = ""
        try:
            def jaccard_similarity(a, b):
                words_a = set(a.lower().split())
                words_b = set(b.lower().split())
                intersection = words_a.intersection(words_b)
                union = words_a.union(words_b)
                return len(intersection) / len(union) if union else 0.0

            suggestion = self.replay_engine.suggest_for(user_input, jaccard_similarity)
            if suggestion:
                suggested_prompt_addition = (
                    f"\n\n[ADVISORY WORKFLOW SUGGESTION]\n"
                    f"A highly similar past task was completed successfully. Feel free to adapt or reuse these steps:\n"
                    f"Original Task: {suggestion['from']}\n"
                    f"Suggested Steps:\n{json.dumps(suggestion['suggested_steps'], indent=2)}\n"
                    f"Confidence Score: {suggestion['confidence']:.2f}"
                )
        except Exception as e:
            print(f"[ReplayEngine] suggestion lookup failed: {e}")

        prompt_with_replays = user_input + suggested_prompt_addition

        messages = [{"role": "system", "content": NEDSTER_SYSTEM_PROMPT}]
        messages.extend(self.memory.get_context_messages())
        messages.append({"role": "user", "content": prompt_with_replays})
        
        native_tools = self._get_native_tools()

        try:
            if self.backend == "local":
                client = ollama.Client(host="127.0.0.1")
                response = client.chat(
                    model=self.model, 
                    messages=messages, 
                    stream=False,
                    tools=native_tools
                )
            else:
                from nedster_api import LiteLLMNedsterBridge
                bridge = LiteLLMNedsterBridge()
                if self.model != os.environ.get("MODEL", "aria-local"):
                    bridge.set_model(self.model)
                response = bridge.generate(messages=messages, tools=native_tools)

            message = response.get("message", {})
            full_response = message.get("content", "")

            # Handle <think> blocks
            if full_response:
                think_match = re.search(r"<think>(.*?)</think>", full_response, re.DOTALL)
                if think_match:
                    if self.think_visible:
                        self.tui.print_thinking(think_match.group(1).strip())
                    full_response = full_response[think_match.end():].strip()

                if full_response.strip():
                    self.tui.print_response(full_response)

            # Handle native tool calls
            tool_calls = message.get("tool_calls", [])
            
            # Legacy fallback: occasionally an LLM might still output XML despite native tools
            if "<tool name=" in full_response and not tool_calls:
                from tools import parse_tool_calls
                parsed_xml = parse_tool_calls(full_response)
                for xml_call in parsed_xml:
                    tool_calls.append({
                        "function": {
                            "name": xml_call["name"],
                            "arguments": xml_call["args"]
                        }
                    })

            if tool_calls:
                import json
                tool_messages = []  # one role:"tool" message per call, matched by id

                for i, call in enumerate(tool_calls):
                    name = call["function"]["name"]
                    args_raw = call["function"]["arguments"]

                    if isinstance(args_raw, str):
                        try:
                            args = json.loads(args_raw)
                        except json.JSONDecodeError:
                            args = {}
                    else:
                        args = args_raw

                    # Ensure every call has a unique id — legacy XML-parsed calls
                    # don't carry one, so synthesize a stable per-turn id.
                    call_id = call.get("id") or f"call_{i}"
                    call["id"] = call_id

                    self.tui.print_tool_call(name, args)
                    
                    self._sync_emit("BEFORE_TOOL", {"name": name, "args": args})
                    result = self.executor.execute(name, args)
                    self._sync_emit("AFTER_TOOL", {"name": name, "result": result})

                    # If writing a file, emit AFTER_WRITE
                    if name in ["write_file", "edit_file"]:
                        self._sync_emit("AFTER_WRITE", {
                            "path": args.get("path"),
                            "diff": result
                        })

                    self.tui.print_tool_result(name, result)

                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": str(result),
                    })

                verification_prompt = (
                    "The above tools have completed executing. Synthesize the raw output into a clear, direct answer "
                    "to my original request. If the tool output contains the requested data (like file paths, code, or search results), "
                    "present them to me clearly. Do NOT just say 'the command succeeded'."
                )

                messages.append(message)        # 1. assistant turn with tool_calls
                messages.extend(tool_messages)  # 2. one tool message per tool_call_id — REQUIRED before any other role
                messages.append({"role": "user", "content": verification_prompt})  # 3. then the synthesis nudge

                self.tui.print_thinking("Synthesizing results...")
                if self.backend == "local":
                    summary_response = client.chat(
                        model=self.model, messages=messages, stream=False
                    )
                else:
                    summary_response = bridge.generate(messages=messages)

                summary_text = summary_response["message"]["content"]

                self.tui.print_response(summary_text)
                full_response = summary_text

                # Store successful workflow execution path for advisory replay engine
                try:
                    steps = []
                    for call in tool_calls:
                        steps.append({
                            "tool": call["function"]["name"],
                            "args": call["function"]["arguments"]
                        })
                    self.replay_engine.store(
                        user_input=user_input,
                        steps=steps,
                        outcome="success",
                        metrics={"loops": len(tool_calls), "ts": asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0}
                    )
                except Exception:
                    pass

            self.memory.add_turn(user_input, full_response)
            self._sync_emit("AFTER_PROMPT", {"user_input": user_input, "response": full_response})

        except Exception as e:
            self.tui.print_error(f"An error occurred in the agent loop: {e}")
            self._sync_emit("ON_ERROR", {"error": str(e)})
