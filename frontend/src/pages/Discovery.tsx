/**
 * Discovery — "AI Assistant First" narrative scroll redesign (D-0).
 *
 * spec: docs/superpowers/specs/2026-05-18-d0-ai-assistant-narrative-redesign.md
 *
 * 구조:
 *   §1 결정 (Sticky Hero)         ← StickyHero
 *   §2 왜 이 결정인가 (근거)        ← SignalContribution + PatternScoreLine mini + NewsTopList + OpecCitation
 *   §3 AI가 어떻게 추론했나 (★ wow) ← MultiAgentTrace + PatternScoreLine long (6년 평시 가치)
 *   §4 무엇을 할까 (액션)          ← Active missions + Backtest summary (Lakebase)
 *   §5 다른 가능성은 (대안)        ← PriceLineChart + FxLineChart + WhatIf link
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  useBacktestResults,
  useMissionsActive,
  usePatternCurrent,
  useSignalContribution,
} from "../lib/queries";
import { useMissionsWebSocket } from "../lib/ws";
import { formatPct, formatScore, relativeTime, termSpotLabel } from "../lib/utils";
import { MissionTypePill, StatusPill } from "../components/StatusPill";
import { StickyHero, type TriggerKind } from "../components/StickyHero";
import { MultiAgentTrace } from "../components/MultiAgentTrace";
import { SignalContribution } from "../components/SignalContribution";
import { PatternScoreLine } from "../components/PatternScoreLine";
import { OpecCitation } from "../components/OpecCitation";
import { PriceLineChart } from "../components/PriceLineChart";
import { NewsTopList } from "../components/NewsTopList";
import { FxLineChart } from "../components/FxLineChart";

export function Discovery() {
  const pattern = usePatternCurrent();
  const missions = useMissionsActive();
  const backtest = useBacktestResults();
  const signalContrib = useSignalContribution();

  const cur = pattern.data?.current ?? null;
  const activeMissions = missions.data?.missions || [];
  const topMission = activeMissions[0] ?? null;
  const topSignals = (signalContrib.data?.items ?? []).slice(0, 2);

  // Trigger badge state — MultiAgentTrace이 실행 중일 때 hero badge morph.
  const [triggerKind, setTriggerKind] = useState<TriggerKind>("daily_cron");

  // WebSocket subscription — reactive.alert event 수신 시 hero badge 30s pulse.
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
    <div className="-mt-8">
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* §1. 결정 — Sticky Hero                                       */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <StickyHero
        cur={cur}
        topMission={topMission}
        topSignals={topSignals}
        triggerKind={triggerKind}
        isLoading={pattern.isLoading}
      />

      <div className="max-w-5xl mx-auto pt-12">
        <SuperSectionHeader title="결정 근거" />

        <SignalContribution />

        {/* Pre-emptive momentum — Pattern score 30일 mini */}
        <PatternScoreLine days={30} variant="mini" />

        <OpecCitation />

        <NewsTopList limit={6} />

        {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
        {/* §3. AI가 어떻게 추론했나 — ★ Multi-Agent live trace          */}
        {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
        <SuperSectionHeader title="AI 추론 과정" />

        <MultiAgentTrace
          onTriggerStart={() => setTriggerKind("manual_query")}
          onTriggerEnd={() => setTriggerKind("manual_recommend")}
        />

        {/* Bidirectional Pattern context — 6년 평시 가치 */}
        <PatternScoreLine days={2200} variant="long" />

        {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
        {/* §4. 무엇을 할까 — 액션                                       */}
        {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
        <SuperSectionHeader title="실행 계획" />

        <section className="mb-10">
          <div className="flex items-baseline justify-between mb-3">
            <h3 className="font-display text-lg font-semibold">진행 중 임무</h3>
            <Link to="/missions" className="text-xs text-ink-3 hover:text-ink underline">
              전체 보기 →
            </Link>
          </div>
          {missions.isLoading && <div className="text-ink-3 text-sm">로딩 중...</div>}
          {activeMissions.length === 0 && !missions.isLoading && (
            <div className="bg-panel rounded-lg border border-line-1 p-6 text-ink-3 text-sm">
              진행 중 임무 없음. 위에서 다시 분석하면 새 임무가 제안됩니다.
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {activeMissions.slice(0, 4).map((m) => (
              <Link
                key={m.mission_id}
                to={`/missions/${m.mission_id}`}
                className="bg-panel rounded-lg border border-line-1 p-4 hover:border-ink-3 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex gap-2">
                    <MissionTypePill type={m.mission_type} />
                    <StatusPill status={m.status} />
                  </div>
                  <span className="text-[10px] font-mono text-ink-3">
                    v{m.version} · {relativeTime(m.created_at)}
                  </span>
                </div>
                <div className="font-medium text-ink mb-1 line-clamp-1">{m.goal_text}</div>
                <div className="text-xs text-ink-3 line-clamp-2">{m.reasoning}</div>
                <div className="mt-2 flex gap-4 text-[11px] font-mono text-ink-3">
                  <span>위기 신호 {formatScore(m.pattern_score)}</span>
                  {m.target_pct !== null && (
                    <span>{termSpotLabel(m.mission_type)} {m.target_pct}%</span>
                  )}
                  <span>{m.duration_days}일</span>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* Backtest Summary — Lakebase 라이브 outcome 추적 */}
        <section className="mb-10">
          <div className="flex items-baseline justify-between mb-3">
            <h3 className="font-display text-lg font-semibold">과거 권고 성과</h3>
            <Link to="/what-if" className="text-xs text-ink-3 hover:text-ink underline">
              과거 시점 복원 →
            </Link>
          </div>
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
                hint="30일 후 vs 평시 비중 대비"
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
              <div className="flex items-start gap-3">
                <span className="text-[10px] uppercase tracking-widest text-ink-3 mt-1 shrink-0">
                  데모 모드
                </span>
                <div className="flex-1">
                  <h4 className="font-display text-base font-semibold text-ink mb-1.5">
                    백테스트 데이터 연결 준비 중
                  </h4>
                  <p className="text-xs text-ink-2 leading-relaxed">
                    데이터베이스 연동이 완료되면 실시간으로 표시됩니다.
                    <Link to="/what-if" className="ml-1 text-ink underline">상세 →</Link>
                  </p>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
        {/* §5. 다른 가능성은 — 대안                                     */}
        {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
        <SuperSectionHeader title="대안 시나리오" />

        <PriceLineChart days={90} />
        <FxLineChart days={90} />

        <section className="mb-16 bg-panel border border-line-1 rounded-xl p-7">
          <div className="flex items-baseline justify-between mb-2">
            <h3 className="font-display text-lg font-semibold text-ink-1">시뮬레이션 도구</h3>
            <Link to="/what-if" className="text-xs text-ink-3 hover:text-ink-1 transition-colors">
              열기 →
            </Link>
          </div>
          <p className="text-sm text-ink-2 leading-relaxed">
            과거 시점으로 돌아가 AI 권고와 실제 결과를 비교하거나, 직접 질문하여 시나리오를 검토할 수 있습니다.
          </p>
        </section>
      </div>
    </div>
  );
}

function SuperSectionHeader({ title }: { title: string }) {
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
      : "text-ink";
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1">{label}</div>
      <div className={`font-display text-2xl font-semibold ${accentClass}`}>{value}</div>
      <div className="text-[11px] text-ink-3 font-mono mt-1">{hint}</div>
    </div>
  );
}
