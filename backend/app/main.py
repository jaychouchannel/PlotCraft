from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import close_db, get_db
from .routes import generate, history, models, templates


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("plot-gen-backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.one_encrypt_key:
        log.warning(
            "未设置 ONE_ENCRYPT_KEY — 模型 api_key 将无法加密存储。"
            "请生成 Fernet 密钥并写入 backend/.env：\n"
            '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    # 初始化 db 并播种内置模板
    await get_db()
    n = await templates.seed_templates_if_empty()
    if n:
        log.info(f"已播种 {n} 个内置模板")
    log.info(f"后端启动完毕：http://{settings.host}:{settings.port}")
    yield
    await close_db()


app = FastAPI(
    title="科研论文矢量图生成器 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models.router)
app.include_router(templates.router)
app.include_router(generate.router)
app.include_router(history.router)


@app.get("/")
async def root():
    return {"name": "科研论文矢量图生成器 API", "docs": "/docs"}
