from abc import ABC, abstractmethod
import logging
from datetime import datetime, timezone
from typing import Any

from core.memory import memory_system

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    async def process(self, context: dict[str, Any]) -> dict[str, Any]: ...

    def get_trace(self) -> dict[str, Any]:
        return {"agent": self.name, "status": "ok", "duration_ms": 0}

    async def reflect(self, context: dict[str, Any]) -> dict[str, Any]:
        reflection = {
            "agent": self.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "observations": [],
            "decisions": [],
            "issues": [],
        }
        return reflection

    async def verify(self, result: dict[str, Any]) -> dict[str, Any]:
        return {"verified": True, "agent": self.name}

    def remember(self, key: str, value: str):
        try:
            memory_system.record_agent_memory(self.name, key, value)
        except Exception as e:
            logger.warning("Agent %s failed to remember %s: %s", self.name, key, e)

    def recall(self, key: str) -> str | None:
        try:
            return memory_system.get_agent_memory(self.name, key)
        except Exception as e:
            logger.warning("Agent %s failed to recall %s: %s", self.name, key, e)
            return None
