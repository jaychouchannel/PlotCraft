from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..db import get_db
from ..models import TemplateIn, TemplateOut

router = APIRouter(prefix="/api/templates", tags=["templates"])

SEED_DIR = Path(__file__).resolve().parent.parent.parent / "templates_seed"


@router.get("")
async def list_templates() -> list[TemplateOut]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM templates ORDER BY builtin DESC, id ASC")
    rows = await cursor.fetchall()
    return [TemplateOut(
        id=r["id"],
        name=r["name"],
        category=r["category"],
        system_prompt=r["system_prompt"],
        user_template=r["user_template"],
        builtin=bool(r["builtin"]),
    ) for r in rows]


@router.get("/{template_id}")
async def get_template(template_id: int) -> TemplateOut:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM templates WHERE id=?", (template_id,))
    r = await cursor.fetchone()
    if r is None:
        raise HTTPException(404, "模板不存在")
    return TemplateOut(
        id=r["id"], name=r["name"], category=r["category"],
        system_prompt=r["system_prompt"], user_template=r["user_template"],
        builtin=bool(r["builtin"]),
    )


@router.post("", status_code=201)
async def create_template(body: TemplateIn) -> TemplateOut:
    db = await get_db()
    cur = await db.execute(
        "INSERT INTO templates (name, category, system_prompt, user_template, builtin) "
        "VALUES (?, ?, ?, ?, 0)",
        (body.name, body.category, body.system_prompt, body.user_template),
    )
    last_id = cur.lastrowid
    await db.commit()
    cursor = await db.execute("SELECT * FROM templates WHERE id=?", (last_id,))
    r = await cursor.fetchone()
    return TemplateOut(
        id=r["id"], name=r["name"], category=r["category"],
        system_prompt=r["system_prompt"], user_template=r["user_template"],
        builtin=bool(r["builtin"]),
    )


@router.put("/{template_id}")
async def update_template(template_id: int, body: TemplateIn) -> TemplateOut:
    db = await get_db()
    # 不允许直接修改 builtin 模板；如要修改，前端应复制为新模板
    cursor = await db.execute("SELECT builtin FROM templates WHERE id=?", (template_id,))
    r = await cursor.fetchone()
    if r is None:
        raise HTTPException(404, "模板不存在")
    if bool(r["builtin"]):
        raise HTTPException(400, "内置模板不可修改，请另存为新模板后再编辑")
    await db.execute(
        "UPDATE templates SET name=?, category=?, system_prompt=?, user_template=? WHERE id=?",
        (body.name, body.category, body.system_prompt, body.user_template, template_id),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM templates WHERE id=?", (template_id,))
    r = await cursor.fetchone()
    return TemplateOut(
        id=r["id"], name=r["name"], category=r["category"],
        system_prompt=r["system_prompt"], user_template=r["user_template"],
        builtin=bool(r["builtin"]),
    )


@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT builtin FROM templates WHERE id=?", (template_id,))
    r = await cursor.fetchone()
    if r is None:
        raise HTTPException(404, "模板不存在")
    if bool(r["builtin"]):
        raise HTTPException(400, "内置模板不可删除")
    await db.execute("DELETE FROM templates WHERE id=?", (template_id,))
    await db.commit()


async def seed_templates_if_empty() -> int:
    """启动时若 templates 表为空，从 templates_seed/*.json 加载内置模板。"""
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM templates WHERE builtin=1")
    cnt_row = await cursor.fetchone()
    if cnt_row[0] > 0:
        return 0
    if not SEED_DIR.exists():
        return 0
    n = 0
    for fp in sorted(SEED_DIR.glob("*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            await db.execute(
                "INSERT INTO templates (name, category, system_prompt, user_template, builtin) "
                "VALUES (?, ?, ?, ?, 1)",
                (data["name"], data.get("category", ""), data.get("system_prompt", ""), data["user_template"]),
            )
            n += 1
        except Exception as exc:
            print(f"[seed] 跳过 {fp.name}: {exc}")
    await db.commit()
    return n
