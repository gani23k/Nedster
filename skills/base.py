# skills/base.py — shared contract, referenced by every module below
from abc import ABC, abstractmethod
from typing import Any

class NedsterSkill(ABC):
    name: str
    description: str
    parameters: dict

    @abstractmethod
    async def run(self, **kwargs) -> Any: ...

    def to_tool_schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": self.parameters
        }}
