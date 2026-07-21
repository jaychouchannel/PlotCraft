from __future__ import annotations

from typing import Any

from .base import Provider


class GeminiProvider(Provider):
    """Google Gemini API 适配器，使用 google-genai 库。"""

    async def generate(self, messages: list[dict[str, str]], temperature: float = 0.2, **kwargs: Any) -> str:
        from google import genai

        client = genai.Client(api_key=self.api_key)
        # 将 messages 转换为 Gemini 的 contents
        contents = []
        for msg in messages:
            role = msg["role"]
            text = msg["content"]
            if role == "system":
                # Gemini 没有原生 system message，放 user 前缀
                contents.append({"role": "user", "parts": [{"text": f"[System instruction]\n{text}"}]})
                # 加一个模型回复让对话平衡
                contents.append({"role": "model", "parts": [{"text": "OK"}]})
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": text}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": text}]})

        # 设置生成配置
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": 8192,
        }

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=generation_config,
            )
            return response.text
        except Exception as exc:
            raise RuntimeError(f"Gemini 调用失败: {exc}") from exc
