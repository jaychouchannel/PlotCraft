from __future__ import annotations

import aiosqlite

from .config import get_settings

DB: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global DB
    if DB is None:
        db_path = get_settings().db_file
        DB = await aiosqlite.connect(str(db_path))
        DB.row_factory = aiosqlite.Row
        await _init_tables(DB)
    return DB


async def close_db():
    global DB
    if DB is not None:
        await DB.close()
        DB = None


async def _init_tables(db: aiosqlite.Connection):
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS model_configs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL DEFAULT '',
            provider    TEXT    NOT NULL,          -- openai_compat | gemini | replicate
            base_url    TEXT    NOT NULL DEFAULT '',
            model_name  TEXT    NOT NULL,
            api_key_enc TEXT    NOT NULL DEFAULT '',
            extra       TEXT    NOT NULL DEFAULT '{}',  -- JSON
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS templates (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            category      TEXT    NOT NULL DEFAULT '',
            system_prompt TEXT    NOT NULL DEFAULT '',
            user_template TEXT    NOT NULL DEFAULT '',
            builtin       INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS generations (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id         INTEGER NOT NULL,
            template_id      INTEGER,
            user_input       TEXT    NOT NULL DEFAULT '',
            generated_code   TEXT    NOT NULL DEFAULT '',
            output_svg       TEXT    NOT NULL DEFAULT '',
            output_svg_path  TEXT    NOT NULL DEFAULT '',
            status           TEXT    NOT NULL DEFAULT 'pending',
            error            TEXT    NOT NULL DEFAULT '',
            created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """)
    await db.commit()
