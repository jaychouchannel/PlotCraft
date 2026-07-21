from __future__ import annotations

from fastapi import APIRouter, HTTPException

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


@router.delete("/{generation_id}", status_code=204)
async def delete_history(generation_id: int):
    db = await get_db()
    await db.execute("DELETE FROM generations WHERE id=?", (generation_id,))
    await db.commit()


@router.delete("", status_code=204)
async def clear_history():
    db = await get_db()
    await db.execute("DELETE FROM generations")
    await db.commit()
