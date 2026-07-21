from __future__ import annotations

import json
from typing import Any

import httpx

from ..safe_logging import redact
from .base import Provider


class OpenAICompatProvider(Provider):
    """OpenAI 兼容 chat completions 接口。覆盖：OpenAI / DeepSeek / GLM / 自定义 base_url。"""

    async def generate(self, messages: list[dict[str, str]], temperature: float = 0.2, **kwargs: Any) -> str:
        if not self.base_url:
            raise ValueError(
                "openai_compat provider 必须配置 base_url。常见值：\n"
                "  OpenAI:    https://api.openai.com/v1\n"
                "  DeepSeek:  https://api.deepseek.com\n"
                "  GLM:       https://open.bigmodel.cn/api/paas/v4\n"
                "  Moonshot:  https://api.moonshot.cn/v1"
            )
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            **self.extra,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                # 把 api_key 从响应文本中脱敏（部分服务会把 header 回显）
                body_text = redact(resp.text, self.api_key)
                raise RuntimeError(f"LLM 调用失败 {resp.status_code}: {body_text}")
            payload = resp.json()
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            payload_str = redact(str(payload), self.api_key)
            raise RuntimeError(f"无法解析 LLM 响应: {payload_str}") from exc


def extract_code_block(text: str) -> str:
    """从 LLM 响应中剥离 ```python``` 代码块，返回纯代码。"""
    if "```" not in text:
        return text.strip()
    parts = text.split("```")
    for i, part in enumerate(parts):
        stripped = part.strip()
        if not stripped:
            continue
        # 跳过开头的语言标识（python / ```python）
        if stripped.startswith(("python", "Python")):
            stripped = stripped[len("python"):].lstrip()
        # 取第一个非空代码块（通常是 2*i 奇数索引，但保险起见扫所有）
        if any(kw in stripped for kw in ("import ", "matplotlib", "plt.", "# ")):
            return stripped
    # 兜底：把所有 ``` 之间的内容拼起来
    code_segments = []
    for i, part in enumerate(parts):
        if i % 2 == 1 and part.strip():
            seg = part.strip()
            if seg.startswith(("python", "Python")):
                seg = seg.split("\n", 1)[-1] if "\n" in seg else ""
            code_segments.append(seg)
    return "\n".join(code_segments).strip() if code_segments else text.strip()
