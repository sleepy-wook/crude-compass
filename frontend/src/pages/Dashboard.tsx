/**
 * Dashboard — Decision Room (/).
 *
 * Phase 2 재배치:
 *   [Header — eyebrow | OSP D-N | spike?]
 *   [DeltaStrip — events>0 일 때만]
 *   [Hero grid 12-col — 5 ActionQueue | 7 SelectedCaseDetail]
 *   [Bidirectional3Zone — full width]
 *   [MonitoringStrip — 1-line each, dense]
 *   [Market Memory]
 *
 * AI 활동 section 제거. (LivePulseStrip / DailyLoopClock / AgentActivityTimeline 컴포넌트
 * 자체는 다른 페이지가 쓸 수 있으므로 삭제 X — Dashboard에서만 import 제거.)
 */
import { useEffect, useMemo, useState } from "react";
import { useDecisionQueue, usePatternCurrent } from "../lib/queries";
import { useMissionsWebSocket } from "../lib/ws";
import { Bidirectional3Zone } from "../components/Bidirectional3Zone";
import { SimilarPastWidget } from "../components/SimilarPastWidget";
import { ActionQueue } from "../components/ActionQueue";
import { SelectedCaseDetail } from "../components/SelectedCaseDetail";
import { MonitoringStrip } from "../components/MonitoringStrip";

export function Dashboard() {
  const queue = useDecisionQueue();
  const pattern = usePatternCurrent();
  const [selectedCaseId, setSelectedCaseId] = useState<string | undefined>(undefined);

  const cur = pattern.data?.current ?? null;
  const needsYou = queue.data?.needs_you ?? [];
  const monitoring = queue.data?.monitoring ?? [];

  const selectedCase = useMemo(() => {
    const all = [...needsYou, ...monitoring];
    if (selectedCaseId) {
      const found = all.find((m) => m.mission_id === selectedCaseId);
      if (found) return found;
    }
    return needsYou[0] ?? monitoring[0] ?? null;
  }, [needsYou, monitoring, selectedCaseId]);

  // 현재 운영 중인 mission — split bar baseline 산출에 사용 (자기 자신 제외)
  const operatingMission = useMemo(() => {
    return (
      monitoring.find(
        (m) =>
          m.mission_id !== selectedCase?.mission_id &&
          (m.status === "active" || m.status === "on_track"),
      ) ?? null
    );
  }, [monitoring, selectedCase?.mission_id]);

  // Reactive trigger flash (위기 spike alert)
  const [spikeFlash, setSpikeFlash] = useState(false);
  const { lastEvent, lastEventAt } = useMissionsWebSocket();
  useEffect(() => {
    if (!lastEvent || !lastEventAt) return;
    if (lastEvent.type === "reactive.alert") {
      setSpikeFlash(true);
      const timer = window.setTimeout(() => setSpikeFlash(false), 30_000);
      return () => window.clearTimeout(timer);
    }
  }, [lastEvent, lastEventAt]);

  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* PAGE HEADER                                                  */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <header className="mb-6 flex items-baseline justify-between flex-wrap gap-3">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3">
          Decision Room
        </div>
        <OspCycleChip />

        {spikeFlash && (
          <div className="w-full inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-crisis-50 text-crisis-700 text-[12px] font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-crisis-500 animate-pulse" />
            실시간 위기 신호 감지 — 30초 내 자동 갱신
          </div>
        )}
      </header>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* HERO grid — 5 ActionQueue | 7 SelectedCaseDetail            */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-10">
        <div className="lg:col-span-5">
          <ActionQueue
            cases={needsYou}
            selectedId={selectedCase?.mission_id}
            onSelect={setSelectedCaseId}
          />
        </div>
        <div className="lg:col-span-7">
          <SelectedCaseDetail
            mission={selectedCase}
            operatingMission={operatingMission}
            isLoading={queue.data === undefined}
          />
        </div>
      </div>

      {/* SIGNAL STRENGTH — Bidirectional full width supporting context */}
      <SectionHeader title="Signal Strength" subtitle="위기 ↔ 기회 (0–100, 90일)" />
      <Bidirectional3Zone cur={cur} topMission={selectedCase} />

      {/* MONITORING — active/on_track/paused */}
      <SectionHeader
        title="진행 중인 작업"
        subtitle={`승인 후 운영 중인 case ${monitoring.length}건`}
      />
      <MonitoringStrip cases={monitoring} />

      {/* MARKET MEMORY */}
      <SectionHeader title="Market Memory" subtitle="7년 backtest analog" />
      <SimilarPastWidget cur={cur} />

      <div className="h-12" />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// OspCycleChip — 매니저 결정 cycle 어디인지 한 줄 (시나리오 §1.2)
// ────────────────────────────────────────────────────────────────────────
function OspCycleChip() {
  const today = new Date();
  const day = today.getDate();
  const month = today.getMonth();
  const year = today.getFullYear();
  const lastDay = new Date(year, month + 1, 0).getDate();

  let phase: string;
  let daysToNext: number;
  let tone: "crisis" | "ink" = "ink";

  if (day <= 5) {
    phase = "OSP 발표 직후";
    daysToNext = lastDay - day + 5;
  } else if (day >= 25) {
    phase = "Term 갱신 임박";
    daysToNext = lastDay - day + 5;
    tone = "crisis";
  } else {
    phase = "월중 Spot 조정";
    daysToNext = lastDay - day + 5;
  }

  const toneCls =
    tone === "crisis"
      ? "border-crisis-100 bg-crisis-50 text-crisis-700"
      : "border-line-2 bg-line-1 text-ink-2";

  return (
    <div
      className={`inline-flex items-baseline gap-2 px-3 py-1.5 rounded-md border text-[12px] ${toneCls}`}
    >
      <span className="font-medium">{phase}</span>
      <span className="opacity-75 tabular-nums">· OSP D-{daysToNext}</span>
    </div>
  );
}

function SectionHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mt-12 mb-5 pb-3 border-b border-line-1">
      <h2 className="font-display text-lg font-semibold text-ink-1 tracking-tight mb-0.5">
        {title}
      </h2>
      {subtitle && <p className="text-xs text-ink-3">{subtitle}</p>}
    </div>
  );
}
