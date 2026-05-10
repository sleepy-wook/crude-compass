"""Application configuration.

- Local dev: read from .env (python-dotenv)
- Databricks Apps: read from environment variables (Apps secret resource auto-injected)

Lakebase 인증은 정적 password 저장 X — runtime에 Databricks SDK가 OAuth token 발급.
저장하는 정보는 host/database/endpoint_path/user (정적 메타데이터)만.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Local dev .env load (Apps deploy 시에는 무시됨)
load_dotenv()


class Settings(BaseModel):
    # Lakebase static metadata (token은 runtime SDK 발급)
    lakebase_host: str = Field(default_factory=lambda: os.getenv("LAKEBASE_HOST", ""))
    lakebase_database: str = Field(
        default_factory=lambda: os.getenv("LAKEBASE_DATABASE", "databricks_postgres")
    )
    lakebase_endpoint_path: str = Field(
        default_factory=lambda: os.getenv("LAKEBASE_ENDPOINT_PATH", "")
    )
    lakebase_user: str = Field(default_factory=lambda: os.getenv("LAKEBASE_USER", ""))

    # External API keys
    oilprice_api_key: str = Field(default_factory=lambda: os.getenv("OILPRICE_API_KEY", ""))
    aisstream_api_key: str = Field(default_factory=lambda: os.getenv("AISSTREAM_API_KEY", ""))
    ecos_api_key: str = Field(default_factory=lambda: os.getenv("ECOS_API_KEY", ""))

    # Slack (Sprint 4 진입 시 등록)
    slack_bot_token: str = Field(default_factory=lambda: os.getenv("SLACK_BOT_TOKEN", ""))
    slack_signing_secret: str = Field(
        default_factory=lambda: os.getenv("SLACK_SIGNING_SECRET", "")
    )

    # Demo mode (production X, 데모용 endpoint enable)
    demo_mode: bool = Field(default_factory=lambda: os.getenv("DEMO_MODE", "false").lower() == "true")

    # Databricks SDK는 환경변수 또는 ~/.databrickscfg 자동 로드
    # (DATABRICKS_HOST + DATABRICKS_TOKEN 또는 PROFILE)


@lru_cache
def get_settings() -> Settings:
    return Settings()
