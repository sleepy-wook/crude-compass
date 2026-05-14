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

# MAGIC %pip install --quiet websockets==13.1 nest-asyncio==1.6.0
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import asyncio
import json
import time
from datetime import datetime, timezone
from decimal import Decimal

import nest_asyncio  # Databricks Runtime은 이미 event loop 안에서 실행 → asyncio.run 충돌
import websockets
from pyspark.sql import Row
from pyspark.sql.types import (
    StructType, StructField, StringType, TimestampType, DoubleType,
    DecimalType, IntegerType, BooleanType
)

nest_asyncio.apply()

# COMMAND ----------

WS_URL = "wss://stream.aisstream.io/v0/stream"
TARGET_TABLE = "crude_compass.bronze.ais_positions"

# K-Petroleum 가상 fleet — 시나리오 §4 "AIS open data 기반" 실증
# 실데이터: SK Shipping operated VLCC fleet (한국 flag 440/441, DWT 299k-313k, VLCC)
# 검증 5/14 VesselFinder. config: databricks/config/k_petroleum_fleet.yml
# anonymize 매핑: MMSI → KPETRO_<NNN> (UI/저장 시점)
KPETRO_FLEET = {
    "441450000": "KPETRO_001",  # C. CHALLENGER, 313,918 DWT, built 2013
    "440266000": "KPETRO_002",  # UNIVERSAL LEADER, 299,981 DWT, built 2019
    "440274000": "KPETRO_003",  # UNIVERSAL WINNER, 299,981 DWT, built 2019
    "440271000": "KPETRO_004",  # UNIVERSAL PARTNER, 299,981 DWT, built 2019
    "440265000": "KPETRO_005",  # UNIVERSAL CREATOR, 299,981 DWT, built 2019
}
KPETRO_MMSI_LIST = list(KPETRO_FLEET.keys())

# 호르무즈 BBOX (시나리오 §6.5 leading indicator) + 한국 항구 BBOX
# FiltersShipMMSI + BoundingBoxes는 AND. 5척이 어디 있든 잡으려면 글로벌 bbox 필요.
GLOBAL_BBOX = [[[-90.0, -180.0], [90.0, 180.0]]]

# 호르무즈 bbox — 향후 background traffic 분석용
HORMUZ_BBOX = [[[24.0, 54.0], [28.0, 58.0]]]

# 한국 항구 UN/LOCODE (cargo lifecycle 분류)
KOREA_PORTS = {"KRYSU", "KRUSN", "KRDSN", "KRINC"}
ME_PORTS = {"SARTA", "SAJUM", "KWMEA", "AEFJR", "AEKHF", "AEJED"}

api_key = dbutils.secrets.get(scope="crude", key="aisstream_api_key")

# COMMAND ----------

def in_hormuz(lat: float, lon: float) -> bool:
    return 24.0 <= lat <= 28.0 and 54.0 <= lon <= 58.0


def in_korea_coast(lat: float, lon: float) -> bool:
    """한국 동남부 항구 영역 (Incheon~Busan)."""
    return 33.0 <= lat <= 38.0 and 124.0 <= lon <= 132.0


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

async def collect_ais(timeout_seconds: int = 60) -> list[dict]:
    """WebSocket collect — K-Petroleum 5척 fleet (FiltersShipMMSI) 글로벌 추적.

    5척이 어디 있든 (호르무즈/인도양/한국 항만) 위치 보고. BBOX는 global.
    """
    out: list[dict] = []
    try:
        async with websockets.connect(WS_URL, open_timeout=10) as ws:
            await ws.send(json.dumps({
                "APIKey": api_key,
                "BoundingBoxes": GLOBAL_BBOX,
                "FiltersShipMMSI": KPETRO_MMSI_LIST,
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

print(f"[K-Petroleum fleet] 5척 MMSI subscribe (180s collection — VLCC AIS report freq ~6min)")
print(f"  MMSI: {KPETRO_MMSI_LIST}")
messages = asyncio.run(collect_ais(180))
print(f"  raw messages received: {len(messages)}")

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

# Filter: K-Petroleum 5척 (FiltersShipMMSI로 이미 server-side filter됨)
# anonymize 매핑: 9-digit MMSI → KPETRO_<NNN>
# 시나리오 §4 "AIS open data 기반 가상 VLCC 5척" + phase2_critique I8 정합
rows = []
for mmsi, r in positions.items():
    if not (r["lat"] and r["lon"]):
        continue
    # 우리 fleet 5척만 매칭 (FiltersShipMMSI 이미 적용됐지만 안전 double-check)
    anon_id = KPETRO_FLEET.get(mmsi)
    if anon_id is None:
        continue

    # vessel_name도 anonymize (실제 이름 노출 X)
    vessel_name_anon = f"VLCC {anon_id}"

    status = classify_status(r["speed_knots"] or 0, r["lat"], r["lon"])

    # DecimalType(4,1) — Decimal 명시 (Spark Connect float coerce 안 함)
    speed_raw = r.get("speed_knots") or 0.0
    speed_dec = Decimal(f"{float(speed_raw):.1f}")
    in_hormuz_flag = in_hormuz(r["lat"], r["lon"])
    rows.append(Row(
        fetched_at=now,
        mmsi=anon_id,  # anonymized (KPETRO_001~005), 9-digit X
        vessel_name=vessel_name_anon,
        lat=float(r["lat"]),
        lon=float(r["lon"]),
        speed_knots=speed_dec,
        heading_deg=r.get("heading_deg") if r.get("heading_deg") != 511 else None,
        in_hormuz_bbox=in_hormuz_flag,
        status=status,
    ))

print(f"\n[K-Petroleum fleet] {len(rows)}/{len(KPETRO_FLEET)} vessels with live AIS")
for row in rows:
    print(f"      {row.mmsi}: lat={row.lat:.2f} lon={row.lon:.2f} "
          f"speed={row.speed_knots}kts status={row.status} hormuz={row.in_hormuz_bbox}")
missing = set(KPETRO_FLEET.values()) - {r.mmsi for r in rows}
if missing:
    print(f"      ⚠️ no message during window: {missing}")

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
