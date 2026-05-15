import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  useBacktestResults,
  useMissionsActive,
  usePatternCurrent,
  queryKeys,
} from "../lib/queries";
import { api } from "../lib/api";
import { formatPct, formatScore, missionTypeLabel, relativeTime } from "../lib/utils";
import { MissionTypePill, StatusPill } from "../components/StatusPill";
import { Term } from "../components/Glossary";
import { FleetLifecycleSection } from "../components/FleetLifecycleSection";
import { HormuzMap } from "../components/HormuzMap";
import { SignalContribution } from "../components/SignalContribution";
import { PatternScoreLine } from "../components/PatternScoreLine";
import { OpecCitation } from "../components/OpecCitation";
import { PriceLineChart } from "../components/PriceLineChart";
import { NewsTopList } from "../components/NewsTopList";
import { FxLineChart } from "../components/FxLineChart";
import type { Mission, PatternScoreCurrent } from "../lib/types";


/** 오늘의 1줄 의사결정 narrative — 평가위원이 0.5초에 추천 파악. */
function buildTodayDecision(
  cur: PatternScoreCurrent | null | undefined,
  activeMissions: Mission[],
): { tone: "crisis" | "opp" | "neutral"; text: string } | null {
  if (!cur) return null;
  // 활성 mission 있으면 그 추천 사용
  const top = activeMissions[0];
  if (top) {
    if (top.mission_type === "HEDGE") {
      return {
        tone: "crisis",
        text: `오늘은 위험방어 강세 (위기 신호 ${cur.pattern_score?.toFixed(0) ?? "?"}점). 추천: 장기계약(Term) 60→${top.target_pct ?? "?"}% · ${top.duration_days}일`,
      };
    }
    return {
      tone: "opp",
      text: `오늘은 기회포착 강세 (위기 신호 ${cur.pattern_score?.toFixed(0) ?? "?"}점). 추천: 즉시구매(Spot) 40→${top.target_pct ?? "?"}% · ${top.duration_days}일`,
    };
  }
  // 활성 mission 없으면 score 기반 fallback
  const score = cur.pattern_score ?? 50;
  if (score >= 70) {
    return {
      tone: "crisis",
      text: `오늘은 위험 신호 누적 (위기 신호 ${score.toFixed(0)}점). 추천: 곧 위험방어(HEDGE) Mission 제안 예상 — 추가 시그널 대기`,
    };
  }
  if (score <= 30) {
    return {
      tone: "opp",
      text: `오늘은 약세 신호 누적 (위기 신호 ${score.toFixed(0)}점). 추천: 곧 기회포착(OPP) Mission 제안 예상 — 추가 시그널 대기`,
    };
  }
  return {
    tone: "neutral",
    text: `오늘은 관망 (위기 신호 ${score.toFixed(0)}점). 평시 매입비중 유지 — 추가 시그널 누적 중`,
  };
}

export function Discovery() {
  const pattern = usePatternCurrent();
  const missions = useMissionsActive();
  const backtest = useBacktestResults();

  const cur = pattern.data?.current;
  const activeMissions = missions.data?.missions || [];
  const today = buildTodayDecision(cur, activeMissions);
  const qc = useQueryClient();
  const [recommendError, setRecommendError] = useState<string | null>(null);

  // '지금 새 추천 생성' — Mission Plan Agent 라이브 호출 (5-10s cold start)
  const recommendMut = useMutation({
    mutationFn: () =>
      api.missionRecommendNow({
        pattern_score: cur?.pattern_score ?? undefined,
        bullish_score: cur?.bullish_score ?? undefined,
        bearish_score: cur?.bearish_score ?? undefined,
      }),
    onSuccess: () => {
      setRecommendError(null);
      // WS event로 자동 update되지만, fallback으로 명시적 invalidate
      qc.invalidateQueries({ queryKey: queryKeys.missionsActive });
    },
    onError: (err: Error) => setRecommendError(err.message || "LLM 호출 실패"),
  });

  return (
    <div className="max-w-6xl mx-auto">
      {/* Hero — 오늘의 위기 신호 점수 */}
      <header className="mb-6">
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          오늘의 발견
        </h1>
        <p className="text-sm text-ink-3 mt-1">
          공개 데이터 7개 종합 · AI가 오늘 매입 비중을 추천합니다
        </p>
      </header>

      {/* 오늘의 1줄 의사결정 — 평가위원 narrative 즉시 이해 */}
      {today && (
        <section className="mb-6">
          <div
            className={
              today.tone === "crisis"
                ? "bg-crisis-50 border border-crisis-100 text-crisis-700 rounded-lg px-5 py-4 flex items-start justify-between gap-4"
                : today.tone === "opp"
                ? "bg-opportunity-50 border border-opportunity-100 text-opportunity-700 rounded-lg px-5 py-4 flex items-start justify-between gap-4"
                : "bg-panel border border-line-1 text-ink-2 rounded-lg px-5 py-4 flex items-start justify-between gap-4"
            }
          >
            <div className="flex-1">
              <div className="text-[10px] uppercase tracking-widest opacity-70 mb-1">
                오늘의 1줄 의사결정
              </div>
              <div className="text-base font-medium leading-relaxed">{today.text}</div>
            </div>
            {/* Mission Plan Agent 라이브 호출 버튼 — 평가위원 앞에서 LLM 시연 */}
            <button
              type="button"
              onClick={() => recommendMut.mutate()}
              disabled={recommendMut.isPending}
              className="shrink-0 px-4 py-2 rounded-md bg-ink text-white text-xs font-medium hover:bg-ink-2 disabled:opacity-50 transition-colors whitespace-nowrap"
              title="Databricks Foundation Model API (Claude Haiku) — 5-10초 cold start"
            >
              {recommendMut.isPending ? "AI 분석 중..." : "지금 새 추천 생성"}
            </button>
          </div>
          {recommendError && (
            <div className="mt-2 text-xs text-crisis-700">
              에러: {recommendError}
            </div>
          )}
          {recommendMut.data && recommendMut.data.action !== "new_mission" && (
            <div className="mt-2 text-xs text-ink-3">
              AI 응답: action={recommendMut.data.action} (현재 시그널 상 새 mission 권고 X)
              · LLM={recommendMut.data.llm_endpoint}
            </div>
          )}
          {recommendMut.isSuccess && recommendMut.data?.mission && (
            <div className="mt-2 text-xs text-opportunity-700">
              새 Mission 생성: {recommendMut.data.mission.goal_text} (신뢰도 {recommendMut.data.confidence_score?.toFixed(0)}/100)
              · 진행 중 미션 목록 자동 update.
            </div>
          )}
        </section>
      )}

      {/* Pattern Score Card (가장 큰 wow — 평가위원 첫 0.5초 grab) */}
      <section className="mb-8">
        {pattern.isLoading && (
          <div className="bg-panel rounded-xl border border-line-1 p-8">
            <div className="text-ink-3">Pattern Score 로딩 중...</div>
          </div>
        )}
        {pattern.isError && (
          <div className="bg-panel rounded-xl border border-line-1 p-6">
            <div className="text-crisis-700 text-sm">Backend 연결 실패. uvicorn 실행 확인.</div>
          </div>
        )}
        {cur && (
          <div className="bg-panel rounded-xl border border-line-1 p-8 grid grid-cols-3 gap-8">
            <div>
              <div className="text-xs text-ink-3 mb-2">
                <Term name="PATTERN_SCORE" position="bottom">위기 신호 점수</Term>
              </div>
              <div
                className={`font-display text-6xl font-semibold ${
                  cur.pattern_score && cur.pattern_score >= 70
                    ? "text-crisis-500"
                    : cur.pattern_score && cur.pattern_score <= 30
                    ? "text-opportunity-500"
                    : "text-ink"
                }`}
              >
                {formatScore(cur.pattern_score)}
              </div>
              <div className="text-xs text-ink-3 mt-2 font-mono">{cur.date}</div>
            </div>

            <div className="border-l border-line-1 pl-8">
              <div className="text-xs uppercase tracking-widest text-ink-3 mb-2">
                현재 추천
              </div>
              <div className="font-display text-2xl font-semibold mb-2">
                {cur.mission_type
                  ? missionTypeLabel(cur.mission_type)
                  : "관망 (대기)"}
              </div>
              <div className="text-xs text-ink-3 font-mono">
                위기 신호 {formatScore(cur.bullish_score)} · 안정 신호{" "}
                {formatScore(cur.bearish_score)}
              </div>
            </div>

            <div className="border-l border-line-1 pl-8">
              <div className="text-xs uppercase tracking-widest text-ink-3 mb-2">
                AI 자신감
              </div>
              <div className="font-display text-2xl font-semibold mb-2">
                {formatScore(cur.confidence_score)}
                <span className="text-base font-normal text-ink-3 ml-1">/100</span>
              </div>
              <div className="text-xs text-ink-3 font-mono">
                90일 시그널 {cur.signal_count_90d ?? "—"}건
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Pattern Score 30일 line (Pattern Card 바로 옆 — 점수 추이 즉시 확인) */}
      <PatternScoreLine days={30} variant="mini" />

      {/* HormuzMap — 호르무즈 narrative anchor (시나리오 §14 Phase 3 핵심) */}
      <HormuzMap />

      {/* Signal Contribution — 점수 근거 시각화 (시나리오 §6.3 #2) */}
      <SignalContribution />

      {/* K-Petroleum 5척 lifecycle (시나리오 §4) */}
      <FleetLifecycleSection />

      {/* OPEC MOMR citation — Document Intelligence wow (§9.6) */}
      <OpecCitation />

      {/* Dubai/Brent/WTI 가격 라인 — 시나리오 §7 #4 anchor */}
      <PriceLineChart days={90} />

      {/* USD/KRW 환율 — 시나리오 §7 #5 + §13 랜딩 코스트 anchor */}
      <FxLineChart days={90} />

      {/* 최근 7일 핵심 뉴스 — 시나리오 §6.3 #3 anchor */}
      <NewsTopList limit={12} />

      {/* 6년 평시 가치 long chart — 시나리오 §14 Phase 7 마지막 wow anchor */}
      <PatternScoreLine days={2200} variant="long" />

      {/* Active Missions Summary */}
      <section className="mb-8">
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="font-display text-xl font-semibold">진행 중 미션</h2>
          <Link to="/missions" className="text-xs text-ink-3 hover:text-ink underline">
            전체 보기 →
          </Link>
        </div>
        {missions.isLoading && (
          <div className="text-ink-3 text-sm">로딩 중...</div>
        )}
        {activeMissions.length === 0 && !missions.isLoading && (
          <div className="bg-panel rounded-lg border border-line-1 p-6 text-ink-3 text-sm">
            진행 중 미션 없음
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
                <span>위기점수 {formatScore(m.pattern_score)}</span>
                {m.target_pct !== null && (
                  <span>
                    {m.mission_type === "HEDGE" ? "Term" : "Spot"} {m.target_pct}%
                  </span>
                )}
                <span>{m.duration_days}일</span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Backtest Summary */}
      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="font-display text-xl font-semibold">백테스트 검증</h2>
          <Link to="/what-if" className="text-xs text-ink-3 hover:text-ink underline">
            What-if 시뮬레이션 →
          </Link>
        </div>
        {backtest.data?.summary && (
          <div className="bg-panel rounded-xl border border-line-1 p-6 grid grid-cols-4 gap-4">
            <Stat
              label="AI 추천 적중률"
              value={formatPct(backtest.data.summary.hit_rate_pct)}
              hint={`${backtest.data.summary.n_active}건 검증`}
              accent="ok"
            />
            <Stat
              label="평균 비용 절감"
              value={formatPct(backtest.data.summary.avg_save_pct, 2)}
              hint="30일 후 vs 평시(Term 60 / Spot 40) 대비"
              accent="ok"
            />
            <Stat
              label="위험방어 권고"
              value={`${backtest.data.summary.n_hedge}건`}
              hint="장기계약(Term) ↑"
              accent="crisis"
            />
            <Stat
              label="기회포착 권고"
              value={`${backtest.data.summary.n_opp}건`}
              hint="즉시구매(Spot) ↑"
              accent="opp"
            />
          </div>
        )}
      </section>
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
      <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1">
        {label}
      </div>
      <div className={`font-display text-2xl font-semibold ${accentClass}`}>{value}</div>
      <div className="text-[11px] text-ink-3 font-mono mt-1">{hint}</div>
    </div>
  );
}
