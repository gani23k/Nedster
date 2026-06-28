import os
import litellm
from typing import Dict, Any, List

class LiteLLMNedsterBridge:
    def __init__(self):
        """
        Unified routing engine for Nedster via LiteLLM.
        Reads NEDSTER_API_MODEL from environment, falling back to gemini-3.1-pro.
        """
        try:
            import dotenv
            dotenv.load_dotenv(".env")
        except ImportError:
            pass

        litellm.drop_params = True
        
        self.default_model = os.getenv("NEDSTER_API_MODEL", "gemini/gemini-3.1-pro-preview")
        self.models = {
            "reasoning": self.default_model,
            "execution": os.getenv("NEDSTER_EXECUTION_MODEL", "gemini/gemini-2.5-flash")
        }
        
    def set_model(self, model_name: str):
        """Allows switching the model at runtime."""
        self.default_model = model_name
        self.models["reasoning"] = model_name
        
    def generate(self, messages: List[Dict[str, str]], tools: List[Dict] = None) -> Dict:
        """
        Executes a unified completion call via LiteLLM, matching the exact dictionary 
        structure expected by Nedster's agent loop (which natively mimics Ollama/OpenAI).
        """
        try:
            kwargs = {
                "model": self.default_model,
                "messages": messages
            }
            if tools:
                kwargs["tools"] = tools

            response = litellm.completion(**kwargs)
            message_obj = response.choices[0].message
            
            # Convert LiteLLM object to dict for the agent loop
            result_message = {
                "role": message_obj.role,
                "content": message_obj.content or ""
            }
            
            if hasattr(message_obj, "tool_calls") and message_obj.tool_calls:
                result_message["tool_calls"] = []
                for tc in message_obj.tool_calls:
                    # Keep the raw argument format for history safety
                    args_raw = tc.function.arguments
                    
                    # Convert to string if it happens to be a dict (to appease LiteLLM history)
                    import json
                    if isinstance(args_raw, dict):
                        args_str = json.dumps(args_raw)
                    else:
                        args_str = args_raw

                    result_message["tool_calls"].append({
                        "id": getattr(tc, "id", None) or "call_unknown",
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": args_str
                        }
                    })
                    
            return {"message": result_message}
            
        except Exception as e:
            return {"message": {"role": "assistant", "content": f"CRITICAL: LiteLLM Routing Error with {self.default_model}. Details: {str(e)}"}}
