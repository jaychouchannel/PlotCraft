from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from ..db import get_db
from ..executor import execute_code, render_to_format
from ..models import GenerateRequest, GenerateResponse, RenderRequest
from ..prompts import DEFAULT_SYSTEM_PROMPT
from ..providers.factory import make_provider
from ..providers.openai_compat import extract_code_block
from ..svg_sanitize import sanitize_svg

router = APIRouter(prefix="/api/generate", tags=["generate"])


class ClientDisconnected(Exception):
    """客户端断开连接，用于跳出主流程，避免继续往 DB 写历史。"""


async def _load_provider(model_id: int):
    from ..crypto import decrypt
    db = await get_db()
    cursor = await db.execute("SELECT * FROM model_configs WHERE id=?", (model_id,))
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(404, f"模型配置 id={model_id} 不存在")
    try:
        extra = json.loads(row["extra"] or "{}")
    except Exception:
        extra = {}
    return make_provider(
        provider=row["provider"],
        model_name=row["model_name"],
        api_key=decrypt(row["api_key_enc"]),
        base_url=row["base_url"],
        extra=extra,
    )


async def _load_template(template_id: int | None) -> tuple[str, str]:
    """返回 (system_prompt, user_template)，user_template 仅作参考拼装用。"""
    if template_id is None:
        return DEFAULT_SYSTEM_PROMPT, ""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM templates WHERE id=?", (template_id,))
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(404, f"模板 id={template_id} 不存在")
    sys_prompt = row["system_prompt"] or DEFAULT_SYSTEM_PROMPT
    user_template = row["user_template"] or ""
    return sys_prompt, user_template


@router.post("")
async def generate(body: GenerateRequest, request: Request) -> GenerateResponse:
    provider = await _load_provider(body.model_id)
    sys_prompt, user_template = await _load_template(body.template_id)
    if body.system_prompt:
        sys_prompt = body.system_prompt

    # 拼装 user prompt：模板（参考）+ 用户实际输入
    parts = []
    if user_template:
        parts.append(f"# 模板参考（如有占位符请替换）：\n{user_template}\n\n# 用户实际需求：")
    if body.user_prompt:
        parts.append(body.user_prompt)
    elif body.user_input:
        parts.append(body.user_input)
    else:
        parts.append("请根据模板生成一张科研论文风格的图。")
    if body.user_input and body.user_prompt:
        parts.append(f"\n# 附带数据 / 参数：\n{body.user_input}")
    user_prompt = "\n".join(parts)

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw = await provider.generate(messages, temperature=body.temperature)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        return GenerateResponse(generated_code="", status="error", error=f"LLM 调用失败: {exc}")

    if await request.is_disconnected():
        raise ClientDisconnected()

    code = extract_code_block(raw)
    if not code:
        return GenerateResponse(generated_code="", status="error", error="LLM 未返回有效代码块")

    svg = None
    status = "code_only"
    error = ""
    if body.render:
        # 沙箱执行期间客户端断开 → 不再写历史
        sandbox_task = asyncio.create_task(execute_code(code))
        disconnect_task = asyncio.create_task(request.is_disconnected())
        done, pending = await asyncio.wait(
            {sandbox_task, disconnect_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()
        if disconnect_task in done and disconnect_task.result():
            raise ClientDisconnected()
        if sandbox_task in done:
            svg, _path, err = sandbox_task.result()
        else:
            svg, _path, err = "", "", "执行被取消"
        if err:
            status = "error"
            error = err
        elif svg:
            status = "success"
        else:
            status = "error"
            error = "执行未返回 SVG"

    # 写入历史
    db = await get_db()
    history_input = body.user_prompt or body.user_input
    cursor = await db.execute(
        "INSERT INTO generations (model_id, template_id, user_input, generated_code, status, error) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (body.model_id, body.template_id, history_input, code, status, error),
    )
    gen_id = cursor.lastrowid
    if svg:
        await db.execute(
            "INSERT INTO generation_svgs (generation_id, svg_content) VALUES (?, ?)",
            (gen_id, svg),
        )
    await db.commit()

    return GenerateResponse(generated_code=code, svg=svg, status=status, error=error)


@router.post("/render")
async def render_only(body: RenderRequest) -> GenerateResponse:
    """接收已生成的代码，仅在沙箱执行渲染。前端「重新渲染」按钮调用。"""
    if not body.code:
        raise HTTPException(400, "code 不能为空")
    svg, _path, err = await execute_code(body.code)
    if err:
        return GenerateResponse(generated_code=body.code, status="error", error=err)
    return GenerateResponse(generated_code=body.code, svg=svg, status="success")


@router.post("/download")
async def download_format(body: RenderRequest, fmt: str = "png") -> Response:
    """把用户编辑后的代码渲染为指定格式二进制（png/pdf/svg）。

    前端通过 ?fmt=png 查询参数指定。svg 直接走渲染流水线，png/pdf 走 render_to_format。
    """
    if not body.code:
        raise HTTPException(400, "code 不能为空")
    fmt = (fmt or "png").lower()
    if fmt == "svg":
        svg, _path, err = await execute_code(body.code)
        if err:
            raise HTTPException(500, err)
        return Response(content=svg, media_type="image/svg+xml", headers={"Content-Disposition": 'attachment; filename="plot.svg"'})
    if fmt not in ("png", "pdf"):
        raise HTTPException(400, f"不支持的格式: {fmt}")
    data, err = await render_to_format(body.code, fmt)
    if err:
        raise HTTPException(500, err)
    media = "image/png" if fmt == "png" else "application/pdf"
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="plot.{fmt}"'},
    )
