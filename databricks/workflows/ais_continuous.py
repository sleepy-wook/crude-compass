"""aisstream WebSocket → bronze.ais_positions (continuous task).

**Apps 외부에서 실행** — Apps의 scale-to-zero 정책 회피 (2026-05 검증).

Lakeflow Workflow continuous task로 등록:
    databricks bundle deploy
    (workflow 정의는 databricks/jobs/ais_workflow.yml — 사용자가 등록)

aisstream 무료 tier:
- BoundingBoxes: 호르무즈 해협 (24°N~27.5°N, 54°E~58°E)
- FiltersShipMMSI: 익명 charter VLCC 5척 (.env에 MMSI list)
- 메시지 타입: PositionReport (5초~30초 주기) + ShipStaticData (10분 주기)

Secret 등록 (사용자 작업):
    databricks secrets put-secret crude-compass aisstream-key
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import websockets

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    BigIntType,
    DoubleType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

logger = logging.getLogger(__name__)

WSS_URL = "wss://stream.aisstream.io/v0/stream"
TARGET_TABLE = "crude_compass.bronze.ais_positions"

# 호르무즈 해협 BoundingBox (lat, lon)
HORMUZ_BBOX = [[24.0, 54.0], [27.5, 58.0]]

# 익명 charter VLCC MMSI 5척 (env에서 comma-separated 로드)
DEFAULT_MMSI = [538009311, 538009312, 538009313, 538009314, 538009315]

AIS_SCHEMA = StructType(
    [
        StructField("received_at", TimestampType(), nullable=False),
        StructField("mmsi", BigIntType(), nullable=False),
        StructField("ship_name", StringType(), nullable=True),
        StructField("ship_type", StringType(), nullable=True),
        StructField("flag", StringType(), nullable=True),
        StructField("latitude", DoubleType(), nullable=False),
        StructField("longitude", DoubleType(), nullable=False),
        StructField("sog", DoubleType(), nullable=True),
        StructField("cog", DoubleType(), nullable=True),
        StructField("destination", StringType(), nullable=True),
        StructField("message_type", StringType(), nullable=True),
        StructField("raw", StringType(), nullable=True),
    ]
)


def _api_key() -> str:
    key = os.environ.get("AISSTREAM_KEY")
    if not key:
        try:
            from databricks.sdk.runtime import dbutils  # type: ignore

            key = dbutils.secrets.get(scope="crude-compass", key="aisstream-key")
        except Exception as e:
            raise RuntimeError("AISSTREAM_KEY 또는 secret 필요") from e
    return key


def _mmsi_list() -> list[int]:
    raw = os.environ.get("AIS_CHARTER_MMSI")
    if not raw:
        return DEFAULT_MMSI
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def _row_from_msg(msg: dict) -> tuple | None:
    """aisstream 메시지를 schema-conformant tuple로 변환. None이면 skip."""
    msg_type = msg.get("MessageType")
    metadata = msg.get("MetaData", {})

    if msg_type == "PositionReport":
        body = msg.get("Message", {}).get("PositionReport", {})
        lat = body.get("Latitude")
        lon = body.get("Longitude")
        if lat is None or lon is None:
            return None
        return (
            datetime.now(timezone.utc),
            int(metadata.get("MMSI", 0)),
            metadata.get("ShipName", "").strip() or None,
            None,  # ship_type from PositionReport 없음
            None,
            float(lat),
            float(lon),
            float(body.get("Sog", 0.0)) if body.get("Sog") is not None else None,
            float(body.get("Cog", 0.0)) if body.get("Cog") is not None else None,
            None,  # destination
            "PositionReport",
            json.dumps(msg, ensure_ascii=False),
        )
    if msg_type == "ShipStaticData":
        body = msg.get("Message", {}).get("ShipStaticData", {})
        # Static data엔 위치 없음 — 포지션 row 만들지 않고 skip
        # (별도 ship_meta 테이블이 필요하면 Phase 1 Part C에서 분리)
        return None
    return None


async def stream_loop(spark: SparkSession) -> None:
    """WebSocket subscribe + buffer 100건 또는 5초마다 Bronze append."""
    api_key = _api_key()
    mmsi_list = _mmsi_list()

    subscribe_msg = {
        "APIKey": api_key,
        "BoundingBoxes": [HORMUZ_BBOX],
        "FiltersShipMMSI": [str(m) for m in mmsi_list],
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    }

    buffer: list[tuple] = []
    BUFFER_FLUSH_SIZE = 100
    BUFFER_FLUSH_SECONDS = 5.0

    async with websockets.connect(WSS_URL, ping_interval=30) as ws:
        await ws.send(json.dumps(subscribe_msg))
        logger.info(
            "aisstream subscribed: bbox=%s mmsi=%d count", HORMUZ_BBOX, len(mmsi_list)
        )

        last_flush = asyncio.get_running_loop().time()

        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            row = _row_from_msg(msg)
            if row is not None:
                buffer.append(row)

            now = asyncio.get_running_loop().time()
            if len(buffer) >= BUFFER_FLUSH_SIZE or (now - last_flush) >= BUFFER_FLUSH_SECONDS:
                if buffer:
                    df = spark.createDataFrame(buffer, schema=AIS_SCHEMA)
                    df.write.mode("append").saveAsTable(TARGET_TABLE)
                    logger.info("flushed %d rows to %s", len(buffer), TARGET_TABLE)
                    buffer.clear()
                last_flush = now


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    spark = SparkSession.builder.getOrCreate()
    while True:
        try:
            asyncio.run(stream_loop(spark))
        except (websockets.ConnectionClosed, OSError) as e:
            logger.warning("WS disconnect: %s — reconnecting in 5s", e)
            import time

            time.sleep(5)


if __name__ == "__main__":
    main()
