"""K-Petroleum 5척 fleet position endpoint.

시나리오 §4 + §6.5: K-Petroleum 가상 fleet (KPETRO_001~005) lifecycle 시각화.
실데이터: bronze.ais_positions 의 5척 (mmsi LIKE 'KPETRO_%') latest position.
"""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter

from app.api.pattern import _q

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/fleet", tags=["fleet"])

# 시나리오 §4 5척 fleet (anonymize ID 고정 slot)
_FLEET_IDS = ["KPETRO_001", "KPETRO_002", "KPETRO_003", "KPETRO_004", "KPETRO_005"]

FleetZone = Literal[
    "hormuz", "red_sea", "indian_ocean", "korean_waters", "gulf_of_mexico", "transit", "unknown"
]


def _classify_zone(
    lat: float | None, lon: float | None, in_hormuz_bbox: bool | None
) -> FleetZone:
    """5척 lifecycle zone 분류 (시나리오 §6.5 narrative).

    Persian Gulf trade route 단순화 bbox:
    - hormuz: bronze.ais_positions의 in_hormuz_bbox flag 우선
    - red_sea: 12~30N, 32~43E (Yanbu/Jeddah)
    - indian_ocean: -30~20N, 40~80E (희망봉/수에즈 우회 경로 중간)
    - korean_waters: 33~38N, 124~132E (Yeosu/Ulsan/Onsan)
    - gulf_of_mexico: 15~32N, -100~-80E (Galveston/Corpus 미주)
    - transit: 그 외 lat/lon 있는 경우
    - unknown: lat/lon null (데이터 미적재)
    """
    if lat is None or lon is None:
        return "unknown"
    if in_hormuz_bbox:
        return "hormuz"
    if 12 <= lat <= 30 and 32 <= lon <= 43:
        return "red_sea"
    if -30 <= lat <= 20 and 40 <= lon <= 80:
        return "indian_ocean"
    if 33 <= lat <= 38 and 124 <= lon <= 132:
        return "korean_waters"
    if 15 <= lat <= 32 and -100 <= lon <= -80:
        return "gulf_of_mexico"
    return "transit"


@router.get("/positions")
async def fleet_positions() -> dict:
    """K-Petroleum 5척 latest position + zone classification.

    5 fixed slot 보장 — 데이터 미적재 vessel은 placeholder (zone='unknown') 반환.
    """
    sql = """
      SELECT mmsi, vessel_name, lat, lon, speed_knots, heading_deg,
             in_hormuz_bbox, status, fetched_at
      FROM crude_compass.bronze.ais_positions
      WHERE mmsi LIKE 'KPETRO_%'
      QUALIFY ROW_NUMBER() OVER (PARTITION BY mmsi ORDER BY fetched_at DESC) = 1
    """
    try:
        rows = _q(sql, timeout="15s")
    except Exception as e:
        logger.warning("fleet positions fetch failed: %s", e)
        rows = []

    by_mmsi: dict[str, dict] = {}
    for r in rows:
        mmsi = str(r[0])
        lat = float(r[2]) if r[2] is not None else None
        lon = float(r[3]) if r[3] is not None else None
        # bronze.ais_positions의 boolean이 string 'true'/'false'로 직렬화됨 (Spark Connect)
        in_hormuz = (str(r[6]).lower() == "true") if r[6] is not None else False
        by_mmsi[mmsi] = {
            "mmsi": mmsi,
            "vessel_name": str(r[1]) if r[1] else None,
            "lat": lat,
            "lon": lon,
            "speed_knots": float(r[4]) if r[4] is not None else None,
            "heading_deg": int(r[5]) if r[5] is not None else None,
            "in_hormuz_bbox": in_hormuz,
            "status": str(r[7]) if r[7] else None,
            "fetched_at": str(r[8]) if r[8] else None,
            "zone": _classify_zone(lat, lon, in_hormuz),
        }

    # 5 fixed slot 보장 — 미적재 vessel은 placeholder
    vessels = []
    for fleet_id in _FLEET_IDS:
        if fleet_id in by_mmsi:
            vessels.append(by_mmsi[fleet_id])
        else:
            vessels.append({
                "mmsi": fleet_id,
                "vessel_name": None,
                "lat": None,
                "lon": None,
                "speed_knots": None,
                "heading_deg": None,
                "in_hormuz_bbox": None,
                "status": "no_data",
                "fetched_at": None,
                "zone": "unknown",
            })

    return {"vessels": vessels}
