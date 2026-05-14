/**
 * HormuzMap — Persian Gulf focus SVG map for K-Petroleum 5척.
 *
 * 디자인 mockup (design/src/charts.jsx HormuzMap) 1:1 이식 + lat/lon projection.
 * 라이브러리 0 (pure SVG). 시나리오 §6.5 (AIS leading indicator) + §14 Phase 3 anchor.
 *
 * Projection:
 *   Persian Gulf BBOX (lat 20~32, lon 47~62) → SVG viewBox 0~720 × 0~280
 *   BBOX 밖 vessel은 우상단 "External zone" indicator (off-map count)
 */
import { useFleetPositions } from "../lib/queries";
import type { FleetVessel, FleetZone } from "../lib/types";

const VIEW_W = 720;
const VIEW_H = 280;

// Persian Gulf focus bbox (lat: south→north, lon: west→east)
const BBOX = {
  lat_min: 20.0,
  lat_max: 32.0,
  lon_min: 47.0,
  lon_max: 62.0,
};

function project(lat: number, lon: number): { x: number; y: number } {
  const x = ((lon - BBOX.lon_min) / (BBOX.lon_max - BBOX.lon_min)) * VIEW_W;
  // SVG y axis: 0 at top → invert lat
  const y = ((BBOX.lat_max - lat) / (BBOX.lat_max - BBOX.lat_min)) * VIEW_H;
  return { x, y };
}

function inBbox(lat: number | null, lon: number | null): boolean {
  if (lat == null || lon == null) return false;
  return (
    lat >= BBOX.lat_min &&
    lat <= BBOX.lat_max &&
    lon >= BBOX.lon_min &&
    lon <= BBOX.lon_max
  );
}

const STATUS_COLOR: Record<string, string> = {
  stranded: "#FF3621",
  transit: "#F59E0B",
  anchored: "#10B981",
  safe: "#10B981",
  no_data: "#9CA3AF",
};

function colorFor(vessel: FleetVessel): string {
  return STATUS_COLOR[vessel.status ?? "no_data"] ?? "#9CA3AF";
}

const ZONE_LABEL: Record<FleetZone, string> = {
  hormuz: "호르무즈",
  red_sea: "홍해",
  indian_ocean: "인도양",
  korean_waters: "한국 해역",
  gulf_of_mexico: "걸프 멕시코",
  transit: "이동 중",
  unknown: "—",
};

export function HormuzMap() {
  const { data, isLoading, isError } = useFleetPositions();
  const vessels = data?.vessels ?? [];
  const onMap = vessels.filter((v) => inBbox(v.lat, v.lon));
  const offMap = vessels.filter(
    (v) => !inBbox(v.lat, v.lon) && v.status !== "no_data",
  );

  const statusBadge = isLoading
    ? "loading…"
    : isError
      ? "data unavailable"
      : `${onMap.length} on-map · ${offMap.length} external`;

  return (
    <section className="mb-6">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-display text-xl font-semibold tracking-tight">
          Persian Gulf — Strait of Hormuz Live
        </h2>
        <span className="text-[11px] text-ink-3 font-mono">
          AIS open standard · 5min cron · {statusBadge}
        </span>
      </div>

      <div className="rounded-xl border border-line-1 bg-panel overflow-hidden">
        <svg
          width="100%"
          height={VIEW_H}
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          style={{ display: "block", background: "#FAFAF7" }}
        >
          <defs>
            <pattern
              id="hormuz-grid"
              width="40"
              height="40"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 40 0 L 0 0 0 40"
                fill="none"
                stroke="#EFEFEA"
                strokeWidth="1"
              />
            </pattern>
            <radialGradient id="hormuz-glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#FF3621" stopOpacity=".22" />
              <stop offset="100%" stopColor="#FF3621" stopOpacity="0" />
            </radialGradient>
          </defs>
          <rect width={VIEW_W} height={VIEW_H} fill="url(#hormuz-grid)" />

          {/* Arabian Peninsula (Saudi Arabia + UAE — bottom landmass) */}
          <path
            d="M 60 90 L 240 70 L 360 100 L 430 150 L 470 200 L 520 240 L 540 280 L 60 280 Z"
            fill="#EDEDE7"
            stroke="#D6D6CF"
            strokeWidth="1"
          />
          {/* Iran (top landmass) */}
          <path
            d="M 280 0 L 720 0 L 720 110 L 640 130 L 540 120 L 460 130 L 400 110 L 340 90 L 300 70 Z"
            fill="#EDEDE7"
            stroke="#D6D6CF"
            strokeWidth="1"
          />
          {/* Oman peninsula (right edge) */}
          <path
            d="M 540 240 L 580 200 L 600 160 L 640 140 L 680 180 L 700 230 L 720 280 L 540 280 Z"
            fill="#EDEDE7"
            stroke="#D6D6CF"
            strokeWidth="1"
          />

          {/* Strait of Hormuz risk zone — lat 26.0~26.7, lon 56.0~56.5 */}
          <ellipse
            cx={project(26.35, 56.25).x}
            cy={project(26.35, 56.25).y}
            rx="80"
            ry="38"
            fill="url(#hormuz-glow)"
          />
          <ellipse
            cx={project(26.35, 56.25).x}
            cy={project(26.35, 56.25).y}
            rx="80"
            ry="38"
            fill="none"
            stroke="#FF3621"
            strokeWidth="1"
            strokeDasharray="4 4"
            opacity=".7"
          />

          {/* Labels */}
          <text
            x="180"
            y="200"
            fill="#7A8A91"
            fontSize="10"
            fontFamily="JetBrains Mono"
            letterSpacing="2"
          >
            SAUDI ARABIA
          </text>
          <text
            x="450"
            y="60"
            fill="#7A8A91"
            fontSize="10"
            fontFamily="JetBrains Mono"
            letterSpacing="2"
          >
            IRAN
          </text>
          <text
            x="640"
            y="260"
            fill="#7A8A91"
            fontSize="10"
            fontFamily="JetBrains Mono"
            letterSpacing="2"
          >
            OMAN
          </text>
          <text
            x="500"
            y="140"
            fill="#FF3621"
            fontSize="11"
            fontFamily="JetBrains Mono"
            fontWeight="600"
          >
            STRAIT OF HORMUZ
          </text>
          <text
            x="500"
            y="155"
            fill="#FF3621"
            fontSize="9"
            fontFamily="JetBrains Mono"
          >
            CHOKEPOINT · 30% global oil
          </text>

          {/* Korea destination indicator (off-map) */}
          <g transform="translate(670,20)">
            <rect width="42" height="22" rx="3" fill="#1B3139" />
            <text
              x="21"
              y="14"
              fill="#fff"
              fontSize="9"
              textAnchor="middle"
              fontFamily="JetBrains Mono"
              fontWeight="600"
            >
              → KR
            </text>
          </g>

          {/* Vessel positions — on map */}
          {onMap.map((v) => {
            if (v.lat == null || v.lon == null) return null;
            const { x, y } = project(v.lat, v.lon);
            const color = colorFor(v);
            return (
              <g key={v.mmsi} transform={`translate(${x},${y})`}>
                <circle r="9" fill={color} fillOpacity=".18" />
                <circle r="4" fill={color} />
                <text
                  x="9"
                  y="4"
                  fill="#1B3139"
                  fontSize="10"
                  fontFamily="JetBrains Mono"
                  fontWeight="600"
                >
                  {v.mmsi.replace("KPETRO_", "K")}
                </text>
              </g>
            );
          })}

          {/* Compass */}
          <g transform="translate(36,240)" stroke="#7A8A91" fill="none">
            <circle r="12" />
            <path d="M 0 -10 L 0 10 M -10 0 L 10 0" />
            <text
              y="-14"
              fill="#7A8A91"
              fontSize="9"
              fontFamily="JetBrains Mono"
              textAnchor="middle"
              stroke="none"
            >
              N
            </text>
          </g>

          {/* Off-map indicator (top-left) */}
          {offMap.length > 0 && (
            <g transform="translate(20,20)">
              <rect
                width="180"
                height={22 + offMap.length * 14}
                rx="4"
                fill="#FFFFFF"
                stroke="#D6D6CF"
              />
              <text
                x="10"
                y="15"
                fill="#7A8A91"
                fontSize="9"
                fontFamily="JetBrains Mono"
                letterSpacing="1"
              >
                EXTERNAL ZONES ({offMap.length})
              </text>
              {offMap.map((v, i) => (
                <text
                  key={v.mmsi}
                  x="10"
                  y={30 + i * 14}
                  fill="#1B3139"
                  fontSize="10"
                  fontFamily="JetBrains Mono"
                >
                  {v.mmsi.replace("KPETRO_", "K")} · {ZONE_LABEL[v.zone]}
                </text>
              ))}
            </g>
          )}
        </svg>

        {/* Legend strip */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-line-1 bg-line-1/30 text-[11px] font-mono text-ink-3">
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full"
              style={{ background: STATUS_COLOR.transit }}
            />
            transit
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full"
              style={{ background: STATUS_COLOR.stranded }}
            />
            stranded
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full"
              style={{ background: STATUS_COLOR.anchored }}
            />
            anchored / safe
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full"
              style={{ background: STATUS_COLOR.no_data }}
            />
            idle (no AIS)
          </span>
          <span className="ml-auto text-ink-3">
            BBOX lat {BBOX.lat_min}~{BBOX.lat_max}, lon {BBOX.lon_min}~
            {BBOX.lon_max}
          </span>
        </div>
      </div>
    </section>
  );
}
