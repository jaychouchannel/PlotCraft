from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ProviderType = Literal["openai_compat", "gemini", "replicate"]


class ModelConfigIn(BaseModel):
    name: str
    provider: ProviderType
    base_url: str = ""
    model_name: str
    api_key: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class ModelConfigOut(BaseModel):
    id: int
    name: str
    provider: ProviderType
    base_url: str
    model_name: str
    api_key_masked: str
    extra: dict[str, Any] = Field(default_factory=dict)


class TemplateIn(BaseModel):
    name: str
    category: str = ""
    system_prompt: str = ""
    user_template: str = ""


class TemplateOut(BaseModel):
    id: int
    name: str
    category: str
    system_prompt: str
    user_template: str
    builtin: bool


class GenerateRequest(BaseModel):
    model_id: int
    template_id: int | None = None
    system_prompt: str | None = None
    user_prompt: str
    temperature: float = 0.2
    # 是否在生成代码后立即在后端沙箱执行渲染
    render: bool = True
    # 用户可附带的数据 / 参数（纯文本，会拼到 user_prompt 里）
    user_input: str = ""


class GenerateResponse(BaseModel):
    generated_code: str
    svg: str | None = None
    status: str  # success | code_only | error
    error: str = ""


class RenderRequest(BaseModel):
    code: str


class GenerationRecord(BaseModel):
    id: int
    model_id: int
    template_id: int | None
    user_input: str
    generated_code: str
    status: str
    error: str
    created_at: str
