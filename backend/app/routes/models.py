from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from ..crypto import decrypt, encrypt, mask
from ..db import get_db
from ..models import ModelConfigIn, ModelConfigOut, ProviderType

router = APIRouter(prefix="/api/models", tags=["models"])


async def _row_to_out(r) -> ModelConfigOut:
    extra_dict: dict[str, Any] = {}
    try:
        extra_dict = json.loads(r["extra"] or "{}")
    except Exception:
        extra_dict = {}
    return ModelConfigOut(
        id=r["id"],
        name=r["name"],
        provider=r["provider"],
        base_url=r["base_url"],
        model_name=r["model_name"],
        api_key_masked=mask(decrypt(r["api_key_enc"])) if r["api_key_enc"] else "",
        extra=extra_dict,
    )


@router.get("")
async def list_models() -> list[ModelConfigOut]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM model_configs ORDER BY id DESC")
    rows = await cursor.fetchall()
    return [await _row_to_out(r) for r in rows]


@router.post("", status_code=201)
async def create_model(body: ModelConfigIn) -> ModelConfigOut:
    db = await get_db()
    api_key_enc = encrypt(body.api_key)
    cur = await db.execute(
        "INSERT INTO model_configs (name, provider, base_url, model_name, api_key_enc, extra) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (body.name, body.provider, body.base_url, body.model_name, api_key_enc, json.dumps(body.extra)),
    )
    last_id = cur.lastrowid
    await db.commit()
    cursor = await db.execute("SELECT * FROM model_configs WHERE id=?", (last_id,))
    r = await cursor.fetchone()
    return await _row_to_out(r)


@router.put("/{model_id}")
async def update_model(model_id: int, body: ModelConfigIn) -> ModelConfigOut:
    db = await get_db()
    if body.api_key:
        await db.execute(
            "UPDATE model_configs SET name=?, provider=?, base_url=?, model_name=?, api_key_enc=?, extra=? WHERE id=?",
            (body.name, body.provider, body.base_url, body.model_name, encrypt(body.api_key), json.dumps(body.extra), model_id),
        )
    else:
        await db.execute(
            "UPDATE model_configs SET name=?, provider=?, base_url=?, model_name=?, extra=? WHERE id=?",
            (body.name, body.provider, body.base_url, body.model_name, json.dumps(body.extra), model_id),
        )
    await db.commit()
    cursor = await db.execute("SELECT * FROM model_configs WHERE id=?", (model_id,))
    r = await cursor.fetchone()
    if r is None:
        raise HTTPException(404, "模型配置不存在")
    return await _row_to_out(r)


@router.delete("/{model_id}", status_code=204)
async def delete_model(model_id: int):
    db = await get_db()
    await db.execute("DELETE FROM model_configs WHERE id=?", (model_id,))
    await db.commit()
