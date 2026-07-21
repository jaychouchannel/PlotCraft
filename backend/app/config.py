from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    one_encrypt_key: str = ""
    host: str = "127.0.0.1"
    port: int = 8000
    db_path: str = "./data.db"
    cors_origins: str = ""  # 逗号分隔，空值 = ["*"]（仅本地开发推荐"*"）

    @property
    def db_file(self) -> Path:
        p = Path(self.db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p.resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
