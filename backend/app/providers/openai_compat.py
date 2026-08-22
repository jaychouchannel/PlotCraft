from __future__ import annotations

import json
import re
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


_LANG_TAG_LINE_RE = re.compile(r"^\s*python\d*\s*$", re.IGNORECASE)


def extract_code_block(text: str) -> str:
    """从 LLM 响应中剥离 ```python``` 代码块，返回纯代码。"""
    text = text.strip()
    if "```" not in text:
        return text
    parts = text.split("```")
    # 只有奇数段（围栏之间）才是代码；偶数段是围栏外的散文，
    # 旧实现连散文一起扫描，会把「本方案使用 matplotlib...」当成代码返回。
    fenced = parts[1::2]
    cleaned: list[str] = []
    for part in fenced:
        stripped = part.strip()
        if not stripped:
            continue
        first, _, rest = stripped.partition("\n")
        if _LANG_TAG_LINE_RE.match(first):
            # 语言标识整行丢弃。不能按固定长度截断前缀——```python3 的
            # "3" 会残留在代码首行造成 SyntaxError。
            stripped = rest.strip()
            if not stripped:
                continue
        cleaned.append(stripped)
    # 优先返回首个像代码的段（沿用原关键词启发式），否则把围栏内容全部拼接
    for seg in cleaned:
        if any(kw in seg for kw in ("import ", "matplotlib", "plt.", "# ")):
            return seg
    return "\n".join(cleaned) or text
