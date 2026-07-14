from abc import ABC, abstractmethod
from typing import Any, Optional


class ConnectorError(Exception):
    """Raised when a connector operation fails."""


class ConnectorAuthError(ConnectorError):
    """Raised when authentication/credentials are missing or invalid."""


class SourceConnector(ABC):
    name: str = "base"
    connected: bool = False
    last_sync: Optional[str] = None
    error: Optional[str] = None

    @abstractmethod
    async def connect(self) -> bool: ...

    @abstractmethod
    async def fetch_tasks(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def normalize(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    @abstractmethod
    def get_status(self) -> dict[str, Any]: ...
