from __future__ import annotations

import json
from typing import Any

from .base import Provider
from .openai_compat import OpenAICompatProvider


def make_provider(provider: str, model_name: str, api_key: str, base_url: str = "", extra: dict | None = None) -> Provider:
    """根据 provider 类型构造 Provider 实例。"""
    extra = extra or {}
    if provider == "openai_compat":
        return OpenAICompatProvider(model_name, api_key, base_url, extra)
    if provider == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider(model_name, api_key, base_url, extra)
    if provider == "replicate":
        # 预留：未来接入 Replicate / FAL 物理化位图生成模型
        raise NotImplementedError("replicate provider 接口已预留，首版未实现。")
    raise ValueError(f"未知 provider: {provider}")


def from_db_row(row) -> Provider:
    """从 SQLite row 构造带解密 key 的 Provider。"""
    from ..crypto import decrypt
    return make_provider(
        provider=row["provider"],
        model_name=row["model_name"],
        api_key=decrypt(row["api_key_enc"]),
        base_url=row["base_url"],
        extra=json.loads(row["extra"] or "{}"),
    )
