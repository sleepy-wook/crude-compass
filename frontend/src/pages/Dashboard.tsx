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
import { MissionSplitBar } from "../components/MissionSplitBar";
import { MissionTypePill, StatusPill } from "../components/StatusPill";
import { AgentActivityTimeline } from "../components/AgentActivityTimeline";
import { LivePulseStrip } from "../components/LivePulseStrip";
import { SuggestedNextActions } from "../components/SuggestedNextActions";
import type { Mission } from "../lib/types";

export function Dashboard() {
  const pattern = usePatternCurrent();
  const missions = useMissionsActive();

  const cur = pattern.data?.current ?? null;
  const activeMissions = missions.data?.missions || [];
  const topMission =
    activeMissions.find((m) => m.status === "proposed") ?? activeMissions[0] ?? null;
  // 현재 운영 중인 mission — 이전 active/on_track/at_risk 중 가장 최근 confirmed
  // 단, topMission 자기 자신은 제외 (같은 mission이 양쪽에 표시되는 버그 방지)
  const operatingMission =
    activeMissions
      .filter(
        (m) =>
          m.mission_id !== topMission?.mission_id &&
          ["active", "on_track", "at_risk"].includes(m.status),
      )
      .sort((a, b) =>
        (b.confirmed_at ?? b.created_at).localeCompare(a.confirmed_at ?? a.created_at),
      )[0] ?? null;

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
    <div className="max-w-6xl mx-auto px-8 py-10">
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* PAGE HEADER — enterprise SaaS 풍 짧은 카피                     */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <header className="mb-8 flex items-baseline justify-between flex-wrap gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-1.5">Decision Room</div>
          <h1 className="font-display text-[28px] md:text-[32px] font-semibold tracking-tight text-ink-1 leading-tight">
            오늘의 결정실 — 원유 조달 코파일럿
          </h1>
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
      {/* HERO ★ — Market Memory + Live AI Pulse                       */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3 mb-4">
        <div className="lg:col-span-3">
          <SimilarPastWidget cur={cur} />
        </div>
        <div className="lg:col-span-2">
          <LivePulseStrip />
        </div>
      </div>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* SIGNAL — Bidirectional + Mission 요약 (좌 360 / 우 1fr)        */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <SectionHeader
        title="오늘의 시그널"
        subtitle="양방향 강도 · 위험·기회 동시 추적"
      />
      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6 mb-10">
        <Bidirectional3Zone cur={cur} topMission={topMission} />
        <MissionSummaryCard
          mission={topMission}
          operatingMission={operatingMission}
          isLoading={pattern.isLoading || missions.isLoading}
        />
      </div>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* AGENT BRICKS 활동 — Supervisor orchestration timeline       */}
      {/* (Lakebase agent_activity_events) — codex P0 핵심 narrative   */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {topMission && (
        <>
          <SectionHeader
            title="Agent Bricks 활동"
            subtitle={`Supervisor · Genie · Knowledge Assistant · Mission Plan — 현재 ${
              topMission.status === "proposed" ? "검토 대기" : "진행 중"
            } case의 실시간 활동 기록`}
          />
          <AgentActivityTimeline
            missionId={topMission.mission_id}
            mode="compact"
            limit={6}
            showHeader={false}
          />
        </>
      )}

      <div className="h-12" />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// MissionSummaryCard — Dashboard mini ledger (full detail은 /missions)
// ────────────────────────────────────────────────────────────────────────
// 현재 운영 비중 helper — mission_type 따라 Term ratio 환산
function getCurrentTermPct(op: Mission | null): number {
  if (!op || op.target_pct == null) return 60;
  return op.mission_type === "HEDGE" ? op.target_pct : 100 - op.target_pct;
}

function MissionSummaryCard({
  mission,
  operatingMission,
  isLoading,
}: {
  mission: Mission | null;
  operatingMission: Mission | null;
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
      <div className="bg-panel border border-line-1 rounded-2xl p-6 min-h-[280px] flex flex-col justify-center">
        <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">Case File</div>
        <div className="text-base text-ink-1 mb-3">현재 열린 case 없음 — 평시 비중 유지</div>
        <p className="text-[13px] text-ink-3 leading-relaxed mb-5">
          시그널 조합이 평시 임계 안이라 Supervisor가 case를 열지 않았습니다. 과거 case 기록은
          Case File에서 확인할 수 있습니다.
        </p>
        <Link
          to="/missions"
          className="inline-flex items-center gap-1.5 text-[13px] font-medium text-ink-1 hover:text-ink-2 transition-colors"
        >
          Case File 보기 <span aria-hidden>→</span>
        </Link>
      </div>
    );
  }

  const isProposed = mission.status === "proposed";
  // baseline은 시나리오 §4 K-Petroleum default (Term 60 / Spot 40)으로 강제.
  // LLM goal_text가 50/40 같은 다른 baseline 명시해도 frontend에서 무시 (numbering inconsistency 방지).
  const target = mission.target_pct ?? (mission.mission_type === "HEDGE" ? 75 : 70);

  return (
    <div className="bg-panel border border-line-1 rounded-2xl p-6 flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <MissionTypePill type={mission.mission_type} />
        <StatusPill status={mission.status} />
        {mission.urgency === "urgent" && (
          <span className="text-[10px] uppercase tracking-wider bg-crisis-500 text-white px-2 py-0.5 rounded">
            긴급
          </span>
        )}
        <span className="ml-auto text-[10px] text-ink-3">
          {isProposed ? "Supervisor 권고 · 검토 대기" : "진행 중"}
        </span>
      </div>

      {/* Term/Spot 분할 시각화 — 현재 운영 vs AI 권고 비교 */}
      <div className="mb-5">
        <MissionSplitBar
          missionType={mission.mission_type}
          targetPct={target}
          currentTermPct={getCurrentTermPct(operatingMission)}
          currentSourceLabel={
            operatingMission
              ? `직전 운영 mission ${operatingMission.created_at.slice(0, 10)} 기록 기준`
              : "회사 평시 기준 (운영 history 없음)"
          }
          size="compact"
        />
      </div>

      <p className="text-[13px] text-ink-2 leading-relaxed mb-5 line-clamp-3">
        {mission.reasoning}
      </p>

      {/* Stat row — 빈 공간 채움 + 정보 dense */}
      <div className="grid grid-cols-3 gap-4 py-4 border-y border-line-1 mb-5">
        <MiniStat
          label="위기 강도"
          value={`${Math.round(mission.pattern_score / 10)}/10`}
          hint="양방향 가중 Pattern Score (0~100) ÷ 10 — Supervisor가 case open 결정한 1차 지표"
        />
        <MiniStat
          label="기간"
          value={`${mission.duration_days}일`}
          hint="Supervisor가 권고하는 비중 유지 기간 — 다음 review trigger까지"
        />
        <MiniStat
          label="시뮬레이션"
          value={`${Object.keys(mission.simulation_roi || {}).length}건`}
          hint="낙관 / 기본 / 비관 시나리오별 절감·손실 추정 (Brent 가격대별 ROI). Case File에서 detail."
        />
      </div>

      {/* 매니저의 다음 행동 — codex P0 SuggestedNextActions (6 agentic options) */}
      <div className="mb-5">
        <SuggestedNextActions mission={mission} compact />
      </div>

      <div className="mt-auto">
        <Link
          to={`/missions/${mission.mission_id}`}
          className="inline-flex items-center gap-1.5 text-[13px] font-medium text-ink-1 hover:text-ink-2 transition-colors"
        >
          상세 보기 (Case File) <span aria-hidden>→</span>
        </Link>
      </div>
    </div>
  );
}

function MiniStat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div title={hint} className={hint ? "cursor-help" : undefined}>
      <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1 flex items-center gap-1">
        {label}
        {hint && <span className="text-ink-3/60 text-[9px]" aria-hidden>ⓘ</span>}
      </div>
      <div className="font-display text-lg font-semibold text-ink-1 tabular-nums">{value}</div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// OspCycleChip — 매니저 결정 cycle 어디인지 한 줄 (시나리오 §1.2)
//   매월 5일경 Saudi Aramco OSP 발표 가정.
//   월초 (1-5일): OSP 발표 직후 — 이번 달 Term 적용 시점
//   월말 (25-31일): 다음 달 OSP 임박 — Term 갱신 cycle
//   월중 (6-24일): Spot 비중 조정 cycle
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
    <div className="mt-16 mb-6 pb-4 border-b border-line-1">
      <h2 className="font-display text-xl font-semibold text-ink-1 tracking-tight mb-0.5">
        {title}
      </h2>
      <p className="text-xs text-ink-3">{subtitle}</p>
    </div>
  );
}
