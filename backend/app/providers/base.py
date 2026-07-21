from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Provider(ABC):
    """统一的 LLM Provider 接口。"""

    def __init__(self, model_name: str, api_key: str, base_url: str = "", extra: dict[str, Any] | None = None):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.extra = extra or {}

    @abstractmethod
    async def generate(self, messages: list[dict[str, str]], temperature: float = 0.2, **kwargs) -> str:
        """发送 messages 并返回文本响应。"""
        ...
