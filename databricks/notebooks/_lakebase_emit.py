"""Notebook → Lakebase agent_activity_events emit helper.

Job notebook (Spark/Python) 안에서 fire-and-forget으로 호출:
    from _lakebase_emit import emit
    emit(actor='gdelt', action='signal_detected',
         result_preview='Hormuz importance 78', metadata={'article_id': '...'})

Lakebase 미연결 / 권한 부족 / network fail → silent skip (notebook flow 막지 않음).

Auth: Databricks SDK OAuth token + Apps secret scope의 lakebase_host/database/user/endpoint_path.
Notebooks가 backend FastAPI 우회 (별도 Spark process).
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)


def _get_lakebase_conn():
    """secret scope 'crude'에서 Lakebase config 읽어 psycopg conn 반환.

    Databricks notebook context (dbutils 가용) 또는 local env var 둘 다 지원.
    """
    try:
        from pyspark.dbutils import DBUtils  # type: ignore
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        dbutils = DBUtils(spark)
        host = dbutils.secrets.get(scope="crude", key="lakebase_host")
        database = dbutils.secrets.get(scope="crude", key="lakebase_database")
        user = dbutils.secrets.get(scope="crude", key="lakebase_user")
        endpoint_path = dbutils.secrets.get(scope="crude", key="lakebase_endpoint_path")
    except Exception:
        host = os.getenv("LAKEBASE_HOST")
        database = os.getenv("LAKEBASE_DATABASE")
        user = os.getenv("LAKEBASE_USER")
        endpoint_path = os.getenv("LAKEBASE_ENDPOINT_PATH")
    if not (host and database and user and endpoint_path):
        return None

    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        try:
            auth = w.config.authenticate()
            token = auth.get("Authorization", "").removeprefix("Bearer ")
        except Exception:
            token = None
        if not token:
            instance_name = endpoint_path.split("/")[1] if endpoint_path.startswith("projects/") else endpoint_path
            credential = w.database.generate_database_credential(
                request_id=str(uuid.uuid4()), instance_names=[instance_name],
            )
            token = credential.token
    except Exception as e:
        logger.warning("lakebase token gen failed: %s", e)
        return None

    try:
        import psycopg
        conn = psycopg.connect(
            f"host={host} dbname={database} user={user} password={token} sslmode=require connect_timeout=10",
            autocommit=False,
        )
        return conn
    except Exception as e:
        logger.warning("lakebase psycopg connect failed: %s", e)
        return None


def emit(
    *,
    actor: str,
    action: str,
    result_preview: str | None = None,
    metadata: dict[str, Any] | None = None,
    mission_id: str | None = None,
) -> bool:
    """Best-effort INSERT — fail silent.

    Args:
        actor: gdelt | curation_job | price_job | reactive | system | ...
        action: signal_detected | score_computed | mission_proposed | revision_suggested | trigger_fired | ...
        result_preview: 80자 내외 한 줄 요약
        metadata: JSONB로 저장될 dict
        mission_id: 연관 case가 있으면. 없으면 None → 전역 system event.
    """
    conn = _get_lakebase_conn()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_activity_events
                    (mission_id, actor, action, result_preview, metadata)
                VALUES
                    (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    mission_id,
                    actor,
                    action,
                    result_preview,
                    json.dumps(metadata) if metadata else None,
                ),
            )
        conn.commit()
        return True
    except Exception as e:
        logger.warning("lakebase emit failed (actor=%s action=%s): %s", actor, action, e)
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass
