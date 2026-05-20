"""user_last_seen repo — Decision Room delta strip 기준점.

Schema (lakebase.py migrate_decision_room):
  user_last_seen (user_key PK, last_seen_at, updated_at)

single-user demo. user_key='default' 한 row만 사용.
"""
from __future__ import annotations

import logging
from datetime import datetime

import psycopg

logger = logging.getLogger(__name__)


def get_last_seen(conn: psycopg.Connection, user_key: str = "default") -> datetime | None:
    """Returns last_seen_at for given user_key, or None on fail / missing row."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT last_seen_at FROM user_last_seen WHERE user_key = %s",
                (user_key,),
            )
            row = cur.fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.warning("get_last_seen failed (user_key=%s): %s", user_key, e)
        return None


def touch_last_seen(conn: psycopg.Connection, user_key: str = "default") -> datetime | None:
    """UPDATE last_seen_at = NOW() + updated_at = NOW(). INSERT if not exists.

    Returns the new last_seen_at, or None on fail.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_last_seen (user_key, last_seen_at, updated_at)
                VALUES (%s, NOW(), NOW())
                ON CONFLICT (user_key) DO UPDATE
                  SET last_seen_at = NOW(),
                      updated_at = NOW()
                RETURNING last_seen_at
                """,
                (user_key,),
            )
            row = cur.fetchone()
        conn.commit()
        return row[0] if row else None
    except Exception as e:
        logger.warning("touch_last_seen failed (user_key=%s): %s", user_key, e)
        try:
            conn.rollback()
        except Exception:
            pass
        return None
