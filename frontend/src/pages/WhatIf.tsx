import { useState, useMemo } from "react";
import { useMutation } from "@tanstack/react-query";
import { useBacktestPredictions, useBacktestResults } from "../lib/queries";
import { MissionTypePill } from "../components/StatusPill";
import { Term } from "../components/Glossary";
import { api } from "../lib/api";
import type { SupervisorQueryResponse } from "../lib/types";
import { formatPct, formatScore, formatUsd } from "../lib/utils";

const SUPERVISOR_EXAMPLES = [
  "오늘 위기 점수 어디서 왔고 추천도 알려줘",
  "OPEC 5월 사우디 감산 근거는?",
  "최근 OPEC 사우디 공급 수치 보여줘",
  "두바이유 7일 momentum + 매입 비중 추천",
];

const SUBAGENT_LABEL: Record<string, { label: string; color: string }> = {
  // Sub-agent name 패턴 매칭 (Supervisor가 반환하는 tool name)
  genie: { label: "Genie SQL", color: "bg-blue-50 text-blue-700 border-blue-200" },
  knowledge: { label: "Knowledge Assistant", color: "bg-purple-50 text-purple-700 border-purple-200" },
  ka: { label: "Knowledge Assistant", color: "bg-purple-50 text-purple-700 border-purple-200" },
  haiku: { label: "Mission Plan (Claude Haiku)", color: "bg-green-50 text-green-700 border-green-200" },
  claude: { label: "Mission Plan (Claude Haiku)", color: "bg-green-50 text-green-700 border-green-200" },
};

function labelSubAgent(name: string): { label: string; color: string } {
  const lower = name.toLowerCase();
  for (const [key, val] of Object.entries(SUBAGENT_LABEL)) {
    if (lower.includes(key)) return val;
  }
  return { label: name, color: "bg-line-1 text-ink-2 border-line-2" };
}

export function WhatIf() {
  const preds = useBacktestPredictions(300);
  const summary = useBacktestResults();

  // Supervisor Agent widget state — Multi-Agent orchestration (Genie + KA + FMA Mission Plan)
  const [supervisorQuestion, setSupervisorQuestion] = useState("");
  const [supervisorResp, setSupervisorResp] = useState<SupervisorQueryResponse | null>(null);

  const supervisorMut = useMutation({
    mutationFn: ({ question }: { question: string }) => api.supervisorQuery(question),
    onSuccess: (res) => setSupervisorResp(res),
  });

  const submitSupervisor = () => {
    const q = supervisorQuestion.trim();
    if (q.length < 2) return;
    supervisorMut.mutate({ question: q });
  };

  // Sort by date asc for slider — preds.data가 바뀔 때만 재계산
  const sorted = useMemo(() => {
    const list = preds.data?.predictions || [];
    return [...list].sort((a, b) => a.as_of_date.localeCompare(b.as_of_date));
  }, [preds.data]);

  // Slider state — 사용자가 움직이면 setIdx로 override. idx === null이면 sorted[-1] 자동 사용.
  const [idx, setIdx] = useState<number | null>(null);
  const effectiveIdx = idx ?? (sorted.length > 0 ? sorted.length - 1 : null);
  const current = effectiveIdx === null ? undefined : sorted[effectiveIdx];

  return (
    <div className="max-w-6xl mx-auto">
      <header className="mb-6">
        <h1 className="font-display text-3xl font-semibold">
          과거 시점 복원 + AI 추천 검증
        </h1>
        <p className="text-sm text-ink-2 mt-2 max-w-3xl">
          데이터: 2019-2026 사이 300개 시점 · 슬라이더로 과거 임의 시점 선택 → AI가
          <strong> 그 시점 데이터만 보고 추천한 결정</strong>과 실제 30/90일 후 가격 비교.
        </p>
      </header>

      {/* Backtest summary card */}
      {summary.data?.summary && (
        <section className="mb-6 bg-panel rounded-xl border border-line-1 p-6 grid grid-cols-5 gap-4">
          <Stat label="총 샘플" value={`${summary.data.summary.n_active}건`} />
          <Stat
            label="적중률"
            value={formatPct(summary.data.summary.hit_rate_pct)}
            accent="ok"
          />
          <Stat
            label="평균 비용 절감"
            value={formatPct(summary.data.summary.avg_save_pct, 2)}
            accent="ok"
          />
          <Stat label="HEDGE" value={`${summary.data.summary.n_hedge}건`} accent="crisis" />
          <Stat label="OPP" value={`${summary.data.summary.n_opp}건`} accent="opp" />
        </section>
      )}

      {/* Time travel slider */}
      <section className="mb-6 bg-panel rounded-xl border border-line-1 p-6">
        <div className="flex items-baseline justify-between mb-2">
          <h2 className="text-xs uppercase tracking-widest text-ink-3">
            시점 선택 ({sorted.length}개 중)
          </h2>
          <span className="text-xs font-mono text-ink-3">
            {sorted[0]?.as_of_date} → {sorted[sorted.length - 1]?.as_of_date}
          </span>
        </div>
        <p className="text-xs text-ink-3 mb-4 leading-relaxed">
          이 backtest는 4 source × 7년 (GDELT / EIA / OPEC / FX + Dubai 종가).
          <strong className="text-ink-2"> OilPriceAPI는 realtime-only이라 production 전용</strong> — backtest 데이터 자체가 없음.
        </p>

        {sorted.length > 0 && (
          <>
            <input
              type="range"
              min={0}
              max={sorted.length - 1}
              value={effectiveIdx ?? 0}
              onChange={(e) => setIdx(Number(e.target.value))}
              className="w-full mb-3 accent-crisis-500"
            />
            {/* Zone legend — slider 자체에 띠 추가 대신 명료한 인라인 legend */}
            <div className="flex items-center justify-center gap-4 text-[11px] text-ink-3 mb-4">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-crisis-500" /> 위기 (70+)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-ink-4" /> 관망 (30~70)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-opportunity-500" /> 기회 (~30)
              </span>
            </div>
            <div className="text-center mb-6">
              <div className="text-xs text-ink-3 mb-1">선택된 시점</div>
              <div className="font-display text-2xl font-semibold flex items-center justify-center gap-3">
                {current?.as_of_date}
                {current && current.pattern_score != null && (() => {
                  const ps = current.pattern_score;
                  return (
                    <span
                      className={
                        ps >= 70
                          ? "text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-crisis-50 text-crisis-700 border border-crisis-100"
                          : ps <= 30
                          ? "text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-opportunity-50 text-opportunity-700 border border-opportunity-100"
                          : "text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-line-1 text-ink-3 border border-line-2"
                      }
                    >
                      {ps >= 70 ? "위기" : ps <= 30 ? "기회" : "관망"}
                    </span>
                  );
                })()}
              </div>
            </div>
          </>
        )}

        {current && (
          <div className="border-t border-line-1 pt-5 grid grid-cols-3 gap-6">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-2">
                AI 추천 (그 날짜)
              </div>
              <div className="flex items-center gap-2 mb-1">
                {current.mission_type && <MissionTypePill type={current.mission_type} />}
                <span className="text-xs text-ink-3">
                  <Term name="PATTERN_SCORE" position="bottom">위기점수</Term>{" "}
                  {formatScore(current.pattern_score)}
                </span>
              </div>
              <div className="text-sm font-medium">
                {current.action_type === "new_mission"
                  ? `${current.mission_type === "HEDGE" ? "Term" : "Spot"} ${current.target_pct}% (${current.duration_days}일)`
                  : "관망 (대기)"}
              </div>
              <div className="text-xs text-ink-3 mt-1">
                자신감 {formatScore(current.confidence_score)}
              </div>
            </div>

            <div>
              <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-2">
                Dubai유 가격 (그 날짜 → 30일 후)
              </div>
              <div className="text-2xl font-display font-semibold">
                {formatUsd(current.dubai_at_signal_usd)} →{" "}
                {formatUsd(current.dubai_30d_usd)}
              </div>
              <div className="text-xs text-ink-3 mt-1">
                30일 변동{" "}
                {current.dubai_at_signal_usd && current.dubai_30d_usd
                  ? formatPct(
                      ((current.dubai_30d_usd - current.dubai_at_signal_usd) /
                        current.dubai_at_signal_usd) *
                        100,
                      2
                    )
                  : "—"}
              </div>
            </div>

            <div>
              <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-2">
                AI 추천 따랐을 때 절감률
              </div>
              <div className="grid grid-cols-3 gap-2">
                <Outcome label="7일" value={current.saving_7d_pct} />
                <Outcome label="30일" value={current.saving_30d_pct} />
                <Outcome label="90일" value={current.saving_90d_pct} />
              </div>
              <div className="text-[11px] text-ink-3 mt-2">
                양수 = 평시(Term 60 / Spot 40) 대비 절감 (좋음)
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Sample list */}
      <section className="bg-panel rounded-xl border border-line-1 p-6">
        <h2 className="text-xs uppercase tracking-widest text-ink-3 mb-3">
          최근 30개 AI 추천 (Backtest sample · 클릭 시 슬라이더 이동)
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-widest text-ink-3 border-b border-line-1">
                <th className="py-2">날짜</th>
                <th>추천</th>
                <th>위기점수</th>
                <th>자신감</th>
                <th>목표</th>
                <th>30일 절감</th>
              </tr>
            </thead>
            <tbody>
              {sorted.slice(-30).reverse().map((p, i) => (
                <tr
                  key={`${p.as_of_date}-${i}`}
                  onClick={() =>
                    setIdx(sorted.findIndex((x) => x.as_of_date === p.as_of_date))
                  }
                  className="border-b border-line-1 cursor-pointer hover:bg-paper"
                >
                  <td className="py-2 font-mono text-xs">{p.as_of_date}</td>
                  <td>
                    {p.mission_type && <MissionTypePill type={p.mission_type} />}
                  </td>
                  <td className="font-mono text-xs">{formatScore(p.pattern_score)}</td>
                  <td className="font-mono text-xs">{formatScore(p.confidence_score)}</td>
                  <td className="font-mono text-xs">{p.target_pct ?? "—"}%</td>
                  <td
                    className={`font-mono text-xs ${
                      (p.saving_30d_pct || 0) > 0
                        ? "text-opportunity-700"
                        : (p.saving_30d_pct || 0) < 0
                        ? "text-crisis-700"
                        : "text-ink-3"
                    }`}
                  >
                    {formatPct(p.saving_30d_pct, 2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Agent Bricks Supervisor — Multi-Agent orchestration (시나리오 §9.7 anchor) */}
      <section className="mt-6 bg-panel rounded-xl border border-line-1 p-6">
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="font-display text-lg font-semibold text-ink">
            AI 어시스턴트 (Supervisor)
          </h2>
          <span className="text-[11px] text-ink-3">
            Agent Bricks · 3 sub-agent (Genie · KA · FMA) 자동 라우팅
          </span>
        </div>
        <p className="text-xs text-ink-3 mb-4 leading-relaxed">
          자연어 질의 1개 → Supervisor가 적절한 sub-agent에 자동 delegate.
          응답 하단에 <code className="px-1 py-0.5 bg-line-1 rounded text-[10px]">사용된 sub-agent</code> 표시 (transparency).
        </p>

        {/* Example chips */}
        <div className="flex flex-wrap gap-2 mb-3">
          {SUPERVISOR_EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setSupervisorQuestion(ex)}
              className="text-xs px-3 py-1.5 rounded-full border border-line-2 text-ink-2 hover:bg-line-1 hover:border-ink-3 transition-colors"
            >
              {ex}
            </button>
          ))}
        </div>

        {/* Textarea */}
        <textarea
          value={supervisorQuestion}
          onChange={(e) => setSupervisorQuestion(e.target.value)}
          placeholder="자유 입력 (예: 오늘 매입 비중 어떻게 조정?)"
          rows={2}
          className="w-full text-sm p-3 border border-line-2 rounded-md focus:outline-none focus:border-ink-3 mb-3"
        />
        <div className="flex items-center justify-between mb-4">
          <button
            type="button"
            onClick={submitSupervisor}
            disabled={supervisorMut.isPending || supervisorQuestion.trim().length < 2}
            className="px-4 py-2 rounded-md bg-ink text-white text-sm font-medium hover:bg-ink-2 disabled:opacity-50 transition-colors"
          >
            {supervisorMut.isPending ? "Supervisor 호출 중..." : "질문하기"}
          </button>
          {supervisorResp && (
            <button
              type="button"
              onClick={() => {
                setSupervisorResp(null);
                setSupervisorQuestion("");
              }}
              className="text-xs text-ink-3 hover:text-ink underline"
            >
              새 질의
            </button>
          )}
        </div>

        {/* Response area */}
        {supervisorMut.isError && (
          <div className="text-xs text-crisis-700 mb-3">
            에러: {(supervisorMut.error as Error)?.message || "Supervisor 호출 실패"}
          </div>
        )}
        {supervisorResp && (
          <div className="border-t border-line-1 pt-4 mt-2">
            {/* Source badge */}
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              <span
                className={
                  supervisorResp.source === "live"
                    ? "text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-opportunity-50 text-opportunity-700 border border-opportunity-100"
                    : "text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-line-1 text-ink-2 border border-line-2"
                }
                title={
                  supervisorResp.source === "live"
                    ? "Agent Bricks Supervisor 라이브 호출"
                    : "Supervisor endpoint 미등록 — Genie fallback 모드"
                }
              >
                {supervisorResp.source === "live" ? "● Live Supervisor" : `● Fallback`}
              </span>
              {supervisorResp.source === "fallback" && supervisorResp.fallback_genie_source && (
                <span className="text-[10px] font-mono text-ink-3">
                  via {supervisorResp.fallback_genie_source}
                </span>
              )}
            </div>

            {/* Answer */}
            <p className="text-sm text-ink leading-relaxed whitespace-pre-wrap mb-3">
              {supervisorResp.answer}
            </p>

            {/* Tools used (Supervisor sub-agent routing trace) */}
            {supervisorResp.tools_used && supervisorResp.tools_used.length > 0 && (
              <div className="border-t border-line-1 pt-3 mt-3">
                <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-2">
                  사용된 sub-agent ({supervisorResp.tools_used.length})
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {supervisorResp.tools_used.map((t, i) => {
                    const { label, color } = labelSubAgent(t.name);
                    return (
                      <span
                        key={`${t.name}-${i}`}
                        className={`text-[11px] px-2 py-0.5 rounded-full border ${color}`}
                        title={t.arguments || t.name}
                      >
                        {label}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Fallback path data (Genie SQL transparency) */}
            {supervisorResp.source === "fallback" &&
              supervisorResp.fallback_data &&
              supervisorResp.fallback_data.length > 0 && (
                <div className="overflow-x-auto bg-paper rounded-md border border-line-1 mt-3">
                  <table className="w-full text-xs">
                    <thead className="bg-line-1">
                      <tr>
                        {Object.keys(supervisorResp.fallback_data[0]).map((k) => (
                          <th key={k} className="py-2 px-3 text-left font-mono text-ink-3">
                            {k}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {supervisorResp.fallback_data.slice(0, 5).map((row, ri) => (
                        <tr key={ri} className="border-t border-line-1">
                          {Object.values(row).map((v, ci) => (
                            <td key={ci} className="py-1.5 px-3 font-mono">
                              {String(v)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
          </div>
        )}
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "ok" | "crisis" | "opp";
}) {
  const cls =
    accent === "ok" || accent === "opp"
      ? "text-opportunity-700"
      : accent === "crisis"
      ? "text-crisis-700"
      : "text-ink";
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1">{label}</div>
      <div className={`font-display text-xl font-semibold ${cls}`}>{value}</div>
    </div>
  );
}

function Outcome({ label, value }: { label: string; value: number | null | undefined }) {
  const positive = (value || 0) > 0;
  const negative = (value || 0) < 0;
  return (
    <div className="text-center border border-line-1 rounded-md p-2">
      <div className="text-[10px] text-ink-3">{label}</div>
      <div
        className={`text-sm font-mono ${
          positive ? "text-opportunity-700" : negative ? "text-crisis-700" : "text-ink-3"
        }`}
      >
        {formatPct(value, 2)}
      </div>
    </div>
  );
}
