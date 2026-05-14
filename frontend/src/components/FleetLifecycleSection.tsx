/**
 * K-Petroleum 5척 lifecycle card section (시나리오 §4 + §6.5).
 *
 * Discovery 페이지 통합. bronze.ais_positions 5분 cron 라이브 데이터.
 * 5 fixed slot 보장 — 미적재 vessel은 'no_data' placeholder.
 */
import { useFleetPositions } from "../lib/queries";
import type { FleetVessel, FleetZone } from "../lib/types";
import { Term } from "./Glossary";
import { relativeTime } from "../lib/utils";

const ZONE_LABEL: Record<FleetZone, string> = {
  hormuz: "호르무즈",
  red_sea: "홍해",
  indian_ocean: "인도양",
  korean_waters: "한국 해역",
  gulf_of_mexico: "걸프",
  transit: "이동 중",
  unknown: "—",
};

const ZONE_VARIANT: Record<FleetZone, string> = {
  hormuz: "bg-crisis-50 text-crisis-700 border-crisis-100",
  red_sea: "bg-amber-50 text-amber-700 border-amber-200",
  indian_ocean: "bg-amber-50 text-amber-700 border-amber-200",
  korean_waters: "bg-opportunity-50 text-opportunity-700 border-opportunity-100",
  gulf_of_mexico: "bg-line-1 text-ink-2 border-line-2",
  transit: "bg-line-1 text-ink-2 border-line-2",
  unknown: "bg-line-1 text-ink-3 border-line-2",
};

function ZonePill({ zone }: { zone: FleetZone }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] border font-medium ${ZONE_VARIANT[zone]}`}
    >
      {ZONE_LABEL[zone]}
    </span>
  );
}

function VesselCard({ vessel }: { vessel: FleetVessel }) {
  const isPlaceholder = vessel.status === "no_data";

  return (
    <div
      className={`rounded-lg border p-3 ${
        isPlaceholder
          ? "bg-line-1/40 border-line-2"
          : "bg-panel border-line-1"
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="font-mono text-[11px] uppercase tracking-wider text-ink-2">
          {vessel.mmsi}
        </div>
        <ZonePill zone={vessel.zone} />
      </div>

      {isPlaceholder ? (
        <div className="text-[11px] text-ink-3 leading-snug">
          데이터 축적 중<br />
          <span className="text-[10px] font-mono">매 5분 cron · AIS ~6분</span>
        </div>
      ) : (
        <>
          <div className="font-mono text-[11px] text-ink-3 leading-snug mb-1.5">
            {vessel.lat?.toFixed(2)} · {vessel.lon?.toFixed(2)}
          </div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="font-display text-lg font-semibold text-ink">
              {vessel.speed_knots?.toFixed(1) ?? "—"}
            </span>
            <span className="text-[10px] text-ink-3">knots</span>
          </div>
          <div className="flex items-center justify-between text-[10px] text-ink-3">
            <span className="capitalize">{vessel.status}</span>
            <span className="font-mono">{relativeTime(vessel.fetched_at)}</span>
          </div>
        </>
      )}
    </div>
  );
}

export function FleetLifecycleSection() {
  const { data, isLoading, isError } = useFleetPositions();
  const vessels = data?.vessels ?? [];

  return (
    <section className="mb-8">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-display text-xl font-semibold tracking-tight">
          <Term name="KPETRO_FLEET">K-Petroleum 5척</Term> — Persian Gulf → Korea 실시간 추적
        </h2>
        <span className="text-[11px] text-ink-3 font-mono">매 15초 갱신</span>
      </div>
      <p className="text-xs text-ink-3 mb-3">
        AIS 공개 데이터 (IMO mandate) + <code className="text-[11px]">KPETRO_NNN</code> 익명화 표시.
        시나리오 §4 가상 fleet narrative.
      </p>

      {isLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="rounded-lg border border-line-1 bg-line-1/30 p-3 h-24 animate-pulse"
            />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-line-1 bg-panel p-4 text-xs text-ink-3">
          실시간 fleet 데이터 일시 불가. cron 매 5분.
        </div>
      )}

      {!isLoading && !isError && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {vessels.map((v) => (
            <VesselCard key={v.mmsi} vessel={v} />
          ))}
        </div>
      )}
    </section>
  );
}
