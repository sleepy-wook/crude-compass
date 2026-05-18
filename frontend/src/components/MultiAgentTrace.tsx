/**
 * MultiAgentTrace — Discovery 추론 과정 component.
 * Supervisor query 응답 staggered animation으로 sub-agent 호출 visualize.
 * Vertical timeline 풍 (ASCII art 사용 안 함).
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
  startAt: number;
  completeAt: number;
}

const TRACE_STEPS: StepSpec[] = [
  {
    key: "supervisor",
    label: "분석 시작",
    defaultQuery: "Multi-Agent 호출",
    defaultResponse: "3개 sub-agent 호출",
    startAt: 200,
    completeAt: 400,
  },
  {
    key: "genie",
    label: "데이터 조회",
    defaultQuery: "WTI와 두바이의 30일 평균 대비 변동, 미국 재고 변화",
    defaultResponse: "WTI +5.2%, 재고 -3.1MB",
    startAt: 600,
    completeAt: 2700,
  },
  {
    key: "knowledge_assistant",
    label: "뉴스 분석",
    defaultQuery: "호르무즈 해협 긴장 관련 보도",
    defaultResponse: "7건 검색, 톤 -0.82 (약세)",
    startAt: 2900,
    completeAt: 4700,
  },
  {
    key: "mission_plan_fma",
    label: "권고 산출",
    defaultQuery: "위기 점수 78, 위기 시그널 4건, 안정 시그널 1건",
    defaultResponse: "장기계약 60% → 75%로 상향",
    startAt: 4900,
    completeAt: 9200,
  },
];

const TOTAL_DURATION_MS = 9400;

type StepStatus = "pending" | "running" | "completed";

interface RenderedStep extends StepSpec {
  status: StepStatus;
  query?: string;
  response?: string;
}

function mapSubAgentToKey(name: string): AgentKey | null {
  const lower = name.toLowerCase();
  if (lower.includes("genie")) return "genie";
  if (lower.includes("knowledge") || lower.includes("ka")) return "knowledge_assistant";
  if (
    lower.includes("haiku") ||
    lower.includes("claude") ||
    lower.includes("mission_plan") ||
    lower.includes("fma")
  )
    return "mission_plan_fma";
  return null;
}

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
      if (cachedResponse) setUsedCache(true);
    },
  });

  const isCompleted =
    !running && elapsed >= TOTAL_DURATION_MS && (mutation.isSuccess || cachedResponse);
  const hasFatalError = mutation.isError && !cachedResponse && elapsed >= TOTAL_DURATION_MS;

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
    };
  });

  const fallbackMode = cachedResponse?.source === "fallback" || usedCache;
  const showTrace = running || elapsed > 0;

  return (
    <section className="mb-14">
      {/* Idle state (no run yet) */}
      {!showTrace && (
        <div className="bg-panel border border-line-1 rounded-xl px-6 py-5 flex items-center justify-between">
          <div>
            <div className="text-sm text-ink-1 mb-0.5">
              {cachedResponse ? "직전 분석 완료" : "분석 대기 중"}
            </div>
            <div className="text-xs text-ink-3">
              {cachedResponse
                ? "데이터·뉴스·권고를 합쳐 다시 계산할 수 있습니다"
                : "데이터·뉴스·권고를 합쳐 권고를 산출합니다"}
            </div>
          </div>
          <TriggerButton
            onClick={startTrace}
            pending={mutation.isPending}
            label={cachedResponse ? "다시 분석" : "분석 시작"}
          />
        </div>
      )}

      {/* Running / completed timeline */}
      {showTrace && (
        <div className="bg-panel border border-line-1 rounded-xl p-7">
          <div className="relative pl-7">
            {/* Vertical timeline guide */}
            <div className="absolute left-[7px] top-2 bottom-2 w-px bg-line-2" />

            {steps.map((step, idx) => (
              <TimelineRow key={step.key} step={step} isLast={idx === steps.length - 1} />
            ))}
          </div>

          {/* Footer — completion / error */}
          {(isCompleted || hasFatalError) && (
            <div className="mt-6 pt-5 border-t border-line-1 flex items-center justify-between">
              {isCompleted && !hasFatalError && (
                <>
                  <div className="text-[13px] text-opportunity-700 font-medium">
                    {(TOTAL_DURATION_MS / 1000).toFixed(1)}초 만에 분석 완료
                    {fallbackMode && (
                      <span className="ml-2 text-[11px] text-ink-3 font-normal">캐시된 결과</span>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={startTrace}
                    className="text-xs text-ink-3 hover:text-ink-1 transition-colors"
                  >
                    다시 분석
                  </button>
                </>
              )}
              {hasFatalError && (
                <>
                  <div className="text-[13px] text-ink-2">
                    Multi-Agent 일시 불가, 대체 경로로 응답
                  </div>
                  <button
                    type="button"
                    onClick={startTrace}
                    className="text-xs text-ink-3 hover:text-ink-1 transition-colors"
                  >
                    재시도
                  </button>
                </>
              )}
            </div>
          )}

          {/* Final synthesis */}
          {isCompleted && cachedResponse?.answer && (
            <div className="mt-6 pt-5 border-t border-line-1">
              <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">권고 요약</div>
              <p className="text-[14px] text-ink-1 leading-relaxed whitespace-pre-wrap">
                {cachedResponse.answer}
              </p>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function TimelineRow({ step, isLast }: { step: RenderedStep; isLast: boolean }) {
  const pending = step.status === "pending";
  const running = step.status === "running";
  const completed = step.status === "completed";

  return (
    <div className={isLast ? "pb-0" : "pb-5"}>
      {/* Dot */}
      <div className="absolute -ml-7 mt-1.5">
        <span
          className={
            pending
              ? "block w-[14px] h-[14px] rounded-full border-2 border-line-2 bg-paper"
              : running
                ? "block w-[14px] h-[14px] rounded-full bg-crisis-500 ring-4 ring-crisis-100 animate-pulse"
                : "block w-[14px] h-[14px] rounded-full bg-opportunity-600 ring-4 ring-opportunity-50"
          }
        />
      </div>

      {/* Header */}
      <div className="flex items-baseline justify-between gap-3">
        <span
          className={`font-display text-[15px] font-semibold ${
            pending ? "text-ink-3" : "text-ink-1"
          }`}
        >
          {step.label}
        </span>
        {completed && (
          <span className="text-[11px] text-ink-3 font-mono shrink-0">
            {((step.completeAt - step.startAt) / 1000).toFixed(1)}초
          </span>
        )}
      </div>

      {/* Query — only after start */}
      {!pending && step.query && (
        <div className="mt-1 text-[13px] text-ink-3 leading-relaxed">{step.query}</div>
      )}

      {/* Response — only after complete */}
      {completed && step.response && (
        <div className="mt-1 text-[13px] text-ink-1 leading-relaxed">{step.response}</div>
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
      className="px-4 py-2 rounded-md bg-ink-1 text-paper text-[13px] font-medium hover:bg-ink-2 disabled:opacity-50 transition-colors shrink-0"
    >
      {pending ? "분석 중..." : label}
    </button>
  );
}
