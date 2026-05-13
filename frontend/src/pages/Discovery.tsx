import { Link } from "react-router-dom";
import {
  useBacktestResults,
  useMissionsActive,
  usePatternCurrent,
} from "../lib/queries";
import { formatPct, formatScore, missionTypeLabel, relativeTime } from "../lib/utils";
import { MissionTypePill, StatusPill } from "../components/StatusPill";

export function Discovery() {
  const pattern = usePatternCurrent();
  const missions = useMissionsActive();
  const backtest = useBacktestResults();

  const cur = pattern.data?.current;
  const activeMissions = missions.data?.missions || [];

  return (
    <div className="max-w-6xl mx-auto">
      {/* Hero — 오늘의 Pattern Score */}
      <header className="mb-8">
        <div className="text-xs uppercase tracking-widest text-ink-3 mb-1">
          Today · Pre-emptive Decision Support
        </div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          오늘의 발견
        </h1>
      </header>

      {/* Pattern Score Card */}
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
              <div className="text-xs uppercase tracking-widest text-ink-3 mb-2">
                Pattern Score
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
                  : "관망 (STAY)"}
              </div>
              <div className="text-xs text-ink-3 font-mono">
                bullish {formatScore(cur.bullish_score)} · bearish{" "}
                {formatScore(cur.bearish_score)}
              </div>
            </div>

            <div className="border-l border-line-1 pl-8">
              <div className="text-xs uppercase tracking-widest text-ink-3 mb-2">
                AI Confidence
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
                <span>PS {formatScore(m.pattern_score)}</span>
                {m.target_pct !== null && <span>target {m.target_pct}%</span>}
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
              hint="30일 후 vs 기본 mix"
              accent="ok"
            />
            <Stat
              label="HEDGE 권고"
              value={`${backtest.data.summary.n_hedge}건`}
              hint="위험 방어"
              accent="crisis"
            />
            <Stat
              label="OPP 권고"
              value={`${backtest.data.summary.n_opp}건`}
              hint="기회 포착"
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
