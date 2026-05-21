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
    ecos_api_key: str = Field(default_factory=lambda: os.getenv("ECOS_API_KEY", ""))

    # Slack (Databricks secret scope=crude)
    slack_bot_token: str = Field(default_factory=lambda: os.getenv("SLACK_BOT_TOKEN", ""))
    slack_signing_secret: str = Field(
        default_factory=lambda: os.getenv("SLACK_SIGNING_SECRET", "")
    )
    # 데모 채널 ID (예: C0123...). 형욱 manual: workspace #crude-compass-demo 만든 후 .env 박기.
    # 비어있으면 dry-run 강등.
    slack_default_channel: str = Field(
        default_factory=lambda: os.getenv("SLACK_DEFAULT_CHANNEL", "")
    )
    # 일일 보고서 전용 채널 (미설정 시 default_channel로 fallback)
    slack_daily_channel: str = Field(
        default_factory=lambda: os.getenv("SLACK_DAILY_CHANNEL", "")
    )

    # Demo mode (production X, 데모용 endpoint enable)
    demo_mode: bool = Field(default_factory=lambda: os.getenv("DEMO_MODE", "false").lower() == "true")

    @property
    def slack_enabled(self) -> bool:
        """bot_token + signing_secret + default_channel 셋 다 채워졌을 때만 live."""
        return bool(self.slack_bot_token and self.slack_signing_secret and self.slack_default_channel)

    # Genie Space (D-2 형욱 manual 등록 — Workspace UI에서 space_id 발급)
    # 비어있으면 /api/genie/query는 fallback 모드로 graceful degrade.
    genie_space_id: str = Field(default_factory=lambda: os.getenv("GENIE_SPACE_ID", ""))

    @property
    def genie_enabled(self) -> bool:
        """Genie Space ID 등록되어 있으면 live SDK 호출."""
        return bool(self.genie_space_id)

    # Agent Bricks Supervisor Agent endpoint (D-2 형욱 manual 등록 — 3 sub-agent 오케스트레이션)
    # 비어있으면 /api/supervisor/query는 Genie fallback으로 graceful degrade.
    supervisor_endpoint_name: str = Field(
        default_factory=lambda: os.getenv("SUPERVISOR_ENDPOINT_NAME", "")
    )

    @property
    def supervisor_enabled(self) -> bool:
        """Supervisor endpoint 등록되어 있으면 live OpenAI client 호출."""
        return bool(self.supervisor_endpoint_name)

    # Databricks SDK는 환경변수 또는 ~/.databrickscfg 자동 로드
    # (DATABRICKS_HOST + DATABRICKS_TOKEN 또는 PROFILE)

    # SQL Warehouse — statement_execution용. Genie space의 warehouse_id 기본값
    # (SDK list-spaces로 확인). DATABRICKS_WAREHOUSE_ID env로 override 가능.
    databricks_warehouse_id: str = Field(
        default_factory=lambda: os.getenv("DATABRICKS_WAREHOUSE_ID", "da56f72320e22238")
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
