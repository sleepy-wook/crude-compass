/**
 * DeltaStrip — "자리 비운 동안 무엇이 변했나" surface.
 *
 * 조건: delta.events.length > 0 일 때만 render.
 *
 * Layout:
 *   [⟳ <시간>만에 — 새 case N · 방향 전환 M · at_risk K]      [모두 확인]
 *   • [#abcd] new_proposed (어제 06:00)
 *   • [#efgh] paused → at_risk
 */
import { Link } from "react-router-dom";
import { useDecisionDelta, useDecisionTouch } from "../lib/queries";
import { relativeTime } from "../lib/utils";
import type { DeltaEvent } from "../lib/types";

function typeIcon(t: DeltaEvent["type"]): string {
  if (t === "new_proposed") return "+";
  if (t === "pivot") return "⇄";
  if (t === "aborted") return "×";
  return "•";
}

function sinceLabel(since: string | null): string {
  if (!since) return "최근";
  const then = new Date(since).getTime();
  const diff = (Date.now() - then) / 1000;
  if (diff < 3600) return `${Math.floor(diff / 60)}분`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간`;
  return `${Math.floor(diff / 86400)}일`;
}

export function DeltaStrip() {
  const { data } = useDecisionDelta();
  const touch = useDecisionTouch();

  if (!data || data.events.length === 0) return null;

  const { events, counts, since } = data;
  const top = events.slice(0, 5);
  const atRiskCount = events.filter(
    (e) => e.type === "status_change" && (e.to === "at_risk" || e.summary.includes("at_risk")),
  ).length;

  return (
    <section className="mb-6 rounded-lg border border-line-2 bg-line-1/40 px-4 py-3">
      <div className="flex items-baseline justify-between gap-3 mb-2">
        <div className="text-[12px] text-ink-2">
          <span className="font-medium text-ink-1">⟳ {sinceLabel(since)} 만에</span>
          <span className="text-ink-3 mx-1.5">—</span>
          <span className="tabular-nums">새 case {counts.new_proposed}</span>
          <span className="text-ink-3 mx-1">·</span>
          <span className="tabular-nums">방향 전환 {counts.pivot}</span>
          {atRiskCount > 0 && (
            <>
              <span className="text-ink-3 mx-1">·</span>
              <span className="tabular-nums text-crisis-700">at_risk {atRiskCount}</span>
            </>
          )}
        </div>
        <button
          type="button"
          onClick={() => touch.mutate()}
          disabled={touch.isPending}
          className="text-[11px] text-ink-3 hover:text-ink-1 transition-colors disabled:opacity-40"
        >
          {touch.isPending ? "확인 중..." : "모두 확인"}
        </button>
      </div>
      <ul className="space-y-0.5">
        {top.map((e, idx) => (
          <li key={`${e.case_id}-${e.occurred_at}-${idx}`} className="text-[12px] leading-relaxed">
            <Link
              to={`/missions/${e.case_id}`}
              className="inline-flex items-baseline gap-1.5 text-ink-2 hover:text-ink-1 transition-colors"
            >
              <span className="text-ink-3 tabular-nums">[#{e.case_id.slice(0, 4)}]</span>
              <span className="text-ink-3" aria-hidden>{typeIcon(e.type)}</span>
              <span className="truncate max-w-[560px]">{e.summary}</span>
              <span className="text-ink-3 text-[11px]">({relativeTime(e.occurred_at)})</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
