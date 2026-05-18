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

        {/* OSP cycle chip — 매니저 결정 cycle 어디인지 한 줄 */}
        <OspCycleChip />

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
  // baseline은 시나리오 §4 K-Petroleum default (Term 60 / Spot 40)으로 강제.
  // LLM goal_text가 50/40 같은 다른 baseline 명시해도 frontend에서 무시 (numbering inconsistency 방지).
  const target = mission.target_pct ?? (mission.mission_type === "HEDGE" ? 75 : 70);

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
          {isProposed ? "AI 권고 · 검토 대기" : "진행 중"}
        </span>
      </div>

      {/* Term/Spot 분할 시각화 — 해커톤 1등 demo killer fix */}
      <div className="mb-5">
        <MissionSplitBar
          missionType={mission.mission_type}
          targetPct={target}
          size="compact"
        />
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
    phase = "이번 달 OSP 발표 직후 — Term 계약 가격 적용 시점";
    daysToNext = lastDay - day + 5; // 다음 달 5일까지
  } else if (day >= 25) {
    phase = "다음 달 OSP 임박 — Term 갱신 검토 cycle";
    daysToNext = lastDay - day + 5;
    tone = "crisis";
  } else {
    phase = "월중 — Spot 비중 미세 조정 cycle";
    daysToNext = lastDay - day + 5;
  }

  const toneCls =
    tone === "crisis"
      ? "border-crisis-100 bg-crisis-50 text-crisis-700"
      : "border-line-2 bg-line-1 text-ink-2";

  return (
    <div
      className={`mt-4 inline-flex items-baseline gap-2 px-3 py-1.5 rounded-md border text-[12px] ${toneCls}`}
    >
      <span className="text-[10px] uppercase tracking-wider opacity-75">OSP cycle</span>
      <span className="font-medium">{phase}</span>
      <span className="opacity-75 tabular-nums">· 다음 Aramco OSP D-{daysToNext}</span>
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
