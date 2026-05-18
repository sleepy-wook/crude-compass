/**
 * Dashboard — 오늘의 결정 (/).
 * Hero (Mission card 또는 관망) + KPI strip + 신호 분석 grid + 시계열.
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
import { SignalContribution } from "../components/SignalContribution";
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
      {/* Page intro */}
      <header className="mb-10">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-2">
          오늘의 결정
        </div>
        <h1 className="font-display text-[28px] md:text-[32px] font-semibold tracking-tight text-ink-1 mb-2 leading-tight">
          AI가 분석한 오늘의 매입 권고
        </h1>
        <p className="text-sm text-ink-2 leading-relaxed max-w-2xl">
          매일 시장 신호를 종합해 두바이/WTI 매입 비중을 권고합니다. 권고는 Apps와 Slack 어느 쪽에서든 채택할 수 있습니다.
        </p>
      </header>

      {/* Hero — Mission card */}
      <MissionHero
        cur={cur}
        topMission={topMission}
        topSignals={topSignals}
        triggerKind={triggerKind}
        isLoading={pattern.isLoading}
      />

      {/* 신호 분석 grid */}
      <SectionHeader title="신호 분석" subtitle="권고의 근거가 된 시장 신호" />
      <SignalContribution />
      <PatternScoreLine days={30} variant="mini" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
        <OpecCitation />
        <NewsTopList limit={5} />
      </div>

      {/* 시장 추세 */}
      <SectionHeader title="시장 추세" subtitle="가격·환율 추이" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
        <PriceLineChart days={90} />
        <FxLineChart days={90} />
      </div>

      {/* 6년 평시 가치 */}
      <SectionHeader title="장기 추세" subtitle="6년 위기 점수 시계열" />
      <PatternScoreLine days={2200} variant="long" />

      {/* AI 추론 trace (선택적 reveal) */}
      <SectionHeader title="AI 추론 과정" subtitle="이번 권고가 만들어진 단계별 추론" />
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
