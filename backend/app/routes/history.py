from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..db import get_db
from ..models import GenerationRecord

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
async def list_history(limit: int = 50) -> list[GenerationRecord]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT id, model_id, template_id, user_input, generated_code, status, error, created_at "
        "FROM generations ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [GenerationRecord(
        id=r["id"], model_id=r["model_id"], template_id=r["template_id"],
        user_input=r["user_input"], generated_code=r["generated_code"],
        status=r["status"], error=r["error"], created_at=r["created_at"],
    ) for r in rows]


@router.get("/{generation_id}/svg")
async def get_generation_svg(generation_id: int) -> dict:
    db = await get_db()
    cursor = await db.execute(
        "SELECT svg_content FROM generation_svgs WHERE generation_id=? ORDER BY id DESC LIMIT 1",
        (generation_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(404, "SVG 不存在")
    return {"svg": row["svg_content"]}


@router.delete("/{generation_id}", status_code=204)
async def delete_history(generation_id: int):
    db = await get_db()
    await db.execute("DELETE FROM generations WHERE id=?", (generation_id,))
    await db.commit()


@router.delete("", status_code=204)
async def clear_history(older_than: str | None = None):
    """清空历史记录。若指定 older_than（ISO 日期字符串），仅删除该时间之前的记录。"""
    db = await get_db()
    if older_than:
        await db.execute("DELETE FROM generations WHERE created_at < ?", (older_than,))
    else:
        await db.execute("DELETE FROM generations")
    await db.commit()
    await db.execute("VACUUM")
    await db.commit()
