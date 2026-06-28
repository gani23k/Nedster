"""Global event bus. One source of truth, no duplicate-subscription bugs."""
from typing import Dict, List, Callable, Any
from collections import defaultdict
import asyncio

class EventBus:
    _subscribers: Dict[str, List[tuple[int, Callable]]] = defaultdict(list)
    _seen_callbacks: set = set()  # prevents the same plugin re-registering on reload

    @classmethod
    def subscribe(cls, event_type: str, callback: Callable, priority: int = 0):
        key = (event_type, id(callback.__func__) if hasattr(callback, "__func__") else id(callback))
        if key in cls._seen_callbacks:
            return  # already subscribed — avoids duplicate firing on plugin reload
        cls._seen_callbacks.add(key)
        cls._subscribers[event_type].append((priority, callback))
        cls._subscribers[event_type].sort(key=lambda x: -x[0])

    @classmethod
    async def emit(cls, event_type: str, payload: Any = None):
        for _, cb in cls._subscribers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(payload)
                else:
                    cb(payload)
            except Exception as e:
                # one bad subscriber must never break the agent loop
                print(f"[EventBus] subscriber error on {event_type}: {e}")

EVENTS = [
    "BEFORE_PROMPT", "AFTER_PROMPT", "BEFORE_TOOL", "AFTER_TOOL",
    "BEFORE_WRITE", "AFTER_WRITE", "BEFORE_COMMIT", "ON_ERROR", "ON_SUCCESS",
]
