# Databricks notebook source
# MAGIC %md
# MAGIC # Job 4 — ais_batch_5min
# MAGIC
# MAGIC ## 시나리오 v2 매핑
# MAGIC - § 7 #1 AISStream (호르무즈 통과량 + 양방향 cargo)
# MAGIC - § 12 #4 cron `*/5 * * * *`
# MAGIC - § 4 cargo 한국 정유사 lifecycle (귀항 + 출항 양방향)
# MAGIC
# MAGIC ## 패턴
# MAGIC - WebSocket 연결 → 30초간 message 수집 → close (continuous 대체)
# MAGIC - 호르무즈 bbox: lat 24~28, lon 54~58
# MAGIC - 양방향 cargo filter: 한국 항구 도착 OR 중동 항구 도착 (한국향 lift)

# COMMAND ----------

# MAGIC %pip install --quiet websockets==13.1
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import asyncio
import json
import time
from datetime import datetime, timezone

import websockets
from pyspark.sql import Row
from pyspark.sql.types import (
    StructType, StructField, StringType, TimestampType, DoubleType,
    DecimalType, IntegerType, BooleanType
)

# COMMAND ----------

WS_URL = "wss://stream.aisstream.io/v0/stream"
TARGET_TABLE = "crude_compass.bronze.ais_positions"

# 호르무즈 bbox (시나리오 § 7 #1)
HORMUZ_BBOX = [[[24.0, 54.0], [28.0, 58.0]]]

# 한국 항구 UN/LOCODE (귀항 cargo)
KOREA_PORTS = {"KRYSU", "KRUSN", "KRDSN", "KRINC"}
# 중동 항구 (출항 cargo - 한국에서 lift 위해 가는 중)
ME_PORTS = {"SARTA", "SAJUM", "KWMEA", "AEFJR", "AEKHF", "AEJED"}

api_key = dbutils.secrets.get(scope="crude", key="aisstream_api_key")

# COMMAND ----------

def in_hormuz(lat: float, lon: float) -> bool:
    return 24.0 <= lat <= 28.0 and 54.0 <= lon <= 58.0


def is_relevant_destination(dest: str) -> bool:
    """양방향 한국 정유사 cargo lifecycle filter."""
    if not dest:
        return False
    d = dest.upper()
    # UN/LOCODE
    for code in KOREA_PORTS | ME_PORTS:
        if code in d:
            return True
    # Free text
    if any(kw in d for kw in ["KOREA", "YEOSU", "ULSAN", "DAESAN", "INCHON",
                                "FUJAIRAH", "RAS TANURA", "JUAYMAH"]):
        return True
    return False


def classify_status(speed_knots: float, lat: float, lon: float) -> str:
    """vessel status 분류 (시나리오 § 4 cargo lifecycle 5 단계)."""
    # 호르무즈 통제구역 (좁은 부분 lat 26.0~26.7, lon 56.0~56.5) 안에서 stuck
    in_chokepoint = 26.0 <= lat <= 26.7 and 56.0 <= lon <= 56.5
    if speed_knots < 1.0 and in_chokepoint:
        return "stranded"
    if speed_knots < 1.0:
        return "anchored"
    if in_hormuz(lat, lon):
        return "transit"
    return "safe"

# COMMAND ----------

async def collect_ais(timeout_seconds: int = 30) -> list[dict]:
    """WebSocket 30초 collect — continuous 대체."""
    out: list[dict] = []
    try:
        async with websockets.connect(WS_URL, open_timeout=10) as ws:
            await ws.send(json.dumps({
                "APIKey": api_key,
                "BoundingBoxes": HORMUZ_BBOX,
                # ShipStaticData (Type 5) + PositionReport (Type 1,2,3) 모두 받음
                "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
            }))
            t_start = time.monotonic()
            while time.monotonic() - t_start < timeout_seconds:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5)
                    msg = json.loads(raw)
                    out.append(msg)
                    if len(out) >= 200:
                        break
                except asyncio.TimeoutError:
                    if out:
                        break  # 이미 받은 게 있으면 종료
                    continue
    except Exception as e:
        print(f"  ⚠️  WebSocket error: {e}")
    return out

# COMMAND ----------

print("🌊 Hormuz bbox AIS collection (30s timeout)")
messages = asyncio.run(collect_ais(30))
print(f"  ✅ {len(messages)} raw messages received")

# COMMAND ----------

# Position + Static data merge per MMSI
positions: dict[str, dict] = {}  # mmsi → latest combined record

now = datetime.now(timezone.utc)

for msg in messages:
    meta = msg.get("MetaData", {})
    msg_type = msg.get("MessageType", "")
    mmsi = str(meta.get("MMSI", "")) or str(msg.get("Message", {}).get("PositionReport", {}).get("UserID", ""))
    if not mmsi:
        continue

    rec = positions.setdefault(mmsi, {
        "mmsi": mmsi,
        "lat": None, "lon": None,
        "speed_knots": None, "heading_deg": None,
        "vessel_name": None, "destination": None,
        "ship_type": None,
    })

    if msg_type == "PositionReport":
        pr = msg.get("Message", {}).get("PositionReport", {})
        rec["lat"] = float(pr.get("Latitude", meta.get("latitude", 0)))
        rec["lon"] = float(pr.get("Longitude", meta.get("longitude", 0)))
        rec["speed_knots"] = float(pr.get("Sog", 0))
        rec["heading_deg"] = int(pr.get("TrueHeading", 511))  # 511 = N/A
    elif msg_type == "ShipStaticData":
        sd = msg.get("Message", {}).get("ShipStaticData", {})
        rec["vessel_name"] = sd.get("Name", "").strip() or None
        rec["destination"] = sd.get("Destination", "").strip() or None
        rec["ship_type"] = sd.get("Type", 0)

    rec["lat"] = rec["lat"] or float(meta.get("latitude", 0))
    rec["lon"] = rec["lon"] or float(meta.get("longitude", 0))

# Filter: 호르무즈 bbox + tanker (ship_type 80-89 또는 unknown)
rows = []
for mmsi, r in positions.items():
    if not (r["lat"] and r["lon"]):
        continue
    if not in_hormuz(r["lat"], r["lon"]):
        continue
    # tanker only (또는 ship_type 정보 없을 때 일단 포함 — Sprint 3 보강)
    is_tanker = r.get("ship_type") is None or 80 <= r["ship_type"] <= 89

    # MMSI 가명 처리 (시나리오 § 18 익명화)
    mmsi_anon = f"ANON_{abs(hash(mmsi)) % 100000:05d}"
    vessel_name_anon = f"VLCC_{mmsi_anon}" if r.get("vessel_name") else None

    status = classify_status(r["speed_knots"] or 0, r["lat"], r["lon"])

    rows.append(Row(
        fetched_at=now,
        mmsi=mmsi_anon,
        vessel_name=vessel_name_anon,
        lat=r["lat"],
        lon=r["lon"],
        speed_knots=r.get("speed_knots") or 0.0,
        heading_deg=r.get("heading_deg") if r.get("heading_deg") != 511 else None,
        in_hormuz_bbox=True,
        status=status,
    ))

print(f"  🛢  {len(rows)} vessels in bbox")
print(f"      transit: {sum(1 for r in rows if r.status == 'transit')}")
print(f"      stranded: {sum(1 for r in rows if r.status == 'stranded')}")
print(f"      anchored: {sum(1 for r in rows if r.status == 'anchored')}")
print(f"      safe: {sum(1 for r in rows if r.status == 'safe')}")

# COMMAND ----------

if rows:
    schema = StructType([
        StructField("fetched_at", TimestampType(), False),
        StructField("mmsi", StringType(), False),
        StructField("vessel_name", StringType(), True),
        StructField("lat", DoubleType(), False),
        StructField("lon", DoubleType(), False),
        StructField("speed_knots", DecimalType(4, 1), True),
        StructField("heading_deg", IntegerType(), True),
        StructField("in_hormuz_bbox", BooleanType(), True),
        StructField("status", StringType(), True),
    ])
    df = spark.createDataFrame(rows, schema=schema)
    df.write.mode("append").saveAsTable(TARGET_TABLE)
    print(f"\n✅ {len(rows)} rows appended to {TARGET_TABLE}")
else:
    print("\nℹ️  No vessels in bbox during 30s window (호르무즈 봉쇄 영향 가능)")

dbutils.notebook.exit(json.dumps({
    "rows_written": len(rows),
    "raw_messages": len(messages),
    "unique_mmsi": len(positions),
}))
