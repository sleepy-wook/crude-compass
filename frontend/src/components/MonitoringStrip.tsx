/**
 * MonitoringStrip — active/on_track/paused dense view (full width).
 *
 * 1-line rows: [#case_id] [type] [target_pct%] [status] [confirmed Xd ago] [→]
 * 5 rows max, "전체 →" if more.
 * 톤 격하 — muted ink-3.
 */
import { Link } from "react-router-dom";
import { MissionTypePill, StatusPill } from "./StatusPill";
import { relativeTime } from "../lib/utils";
import type { Mission } from "../lib/types";

interface Props {
  cases: Mission[];
}

export function MonitoringStrip({ cases }: Props) {
  if (cases.length === 0) {
    return (
      <div className="rounded-lg border border-line-1 bg-panel/60 px-4 py-6 text-center text-[12px] text-ink-3">
        모니터링 중인 case 없음
      </div>
    );
  }

  const top = cases.slice(0, 5);
  const hasMore = cases.length > 5;

  return (
    <section className="rounded-lg border border-line-1 bg-panel/60">
      <ul className="divide-y divide-line-1">
        {top.map((m) => {
          const target = m.target_pct ?? (m.mission_type === "HEDGE" ? 75 : 70);
          const ts = m.confirmed_at ?? m.created_at;
          return (
            <li key={m.mission_id}>
              <Link
                to={`/missions/${m.mission_id}`}
                className="flex items-center gap-3 px-4 py-2 text-[12px] hover:bg-line-1/40 transition-colors"
              >
                <span className="shrink-0 tabular-nums text-ink-3 text-[11px] w-14">
                  #{m.mission_id.slice(0, 6)}
                </span>
                <span className="shrink-0">
                  <MissionTypePill type={m.mission_type} />
                </span>
                <span className="shrink-0 tabular-nums text-ink-3">
                  {m.mission_type === "HEDGE" ? "Term" : "Spot"} {target}%
                </span>
                <span className="shrink-0">
                  <StatusPill status={m.status} />
                </span>
                <span className="shrink-0 text-ink-3 text-[11px]">
                  확정 {relativeTime(ts)}
                </span>
                <span className="ml-auto text-ink-3 text-[12px]" aria-hidden>
                  →
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
      {hasMore && (
        <div className="px-4 py-2 border-t border-line-1">
          <Link
            to="/missions"
            className="text-[11px] text-ink-3 hover:text-ink-1 transition-colors"
          >
            전체 → ({cases.length})
          </Link>
        </div>
      )}
    </section>
  );
}
