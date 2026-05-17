/**
 * MultiAgentTrace — §3 wow anchor.
 *
 * spec: docs/superpowers/specs/2026-05-18-d0-ai-assistant-narrative-redesign.md §5
 *
 * Supervisor query POST 응답은 한 번에 옴 (`tools_used: SubAgentCall[]`).
 * Client에서 staggered animation으로 "AI agent가 실시간으로 일하는" 느낌 fake.
 *
 * Demo safety:
 *  - mutation 실패 시 cached lastTrace replay (visual 동일, "캐시" badge 추가)
 *  - timeout 90s 후 동일 fallback
 *
 * State:
 *  - idle (page load)
 *  - running (mutation 진행 중 + staggered animation)
 *  - completed (full trace + footer)
 *  - error → fallback to cached
 */
import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { SubAgentCall, SupervisorQueryResponse } from "../lib/types";

const SUPERVISOR_PROMPT = "현재 시그널 종합 분석하고 최적 mission을 추천해줘";

type AgentKey = "supervisor" | "genie" | "knowledge_assistant" | "mission_plan_fma";

interface StepSpec {
  key: AgentKey;
  label: string;
  defaultQuery: string;
  defaultResponse: string;
  /** ms after start to begin */
  startAt: number;
  /** ms after start to complete */
  completeAt: number;
}

const TRACE_STEPS: StepSpec[] = [
  {
    key: "supervisor",
    label: "Supervisor 시작",
    defaultQuery: "Multi-Agent fan-out 시작",
    defaultResponse: "3 sub-agent 호출",
    startAt: 200,
    completeAt: 400,
  },
  {
    key: "genie",
    label: "Genie Space 호출 중...",
    defaultQuery: "WTI/두바이 30일 평균 대비 spike 여부, EIA 재고 변화",
    defaultResponse: "WTI +5.2%, 재고 -3.1MB",
    startAt: 600,
    completeAt: 2700,
  },
  {
    key: "knowledge_assistant",
    label: "Knowledge Assistant 호출 중...",
    defaultQuery: "호르무즈 해협 긴장 관련 기사 분석",
    defaultResponse: "7건 retrieve, 평균 tone -0.82",
    startAt: 2900,
    completeAt: 4700,
  },
  {
    key: "mission_plan_fma",
    label: "Mission Plan FMA 호출 중...",
    defaultQuery: "입력: pattern_score=78, bullish=4, bearish=1",
    defaultResponse: "결정: HEDGE pivot 60% → 75%",
    startAt: 4900,
    completeAt: 9200,
  },
];

const TOTAL_DURATION_MS = 9400;

type StepStatus = "pending" | "running" | "completed";

interface RenderedStep extends StepSpec {
  status: StepStatus;
  /** SubAgentCall에서 받은 실제 데이터 */
  query?: string;
  response?: string;
  elapsedMs?: number;
}

function mapSubAgentToKey(name: string): AgentKey | null {
  const lower = name.toLowerCase();
  if (lower.includes("genie")) return "genie";
  if (lower.includes("knowledge") || lower.includes("ka")) return "knowledge_assistant";
  if (lower.includes("haiku") || lower.includes("claude") || lower.includes("mission_plan") || lower.includes("fma"))
    return "mission_plan_fma";
  return null;
}

/** SubAgentCall[] → AgentKey 별 매핑. */
function indexCalls(calls: SubAgentCall[]): Partial<Record<AgentKey, SubAgentCall>> {
  const idx: Partial<Record<AgentKey, SubAgentCall>> = {};
  for (const c of calls) {
    const k = mapSubAgentToKey(c.name);
    if (k && !idx[k]) idx[k] = c;
  }
  return idx;
}

interface MultiAgentTraceProps {
  onTriggerStart?: () => void;
  onTriggerEnd?: () => void;
}

export function MultiAgentTrace({ onTriggerStart, onTriggerEnd }: MultiAgentTraceProps) {
  const [elapsed, setElapsed] = useState(0);
  const [running, setRunning] = useState(false);
  const [cachedResponse, setCachedResponse] = useState<SupervisorQueryResponse | null>(null);
  const [usedCache, setUsedCache] = useState(false);
  const startedAtRef = useRef<number | null>(null);
  const tickRef = useRef<number | null>(null);

  const mutation = useMutation({
    mutationFn: () => api.supervisorQuery(SUPERVISOR_PROMPT),
    onSuccess: (data) => {
      setCachedResponse(data);
      setUsedCache(false);
    },
    onError: () => {
      // cache replay (demo safety)
      if (cachedResponse) {
        setUsedCache(true);
      }
    },
  });

  const isCompleted = !running && elapsed >= TOTAL_DURATION_MS && (mutation.isSuccess || cachedResponse);
  const hasFatalError = mutation.isError && !cachedResponse && elapsed >= TOTAL_DURATION_MS;

  // Animation tick (60fps not needed — 100ms is plenty)
  useEffect(() => {
    if (!running) return;
    function tick() {
      if (startedAtRef.current == null) return;
      const e = Date.now() - startedAtRef.current;
      setElapsed(e);
      if (e >= TOTAL_DURATION_MS) {
        setRunning(false);
        onTriggerEnd?.();
        return;
      }
      tickRef.current = window.setTimeout(tick, 100);
    }
    tickRef.current = window.setTimeout(tick, 100);
    return () => {
      if (tickRef.current) window.clearTimeout(tickRef.current);
    };
  }, [running, onTriggerEnd]);

  function startTrace() {
    setElapsed(0);
    setRunning(true);
    setUsedCache(false);
    startedAtRef.current = Date.now();
    onTriggerStart?.();
    mutation.mutate();
  }

  // Response data → step data 병합
  const callsIdx = cachedResponse ? indexCalls(cachedResponse.tools_used) : {};
  const steps: RenderedStep[] = TRACE_STEPS.map((spec) => {
    const call = callsIdx[spec.key];
    let status: StepStatus = "pending";
    if (elapsed >= spec.completeAt) status = "completed";
    else if (elapsed >= spec.startAt) status = "running";
    return {
      ...spec,
      status,
      query: call?.arguments || spec.defaultQuery,
      response: call?.result_preview || spec.defaultResponse,
      elapsedMs: spec.completeAt - spec.startAt,
    };
  });

  const fallbackMode = cachedResponse?.source === "fallback" || usedCache;

  return (
    <section className="mb-12">
      {/* Heading */}
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <div className="text-[11px] font-mono text-ink-3 mb-1">§3</div>
          <h2 className="font-display text-2xl md:text-3xl font-semibold tracking-tight">
            AI가 어떻게 추론했나
          </h2>
        </div>
      </div>

      {/* Idle CTA */}
      {!running && elapsed === 0 && !cachedResponse && (
        <div className="bg-panel border border-line-1 rounded-lg p-5 mb-3 flex items-center justify-between">
          <div className="text-xs text-ink-3">
            아직 분석 trace가 없습니다. 클릭하면 Supervisor + 3 sub-agent 호출.
          </div>
          <TriggerButton onClick={startTrace} pending={mutation.isPending} label="지금 분석" />
        </div>
      )}

      {/* Idle with cached summary */}
      {!running && elapsed === 0 && cachedResponse && (
        <div className="bg-panel border border-line-1 rounded-lg p-5 mb-3 flex items-center justify-between">
          <div className="text-xs text-ink-2">
            직전 분석 완료 · {cachedResponse.tools_used.length} sub-agent 호출 ·{" "}
            {(TOTAL_DURATION_MS / 1000).toFixed(1)}s
          </div>
          <TriggerButton onClick={startTrace} pending={mutation.isPending} label="지금 다시 분석" />
        </div>
      )}

      {/* Running / completed trace tree */}
      {(running || elapsed > 0) && (
        <div className="bg-panel border border-line-1 rounded-lg p-6 font-mono text-[13px] leading-relaxed">
          {/* Trace lines */}
          {steps.map((step, idx) => {
            const isLast = idx === steps.length - 1;
            const isSupervisor = step.key === "supervisor";
            return (
              <StepLine
                key={step.key}
                step={step}
                isLast={isLast}
                isSupervisor={isSupervisor}
              />
            );
          })}

          {/* Divider */}
          {(isCompleted || hasFatalError) && (
            <div className="border-t border-line-2 mt-4 pt-3 flex items-center justify-between">
              {isCompleted && !hasFatalError && (
                <>
                  <div className="text-opportunity-700 text-[13px] font-medium">
                    ✓ {(TOTAL_DURATION_MS / 1000).toFixed(1)}s · 분석 완료
                    {fallbackMode && (
                      <span className="ml-2 text-[10px] font-mono text-ink-3 bg-line-1 px-1.5 py-0.5 rounded">
                        캐시
                      </span>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={startTrace}
                    className="text-[11px] text-ink-3 hover:text-ink underline"
                  >
                    다시 실행
                  </button>
                </>
              )}
              {hasFatalError && (
                <>
                  <div className="text-crisis-700 text-[12px]">
                    Multi-Agent 일시 불가 — Genie fallback 경로 표시 중
                  </div>
                  <button
                    type="button"
                    onClick={startTrace}
                    className="text-[11px] text-ink-3 hover:text-ink underline"
                  >
                    재시도
                  </button>
                </>
              )}
            </div>
          )}

          {/* Live response (completed에 narrative_summary 또는 supervisor answer) */}
          {isCompleted && cachedResponse?.answer && (
            <div className="mt-4 pt-4 border-t border-line-2 text-[13px] font-body text-ink-1 whitespace-pre-wrap leading-relaxed">
              <span className="text-ink-3">▸ </span>
              {cachedResponse.answer}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function StepLine({
  step,
  isLast,
  isSupervisor,
}: {
  step: RenderedStep;
  isLast: boolean;
  isSupervisor: boolean;
}) {
  const indent = isSupervisor ? "" : "  ";
  const branch = isSupervisor ? "" : isLast ? "└─ " : "├─ ";

  if (step.status === "pending") {
    return (
      <div className="text-ink-3 opacity-40">
        <span className="text-line-2">
          {indent}
          {branch}
        </span>
        <span className="text-ink-3">○ </span>
        <span>{step.label}</span>
      </div>
    );
  }

  return (
    <div className="mb-1">
      {/* Header line */}
      <div className="flex items-baseline gap-2">
        <span className="text-line-2 shrink-0">
          {indent}
          {branch}
        </span>
        <span
          className={
            step.status === "running"
              ? "text-crisis-500 animate-pulse"
              : "text-opportunity-600"
          }
        >
          {step.status === "running" ? "●" : "✓"}
        </span>
        <span className="font-display font-semibold text-ink-1 not-italic">{step.label}</span>
        {step.status === "completed" && step.elapsedMs != null && (
          <span className="ml-auto text-[11px] text-ink-3">
            {(step.elapsedMs / 1000).toFixed(1)}s
          </span>
        )}
      </div>

      {/* Query line */}
      {step.query && (
        <div className="text-ink-3 italic text-[12px] ml-7 truncate" title={step.query}>
          {step.query}
        </div>
      )}

      {/* Response (only completed) */}
      {step.status === "completed" && step.response && (
        <div className="text-ink-1 text-[13px] ml-7 mt-0.5 truncate" title={step.response}>
          <span className="text-opportunity-600">└─ ✓ </span>
          {step.response}
        </div>
      )}
    </div>
  );
}

function TriggerButton({
  onClick,
  pending,
  label,
}: {
  onClick: () => void;
  pending: boolean;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={pending}
      className="px-4 py-2 rounded-md bg-ink text-white text-xs font-medium hover:bg-ink-2 disabled:opacity-50 transition-colors shrink-0"
    >
      {pending ? "추론 시작 중..." : label}
    </button>
  );
}
