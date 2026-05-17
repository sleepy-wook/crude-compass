import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  useBacktestResults,
  useMissionsActive,
  usePatternCurrent,
  useSignalContribution,
  queryKeys,
} from "../lib/queries";
import { api } from "../lib/api";
import { formatPct, formatScore, missionTypeLabel, relativeTime, termSpotLabel } from "../lib/utils";
import { MissionTypePill, StatusPill } from "../components/StatusPill";
import { Term } from "../components/Glossary";
import { SignalContribution } from "../components/SignalContribution";
import { PatternScoreLine } from "../components/PatternScoreLine";
import { OpecCitation } from "../components/OpecCitation";
import { PriceLineChart } from "../components/PriceLineChart";
import { NewsTopList } from "../components/NewsTopList";
import { FxLineChart } from "../components/FxLineChart";
import type { Mission, PatternScoreCurrent } from "../lib/types";

/** YYYY-MM-DD → "2026년 5월 15일 화요일" */
function formatKoreanDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const days = ["일", "월", "화", "수", "목", "금", "토"];
    return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일 ${days[d.getDay()]}요일`;
  } catch {
    return iso.slice(0, 10);
  }
}

const SIGNAL_LABEL_KO: Record<string, string> = {
  news_tone: "GDELT 뉴스 톤",
  eia_inventory: "EIA 미국 재고",
  opec_momr: "OPEC MOMR",
  fx_krw_usd: "USD/KRW 환율",
  price_spike: "유가 급변동",
};

/** 오늘의 권고 narrative — 평가위원이 0.5초에 추천 파악. */
function buildTodayDecision(
  cur: PatternScoreCurrent | null | undefined,
  activeMissions: Mission[],
): { tone: "crisis" | "opp" | "neutral"; text: string } | null {
  if (!cur) return null;
  const top = activeMissions[0];
  if (top) {
    if (top.mission_type === "HEDGE") {
      return {
        tone: "crisis",
        text: `장기계약 비중 60% → ${top.target_pct ?? "?"}% · ${top.duration_days}일`,
      };
    }
    return {
      tone: "opp",
      text: `즉시구매 비중 40% → ${top.target_pct ?? "?"}% · ${top.duration_days}일`,
    };
  }
  const score = cur.pattern_score ?? 50;
  if (score >= 70) {
    return { tone: "crisis", text: "위험방어 임무 제안 예상 — 추가 시그널 대기" };
  }
  if (score <= 30) {
    return { tone: "opp", text: "기회포착 임무 제안 예상 — 추가 시그널 대기" };
  }
  return { tone: "neutral", text: "관망 — 평시 매입 비중 유지" };
}

export function Discovery() {
  const pattern = usePatternCurrent();
  const missions = useMissionsActive();
  const backtest = useBacktestResults();
  const signalContrib = useSignalContribution();

  const cur = pattern.data?.current;
  const activeMissions = missions.data?.missions || [];
  const today = buildTodayDecision(cur, activeMissions);
  const qc = useQueryClient();
  const [recommendError, setRecommendError] = useState<string | null>(null);

  const recommendMut = useMutation({
    mutationFn: () =>
      api.missionRecommendNow({
        pattern_score: cur?.pattern_score ?? undefined,
        bullish_score: cur?.bullish_score ?? undefined,
        bearish_score: cur?.bearish_score ?? undefined,
      }),
    onSuccess: () => {
      setRecommendError(null);
      qc.invalidateQueries({ queryKey: queryKeys.missionsActive });
    },
    onError: (err: Error) => setRecommendError(err.message || "AI 호출 실패"),
  });

  const hedgeMission = activeMissions.find((m) => m.mission_type === "HEDGE");
  const oppMission = activeMissions.find((m) => m.mission_type === "OPPORTUNITY");
  const topSignal = signalContrib.data?.items?.[0];

  const scoreColor = cur?.pattern_score && cur.pattern_score >= 70
    ? "text-crisis-500"
    : cur?.pattern_score && cur.pattern_score <= 30
    ? "text-opportunity-500"
    : "text-ink";

  return (
    <div className="max-w-5xl mx-auto">
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* HERO — Editorial Korean Minimalist                          */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <header className="py-16 text-center border-b border-line-1 mb-12">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-3">
          K-Petroleum · {cur ? formatKoreanDate(cur.date) : "데이터 로딩"}
        </div>
        <h1 className="font-display text-4xl font-semibold tracking-tight mb-10">
          오늘의 결정
        </h1>

        {pattern.isLoading && (
          <div className="text-ink-3 text-sm">위기 신호 점수 계산 중...</div>
        )}
        {pattern.isError && (
          <div className="text-crisis-700 text-sm">데이터 연결 실패</div>
        )}

        {cur && (
          <>
            <div className="flex items-baseline justify-center gap-4 mb-4">
              <span className={`font-display text-7xl font-semibold ${scoreColor}`}>
                {formatScore(cur.pattern_score)}
              </span>
              <span className="text-2xl text-ink-2 font-display">
                {cur.mission_type ? missionTypeLabel(cur.mission_type) + " 강세" : "관망"}
              </span>
            </div>
            <div className="text-sm text-ink-3 mb-1">
              <Term name="PATTERN_SCORE" position="bottom">위기 신호</Term>{" "}
              {formatScore(cur.bullish_score)}
              <span className="mx-2 text-line-2">·</span>
              안정 신호 {formatScore(cur.bearish_score)}
            </div>
            <div className="text-sm text-ink-3 mb-8">
              신뢰도 {formatScore(cur.confidence_score)}%
              <span className="mx-2 text-line-2">·</span>
              90일 시그널 {cur.signal_count_90d ?? "—"}건
            </div>

            {today && (
              <div
                className={`inline-block px-6 py-4 rounded-lg border max-w-2xl ${
                  today.tone === "crisis"
                    ? "bg-crisis-50 border-crisis-100 text-crisis-700"
                    : today.tone === "opp"
                    ? "bg-opportunity-50 border-opportunity-100 text-opportunity-700"
                    : "bg-panel border-line-1 text-ink-2"
                }`}
              >
                <div className="text-[10px] uppercase tracking-widest opacity-70 mb-1">
                  AI 권고
                </div>
                <div className="text-base font-medium">{today.text}</div>
              </div>
            )}

            <div className="mt-6">
              <button
                type="button"
                onClick={() => recommendMut.mutate()}
                disabled={recommendMut.isPending}
                className="px-5 py-2.5 rounded-md bg-ink text-white text-xs font-medium hover:bg-ink-2 disabled:opacity-50 transition-colors"
                title="Databricks Foundation Model API (Claude Haiku) — 5-10초 cold start"
              >
                {recommendMut.isPending ? "AI 분석 중..." : "↻ 지금 새 권고 생성"}
              </button>
              {recommendError && (
                <div className="mt-3 text-xs text-crisis-700">
                  에러: {recommendError}
                </div>
              )}
              {recommendMut.isSuccess && recommendMut.data?.mission && (
                <div className="mt-3 text-xs text-opportunity-700">
                  새 임무 생성 — 신뢰도 {recommendMut.data.confidence_score?.toFixed(0)}/100
                </div>
              )}
            </div>
          </>
        )}
      </header>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* 5 CARDS — typography 중심, icon 없음                         */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <section className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-16">
        {/* 1. 위험방어 */}
        <SummaryCard
          eyebrow="위험방어"
          accent="crisis"
          primary={hedgeMission ? `+${maxRoi(hedgeMission)}억` : "대기"}
          secondary={
            hedgeMission && hedgeMission.target_pct !== null
              ? `장기계약 60→${hedgeMission.target_pct}%`
              : "위기 시그널 누적 시 자동 권고"
          }
          to="/missions"
        />
        {/* 2. 기회포착 */}
        <SummaryCard
          eyebrow="기회포착"
          accent="opp"
          primary={oppMission ? `+${maxRoi(oppMission)}억` : "대기"}
          secondary={
            oppMission && oppMission.target_pct !== null
              ? `즉시구매 40→${oppMission.target_pct}%`
              : "약세 시그널 누적 시 자동 권고"
          }
          to="/missions"
        />
        {/* 3. 실시간 알림 — top signal direction */}
        <SummaryCard
          eyebrow="실시간 알림"
          accent={topSignal?.direction === "bullish" ? "crisis" : topSignal?.direction === "bearish" ? "opp" : "ink"}
          primary={topSignal ? `${topSignal.share_pct.toFixed(1)}%` : "대기"}
          secondary={
            topSignal
              ? `${SIGNAL_LABEL_KO[topSignal.signal_type] ?? topSignal.signal_type} ${topSignal.direction === "bullish" ? "위기" : "약세"}`
              : "스파이크 모니터링 중"
          }
        />
        {/* 4. 신호 기여도 */}
        <SummaryCard
          eyebrow="신호 기여도"
          accent="ink"
          primary={signalContrib.data?.items?.length ? `${signalContrib.data.items.length}` : "—"}
          secondary="공개 6 소스 종합"
          to="#signal-contribution"
        />
        {/* 5. 진행 임무 */}
        <SummaryCard
          eyebrow="진행 임무"
          accent="ink"
          primary={`${activeMissions.length}건`}
          secondary={activeMissions.length > 0 ? "진행 중" : "임무 없음"}
          to="/missions"
        />
      </section>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* DETAIL (scroll) — 근거 시각화                                */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <div id="signal-contribution">
        <SignalContribution />
      </div>

      {/* 6년 평시 가치 — narrative 핵심 anchor */}
      <PatternScoreLine days={2200} variant="long" />

      {/* Pattern Score 30일 (mini) */}
      <PatternScoreLine days={30} variant="mini" />

      <OpecCitation />
      <PriceLineChart days={90} />
      <FxLineChart days={90} />
      <NewsTopList limit={12} />

      {/* Active Missions Summary (compact) */}
      <section className="mb-12">
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="font-display text-xl font-semibold">진행 중 임무</h2>
          <Link to="/missions" className="text-xs text-ink-3 hover:text-ink underline">
            전체 보기 →
          </Link>
        </div>
        {missions.isLoading && <div className="text-ink-3 text-sm">로딩 중...</div>}
        {activeMissions.length === 0 && !missions.isLoading && (
          <div className="bg-panel rounded-lg border border-line-1 p-6 text-ink-3 text-sm">
            진행 중 임무 없음
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

      {/* Backtest Summary — Lakebase 라이브 검증 anchor */}
      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="font-display text-xl font-semibold">백테스트 검증</h2>
          <Link to="/what-if" className="text-xs text-ink-3 hover:text-ink underline">
            과거 시점 복원 →
          </Link>
        </div>
        {backtest.data?.summary && (
          <div className="bg-panel rounded-xl border border-line-1 p-6 grid grid-cols-4 gap-4">
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
        {backtest.data && backtest.data.summary && (
          <div className="mt-3 inline-flex items-center gap-2 text-[11px] text-opportunity-700 font-mono">
            <span>● 라이브 Lakebase</span>
            <span className="text-ink-3">·</span>
            <span>run_id {backtest.data.summary.run_id}</span>
            <span className="text-ink-3">·</span>
            <span>psycopg3 pool · OAuth 토큰 50분 rotation</span>
          </div>
        )}
        {backtest.data && !backtest.data.summary && backtest.data.lakebase_available === false && (
          <div className="bg-panel rounded-xl border-2 border-dashed border-line-2 p-5">
            <div className="flex items-start gap-3">
              <span className="text-[10px] uppercase tracking-widest text-ink-3 mt-1 shrink-0">
                데모 모드
              </span>
              <div className="flex-1">
                <h3 className="font-display text-base font-semibold text-ink mb-1.5">
                  백테스트 데이터 — Lakebase OAuth 연동 진행 중
                </h3>
                <p className="text-xs text-ink-2 leading-relaxed">
                  Lakebase OLTP에 적재된 백테스트 결과는 Apps Database resource binding 완료 시 즉시 라이브.
                  <Link to="/what-if" className="ml-1 text-ink underline">상세 →</Link>
                </p>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

/** mission simulation_roi 중 최댓값 (억원) */
function maxRoi(m: Mission): number {
  const vals = Object.values(m.simulation_roi || {});
  if (vals.length === 0) return 0;
  return Math.max(...vals, 0);
}

interface SummaryCardProps {
  eyebrow: string;
  primary: string;
  secondary: string;
  accent: "crisis" | "opp" | "ink";
  to?: string;
}

function SummaryCard({ eyebrow, primary, secondary, accent, to }: SummaryCardProps) {
  const accentClass =
    accent === "crisis"
      ? "text-crisis-700"
      : accent === "opp"
      ? "text-opportunity-700"
      : "text-ink";
  const card = (
    <div className="bg-panel border border-line-1 rounded-xl px-4 py-5 h-full hover:border-ink-3 transition-colors">
      <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-2">
        {eyebrow}
      </div>
      <div className={`font-display text-2xl font-semibold ${accentClass} mb-1 truncate`}>
        {primary}
      </div>
      <div className="text-xs text-ink-3 leading-snug">{secondary}</div>
    </div>
  );
  if (to && to.startsWith("/")) {
    return <Link to={to}>{card}</Link>;
  }
  if (to && to.startsWith("#")) {
    return <a href={to}>{card}</a>;
  }
  return card;
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
      <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1">
        {label}
      </div>
      <div className={`font-display text-2xl font-semibold ${accentClass}`}>{value}</div>
      <div className="text-[11px] text-ink-3 font-mono mt-1">{hint}</div>
    </div>
  );
}
