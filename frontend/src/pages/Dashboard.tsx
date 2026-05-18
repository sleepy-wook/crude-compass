/**
 * Dashboard — 오늘의 결정 (/).
 *
 * 슬림화: 차트는 /market으로, AI Ask는 /ask로, Mission detail은 /missions로 분리.
 * 첫 페이지는 hero (Market Memory) + Bidirectional + Mission 한 줄 요약만 노출.
 *
 * 시나리오 정합:
 *   §2 평시 가치 narrative
 *   §3 Open Data Democratization (Track 1)
 *   §6 Bidirectional Pattern (3-zone)
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useMissionsActive, usePatternCurrent } from "../lib/queries";
import { useMissionsWebSocket } from "../lib/ws";
import { Bidirectional3Zone } from "../components/Bidirectional3Zone";
import { SimilarPastWidget } from "../components/SimilarPastWidget";
import { MissionTypePill, StatusPill } from "../components/StatusPill";
import type { Mission } from "../lib/types";

export function Dashboard() {
  const pattern = usePatternCurrent();
  const missions = useMissionsActive();

  const cur = pattern.data?.current ?? null;
  const activeMissions = missions.data?.missions || [];
  const topMission =
    activeMissions.find((m) => m.status === "proposed") ?? activeMissions[0] ?? null;

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
    <div className="max-w-7xl mx-auto px-8 py-10">
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* PAGE HEADER — enterprise SaaS 풍 짧은 카피                     */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <header className="mb-10">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-2">오늘의 결정</div>
        <h1 className="font-display text-[28px] md:text-[32px] font-semibold tracking-tight text-ink-1 mb-3 leading-tight">
          원유 조달 의사결정 코파일럿
        </h1>
        <p className="text-sm text-ink-2 leading-relaxed max-w-2xl">
          공개 데이터 기반 일일 시그널 · 7년 시장 메모리 · 매니저 결정 기록.
        </p>
        {spikeFlash && (
          <div className="mt-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-crisis-50 text-crisis-700 text-[12px] font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-crisis-500 animate-pulse" />
            실시간 위기 신호 감지 — 30초 내 자동 갱신
          </div>
        )}
      </header>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* HERO ★ — Market Memory                                       */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <SimilarPastWidget cur={cur} />

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* SIGNAL — Bidirectional + Mission 요약 (좌 360 / 우 1fr)        */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <SectionHeader
        title="오늘의 시그널"
        subtitle="양방향 강도 · 위험·기회 동시 추적"
      />
      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6 mb-10">
        <Bidirectional3Zone cur={cur} topMission={topMission} />
        <MissionSummaryCard mission={topMission} isLoading={pattern.isLoading || missions.isLoading} />
      </div>

      <div className="h-12" />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// MissionSummaryCard — Dashboard mini ledger (full detail은 /missions)
// ────────────────────────────────────────────────────────────────────────
function MissionSummaryCard({
  mission,
  isLoading,
}: {
  mission: Mission | null;
  isLoading?: boolean;
}) {
  if (isLoading) {
    return (
      <div className="bg-panel border border-line-1 rounded-2xl p-8 flex items-center text-sm text-ink-3">
        불러오는 중...
      </div>
    );
  }

  if (!mission) {
    return (
      <div className="bg-panel border border-line-1 rounded-2xl p-8">
        <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">매니저 결정 기록</div>
        <div className="text-base text-ink-1 mb-3">현재 AI 권고 없음 — 평시 비중 유지</div>
        <p className="text-[13px] text-ink-3 leading-relaxed mb-5">
          시그널 조합이 평시 임계 안에 있어 별도 권고를 생성하지 않았습니다. 매니저 결정 기록은
          별도 페이지에서 확인할 수 있습니다.
        </p>
        <Link
          to="/missions"
          className="inline-flex items-center gap-1.5 text-[13px] font-medium text-ink-1 hover:text-ink-2 transition-colors"
        >
          내 결정 기록 보기 <span aria-hidden>→</span>
        </Link>
      </div>
    );
  }

  const isProposed = mission.status === "proposed";
  const baseline = mission.mission_type === "HEDGE" ? 60 : 40;
  const target = mission.target_pct ?? baseline;
  const action = mission.mission_type === "HEDGE" ? "장기 비중" : "즉시 비중";

  return (
    <div className="bg-panel border border-line-1 rounded-2xl p-8 flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <MissionTypePill type={mission.mission_type} />
        <StatusPill status={mission.status} />
        {mission.urgency === "urgent" && (
          <span className="text-[10px] uppercase tracking-wider bg-crisis-500 text-white px-2 py-0.5 rounded">
            긴급
          </span>
        )}
        <span className="ml-auto text-[10px] text-ink-3">
          {isProposed ? "AI 검토 권한" : "진행 중"}
        </span>
      </div>

      <div className="text-[13px] text-ink-3 mb-2">
        오늘 {action} <span className="text-ink-3/70">· 평시 {baseline}%</span>
      </div>
      <div className="font-display text-[36px] font-semibold tracking-tight leading-[1.1] text-ink-1 mb-4">
        {baseline}% <span className="text-ink-3 mx-2">→</span> {target}%
      </div>

      <p className="text-[13px] text-ink-2 leading-relaxed mb-6 line-clamp-3">
        {mission.reasoning}
      </p>

      <div className="mt-auto pt-5 border-t border-line-1">
        <Link
          to={`/missions/${mission.mission_id}`}
          className="inline-flex items-center gap-1.5 text-[13px] font-medium text-ink-1 hover:text-ink-2 transition-colors"
        >
          내 결정으로 기록하기 <span aria-hidden>→</span>
        </Link>
      </div>
    </div>
  );
}

function SectionHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mt-20 mb-6 pb-4 border-b border-line-1">
      <h2 className="font-display text-xl font-semibold text-ink-1 tracking-tight mb-0.5">
        {title}
      </h2>
      <p className="text-xs text-ink-3">{subtitle}</p>
    </div>
  );
}
