/**
 * Dashboard — 오늘의 결정 (/).
 *
 * 시나리오 정합:
 *   §2 평시 가치 narrative (Opportunity가 더 자주 가치)
 *   §3 Open Data Democratization (Track 1)
 *   §6 Bidirectional Pattern (3-zone)
 *   §6.5 시간 지평 차별화 (Leading/Macro/Fundamentals)
 */
import { useEffect, useState } from "react";
import {
  useMissionsActive,
  usePatternCurrent,
  useSignalContribution,
} from "../lib/queries";
import { useMissionsWebSocket } from "../lib/ws";
import { MissionHero, type TriggerKind } from "../components/MissionHero";
import { MultiAgentTrace } from "../components/MultiAgentTrace";
import { Bidirectional3Zone } from "../components/Bidirectional3Zone";
import { SimilarPastWidget } from "../components/SimilarPastWidget";
import { TimeHorizonBreakdown } from "../components/TimeHorizonBreakdown";
import { OpenDataBadge } from "../components/OpenDataBadge";
import { PatternScoreLine } from "../components/PatternScoreLine";
import { OpecCitation } from "../components/OpecCitation";
import { PriceLineChart } from "../components/PriceLineChart";
import { NewsTopList } from "../components/NewsTopList";
import { FxLineChart } from "../components/FxLineChart";

export function Dashboard() {
  const pattern = usePatternCurrent();
  const missions = useMissionsActive();
  const signalContrib = useSignalContribution();

  const cur = pattern.data?.current ?? null;
  const activeMissions = missions.data?.missions || [];
  const topMission =
    activeMissions.find((m) => m.status === "proposed") ?? activeMissions[0] ?? null;
  const topSignals = (signalContrib.data?.items ?? []).slice(0, 2);

  const [triggerKind, setTriggerKind] = useState<TriggerKind>("daily_cron");

  const { lastEvent, lastEventAt } = useMissionsWebSocket();
  useEffect(() => {
    if (!lastEvent || !lastEventAt) return;
    if (lastEvent.type === "reactive.alert") {
      setTriggerKind("price_spike");
      const timer = window.setTimeout(() => setTriggerKind("daily_cron"), 30_000);
      return () => window.clearTimeout(timer);
    }
  }, [lastEvent, lastEventAt]);

  return (
    <div className="max-w-7xl mx-auto px-8 py-10">
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* PAGE INTRO — 평시 가치 narrative (시나리오 §2)                 */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <header className="mb-10">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-2">
          오늘의 결정
        </div>
        <h1 className="font-display text-[28px] md:text-[32px] font-semibold tracking-tight text-ink-1 mb-3 leading-tight">
          한국 정유사 원유 조달 코파일럿
        </h1>
        <p className="text-sm text-ink-2 leading-relaxed max-w-2xl">
          평시 매주 발생하는 시그널을 종합해 텀 계약과 스팟 매입의 비중을 미세 조정합니다.
          호르무즈 같은 큰 위기 한 번이 아니라,{" "}
          <span className="text-ink-1 font-medium">
            매월 가장 싸게 사는 일상 도구
          </span>
          입니다.
        </p>
      </header>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* HERO ★ — Market Memory (오늘 시그널 → 지난 7년 비슷한 패턴 outcome) */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <SimilarPastWidget cur={cur} />

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* SIGNAL OVERVIEW — 좌(Bidirectional 3-zone) + 우(Mission)     */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <SectionHeader title="시그널 강도 + 결정 기록" subtitle="양방향 신호 + 매니저 행동 ledger" />
      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6 mb-10">
        <Bidirectional3Zone cur={cur} topMission={topMission} />
        <MissionHero
          cur={cur}
          topMission={topMission}
          topSignals={topSignals}
          triggerKind={triggerKind}
          isLoading={pattern.isLoading}
        />
      </div>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* WHY — 시간 지평별 근거 (시나리오 §6.5)                       */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <SectionHeader title="이번 권고의 근거" subtitle="시간 지평별 신호 분류" />
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 mb-10">
        <TimeHorizonBreakdown />
        <div className="space-y-4">
          <PatternScoreLine days={30} variant="mini" />
        </div>
      </div>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* OPEN DATA TRACK 1 — Bloomberg 대신 무료 6 source              */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <SectionHeader title="Track 1 · Open Data" subtitle="유료 인텔리전스를 무료로" />
      <OpenDataBadge />

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* SIGNAL DETAILS — 4개 source visualize                       */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <SectionHeader title="시그널 상세" subtitle="4개 source 실시간 종합" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
        <OpecCitation />
        <NewsTopList limit={5} />
      </div>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* MARKET TRENDS                                                */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <SectionHeader title="시장 추세" subtitle="가격 · 환율 90일" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
        <PriceLineChart days={90} />
        <FxLineChart days={90} />
      </div>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* 6년 평시 가치 — 시나리오 §14 Phase 7                          */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <SectionHeader
        title="6년 위기 점수 추이"
        subtitle="1년 1-2 위기 + 분기 1-2 기회 + 매주 미세 조정"
      />
      <PatternScoreLine days={2200} variant="long" />

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* AI 추론 trace (★ wow)                                        */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <SectionHeader
        title="AI 추론 과정"
        subtitle="Multi-Agent — Supervisor + 데이터 조회 + 뉴스 분석 + 권고 산출"
      />
      <MultiAgentTrace
        onTriggerStart={() => setTriggerKind("manual_query")}
        onTriggerEnd={() => setTriggerKind("manual_recommend")}
      />

      <div className="h-20" />
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
