/**
 * CaseThread — 한 case의 thread-style 활동 이력.
 *
 * AgentActivityTimeline의 "full" mode 대체. 차이점:
 *   - WebSocket 실시간 push (mission_id 일치하는 event)
 *   - Expand-to-raw (CaseThreadEntry)
 *   - chronological (오래된→최근, 위에서 아래로 누적)
 *   - 새 entry 도착 시 하단에 push + scroll-into-view animation
 */
import { useEffect, useMemo, useRef } from "react";
import { useMissionActivity } from "../lib/queries";
import { usePulseStream } from "../hooks/usePulseStream";
import { CaseThreadEntry } from "./CaseThreadEntry";
import type { ActivityEvent } from "./AgentActivityTimeline";

export function CaseThread({ missionId }: { missionId: string | undefined }) {
  const { data, isLoading, isError } = useMissionActivity(missionId);
  const { events: pulseEvents } = usePulseStream(50);
  const scrollRef = useRef<HTMLOListElement | null>(null);
  const lastCountRef = useRef(0);

  // REST events (per-mission) + WS events (filter to this mission)
  const merged = useMemo<ActivityEvent[]>(() => {
    const rest = data?.events ?? [];
    if (!missionId) return rest;
    const wsForCase = pulseEvents.filter((e) => e.mission_id === missionId);
    const seen = new Set<string>(rest.map((e) => String(e.id)));
    const extras = wsForCase.filter((e) => !seen.has(String(e.id)));
    const all = [...rest, ...extras];
    // chronological (oldest → newest)
    return all.sort((a, b) => a.occurred_at.localeCompare(b.occurred_at));
  }, [data?.events, pulseEvents, missionId]);

  // Auto-scroll on new entry
  useEffect(() => {
    if (merged.length > lastCountRef.current && scrollRef.current) {
      const el = scrollRef.current;
      el.scrollTop = el.scrollHeight;
    }
    lastCountRef.current = merged.length;
  }, [merged.length]);

  if (!missionId) return null;

  return (
    <section className="bg-white rounded-lg border border-line-2">
      <header className="px-4 py-3 border-b border-line-2 flex items-center justify-between">
        <div>
          <h3 className="text-[13px] font-semibold text-ink tracking-tight">Case Thread</h3>
          <p className="text-[10px] text-ink-3 mt-0.5">
            AI가 이 case에 한 일 · 실시간 누적 · {merged.length}건
          </p>
        </div>
      </header>
      <ol
        ref={scrollRef}
        className="relative px-4 py-3 max-h-[480px] overflow-y-auto"
      >
        <span aria-hidden className="absolute left-[21px] top-3 bottom-3 w-px bg-line-2" />
        {isLoading && (
          <li className="text-[11px] text-ink-3">불러오는 중...</li>
        )}
        {!isLoading && isError && (
          <li className="text-[11px] text-ink-3">불러올 수 없습니다</li>
        )}
        {!isLoading && !isError && merged.length === 0 && (
          <li className="text-[11px] text-ink-3">아직 활동이 없습니다</li>
        )}
        {merged.map((ev) => (
          <CaseThreadEntry key={ev.id} ev={ev} />
        ))}
      </ol>
    </section>
  );
}
