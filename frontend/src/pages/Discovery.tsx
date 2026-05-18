/**
 * Discovery — Single page "오늘의 결정" (D-0 mission-centric redesign).
 *
 * 3 page → 1 page 통합:
 *   Hero (Mission card)
 *   Zone 1 — 결정 근거 (AI 추론 trace + 신호 + 추세 + 보도)
 *   Zone 2 — 실행 추적 (active mission + 과거 권고 성과)
 *   Zone 3 — 탐색 (AI 어시스턴트 + 시장 추세 + 과거 검증)
 *
 * 우측 RightSidebar — K-Petroleum + 기술 스택 + 실시간 상태.
 */
import { useEffect, useRef, useState } from "react";
import {
  useBacktestResults,
  useMissionsActive,
  usePatternCurrent,
  useSignalContribution,
} from "../lib/queries";
import { useMissionsWebSocket } from "../lib/ws";
import { formatPct, formatScore, relativeTime, termSpotLabel } from "../lib/utils";
import { MissionTypePill, StatusPill } from "../components/StatusPill";
import { MissionHero, type TriggerKind } from "../components/MissionHero";
import { MultiAgentTrace } from "../components/MultiAgentTrace";
import { SignalContribution } from "../components/SignalContribution";
import { PatternScoreLine } from "../components/PatternScoreLine";
import { OpecCitation } from "../components/OpecCitation";
import { PriceLineChart } from "../components/PriceLineChart";
import { NewsTopList } from "../components/NewsTopList";
import { FxLineChart } from "../components/FxLineChart";
import { SupervisorChat } from "../components/SupervisorChat";
import { BacktestTimeSlider } from "../components/BacktestTimeSlider";

export function Discovery() {
  const pattern = usePatternCurrent();
  const missions = useMissionsActive();
  const backtest = useBacktestResults();
  const signalContrib = useSignalContribution();

  const cur = pattern.data?.current ?? null;
  const activeMissions = missions.data?.missions || [];
  // Hero에 표시할 mission 우선순위: proposed > active > 없음
  const topMission =
    activeMissions.find((m) => m.status === "proposed") ??
    activeMissions[0] ??
    null;
  // Hero에 노출되지 않는 나머지 mission들
  const otherMissions = topMission
    ? activeMissions.filter((m) => m.mission_id !== topMission.mission_id)
    : activeMissions;
  const topSignals = (signalContrib.data?.items ?? []).slice(0, 2);

  // Trigger badge state
  const [triggerKind, setTriggerKind] = useState<TriggerKind>("daily_cron");
  const traceSectionRef = useRef<HTMLDivElement | null>(null);

  // WebSocket subscribe — reactive.alert event 수신 시 hero badge 30s pulse
  const { lastEvent, lastEventAt } = useMissionsWebSocket();
  useEffect(() => {
    if (!lastEvent || !lastEventAt) return;
    if (lastEvent.type === "reactive.alert") {
      setTriggerKind("price_spike");
      const timer = window.setTimeout(() => setTriggerKind("daily_cron"), 30_000);
      return () => window.clearTimeout(timer);
    }
  }, [lastEvent, lastEventAt]);

  function scrollToTrace() {
    traceSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="max-w-4xl">
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* HERO — Mission card (오늘 권고)                              */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <MissionHero
        cur={cur}
        topMission={topMission}
        topSignals={topSignals}
        triggerKind={triggerKind}
        isLoading={pattern.isLoading}
        onRequestAnalysis={scrollToTrace}
      />

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* ZONE 1 — 결정 근거                                            */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <ZoneHeader title="결정 근거" />

      <div ref={traceSectionRef}>
        <MultiAgentTrace
          onTriggerStart={() => setTriggerKind("manual_query")}
          onTriggerEnd={() => setTriggerKind("manual_recommend")}
        />
      </div>

      <SignalContribution />

      <PatternScoreLine days={30} variant="mini" />

      <OpecCitation />

      <NewsTopList limit={6} />

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* ZONE 2 — 실행 추적                                            */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <ZoneHeader title="실행 추적" />

      {/* 6년 평시 가치 — narrative context */}
      <PatternScoreLine days={2200} variant="long" />

      {/* 다른 진행 중 임무 (Hero에 안 들어간 것들) */}
      {otherMissions.length > 0 && (
        <section className="mb-10">
          <h3 className="font-display text-lg font-semibold text-ink-1 mb-4">
            다른 진행 임무
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {otherMissions.slice(0, 4).map((m) => (
              <div
                key={m.mission_id}
                className="bg-panel rounded-lg border border-line-1 p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex gap-2">
                    <MissionTypePill type={m.mission_type} />
                    <StatusPill status={m.status} />
                  </div>
                  <span className="text-[11px] text-ink-3">
                    {relativeTime(m.created_at)}
                  </span>
                </div>
                <div className="font-medium text-ink-1 mb-1 line-clamp-1">{m.goal_text}</div>
                <div className="text-xs text-ink-3 line-clamp-2">{m.reasoning}</div>
                <div className="mt-2 flex gap-4 text-[11px] text-ink-3">
                  <span>위기 {formatScore(m.pattern_score)}</span>
                  {m.target_pct !== null && (
                    <span>
                      {termSpotLabel(m.mission_type)} {m.target_pct}%
                    </span>
                  )}
                  <span>{m.duration_days}일</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 과거 권고 성과 */}
      <section className="mb-10">
        <h3 className="font-display text-lg font-semibold text-ink-1 mb-4">
          과거 권고 성과
        </h3>
        {backtest.data?.summary && (
          <div className="bg-panel rounded-xl border border-line-1 p-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat
              label="AI 권고 적중률"
              value={formatPct(backtest.data.summary.hit_rate_pct)}
              hint={`${backtest.data.summary.n_active}건 검증`}
              accent="ok"
            />
            <Stat
              label="평균 비용 절감"
              value={formatPct(backtest.data.summary.avg_save_pct, 2)}
              hint="30일 기준"
              accent="ok"
            />
            <Stat
              label="위험방어 권고"
              value={`${backtest.data.summary.n_hedge}건`}
              hint="장기계약 상향"
              accent="crisis"
            />
            <Stat
              label="기회포착 권고"
              value={`${backtest.data.summary.n_opp}건`}
              hint="즉시구매 상향"
              accent="opp"
            />
          </div>
        )}
        {backtest.data?.summary && (
          <div className="mt-3 inline-flex items-center gap-2 text-[11px] text-ink-3">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-opportunity-500" />
            <span>실시간 데이터 연결됨</span>
          </div>
        )}
        {backtest.data && !backtest.data.summary && backtest.data.lakebase_available === false && (
          <div className="bg-panel rounded-xl border-2 border-dashed border-line-2 p-5">
            <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-2">데모 모드</div>
            <h4 className="font-display text-base font-semibold text-ink-1 mb-1.5">
              실시간 데이터 연결 준비 중
            </h4>
            <p className="text-xs text-ink-2 leading-relaxed">
              데이터베이스 연동이 완료되면 실시간으로 검증 결과가 표시됩니다.
            </p>
          </div>
        )}
      </section>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* ZONE 3 — 탐색                                                  */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <ZoneHeader title="탐색" />

      <SupervisorChat />

      <PriceLineChart days={90} />
      <FxLineChart days={90} />

      <BacktestTimeSlider />

      <div className="h-20" />
    </div>
  );
}

function ZoneHeader({ title }: { title: string }) {
  return (
    <div className="mt-24 mb-8">
      <h2 className="font-display text-2xl md:text-[28px] font-semibold tracking-tight text-ink-1">
        {title}
      </h2>
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint: string;
  accent?: "ok" | "crisis" | "opp";
}) {
  const accentClass =
    accent === "ok"
      ? "text-opportunity-700"
      : accent === "crisis"
        ? "text-crisis-700"
        : accent === "opp"
          ? "text-opportunity-700"
          : "text-ink-1";
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1">{label}</div>
      <div className={`font-display text-2xl font-semibold ${accentClass}`}>{value}</div>
      <div className="text-[11px] text-ink-3 mt-1">{hint}</div>
    </div>
  );
}
