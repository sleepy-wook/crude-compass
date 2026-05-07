"""Lakebase Postgres client with OAuth token refresh.

Databricks Apps auto-injects: PGHOST, PGPORT, PGDATABASE, PGUSER, PGSSLMODE, PGAPPNAME.
PGPASSWORD is NOT injected — must be obtained via WorkspaceClient.database.generate_database_credential().
Token TTL is 1h; we refresh 5 minutes before expiry.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime, timedelta, timezone

import psycopg


class LakebaseClient:
    """Threadsafe Lakebase connection helper. Use `with client.conn() as c: ...`."""

    _token: str | None
    _expires_at: datetime | None

    def __init__(self) -> None:
        self._token = None
        self._expires_at = None
        self._lock = threading.Lock()

    def _refresh_token(self) -> str:
        """Acquire fresh OAuth token from Databricks SDK. Cached 1h with 5m refresh window."""
        # lazy import — keeps tests fast and allows running without SDK in dev
        from databricks.sdk import WorkspaceClient

        instance = os.environ.get("DATABRICKS_LAKEBASE_INSTANCE")
        if not instance:
            raise RuntimeError(
                "DATABRICKS_LAKEBASE_INSTANCE env var missing. "
                "Set it to the Lakebase Postgres instance name."
            )

        w = WorkspaceClient()
        creds = w.database.generate_database_credential(instance_names=[instance])
        self._token = creds.token  # type: ignore[attr-defined]
        # 1h TTL per Databricks docs; refresh 5m early
        self._expires_at = datetime.now(timezone.utc) + timedelta(seconds=3600)
        if not self._token:
            raise RuntimeError("Lakebase OAuth credential returned empty token")
        return self._token

    def _get_token(self) -> str:
        with self._lock:
            if (
                self._token
                and self._expires_at
                and datetime.now(timezone.utc) < self._expires_at - timedelta(minutes=5)
            ):
                return self._token
            return self._refresh_token()

    def conn(self) -> psycopg.Connection:
        """Return a new psycopg connection. Caller manages with-block lifetime."""
        return psycopg.connect(
            host=os.environ["PGHOST"],
            port=int(os.environ.get("PGPORT", "5432")),
            dbname=os.environ["PGDATABASE"],
            user=os.environ["PGUSER"],
            password=self._get_token(),
            sslmode=os.environ.get("PGSSLMODE", "require"),
            application_name=os.environ.get("PGAPPNAME", "crude-compass"),
        )
