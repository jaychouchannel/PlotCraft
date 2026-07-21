from __future__ import annotations

import re


def redact(text: str, key: str, placeholder: str = "***") -> str:
    """替换字符串中所有出现的 key，避免 API key 泄露到日志或错误信息。"""
    if not key or len(key) < 4:
        return text
    return re.sub(re.escape(key), placeholder, text)
