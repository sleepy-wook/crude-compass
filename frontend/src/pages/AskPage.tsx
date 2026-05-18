/**
 * AskPage — /ask
 *
 * AI에게 묻기 (Multi-Agent + Genie). Cursor / Databricks Genie 풍.
 * 자연어 질의 → Supervisor → 3 sub-agent → 응답 trace.
 * 하단 collapsible: 과거 권고 검증 (Backtest slider).
 */
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { SubAgentCall, SupervisorQueryResponse } from "../lib/types";
import { BacktestTimeSlider } from "../components/BacktestTimeSlider";
import { usePatternCurrent } from "../lib/queries";

// 각 sample 질문에 어떤 sub-agent 주로 호출되는지 hint (평가위원/매니저 demo).
interface SampleQuery {
  text: string;
  routes: ("genie" | "knowledge" | "mission_plan")[];
  preview: string; // cached one-line example response
}

const EXAMPLES: SampleQuery[] = [
  {
    text: "지금 같은 시장 상황은 과거에 어떻게 됐어?",
    routes: ["genie", "mission_plan"],
    preview: "지난 7년 비슷한 패턴 4건 — 평균 0.09% 절감, 적중률 75%",
  },
  {
    text: "호르무즈 긴장 누적될 때 평균 가격 반영은?",
    routes: ["genie", "knowledge"],
    preview: "호르무즈 봉쇄 우려 시기 두바이 평균 +8~12% (30일), Term 비중 75%로 hedge한 케이스 절감 효과 유의",
  },
  {
    text: "OPEC 사우디 최근 공급 추세 알려줘",
    routes: ["knowledge", "genie"],
    preview: "MOMR 2026-03 사우디 10.1M b/d (+24 kb/d M/M), 공급 부족 (-77M b/d)",
  },
  {
    text: "지금 추세에서 30일 후 가격 예측은?",
    routes: ["mission_plan", "genie"],
    preview: "위기 강도 10/10 + 호르무즈 신호 누적 → Brent 130 시나리오 580억 절감 가능 (보수적)",
  },
];

interface SimilarContext {
  n: number;
  avg_saving_30d_pct: number | null;
  avg_dubai_change_30d_pct: number | null;
  hit_rate_pct: number | null;
}

const AGENT_LABEL: Record<string, string> = {
  genie: "데이터 조회",
  knowledge: "뉴스 분석",
  ka: "뉴스 분석",
  haiku: "권고 산출",
  claude: "권고 산출",
};

function labelAgent(name: string): string {
  const lower = name.toLowerCase();
  for (const [key, val] of Object.entries(AGENT_LABEL)) {
    if (lower.includes(key)) return val;
  }
  return name;
}

interface ChatTurn {
  question: string;            // 원본 매니저 질문
  enriched_question: string;   // backend로 보낸 enriched (context prepended)
  similar_context: SimilarContext | null;  // 응답 카드에 "참조한 과거 N건" 표시
  response: SupervisorQueryResponse | null;
  pending: boolean;
  error: boolean;
}

export function AskPage() {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const pattern = usePatternCurrent();

  const mut = useMutation({
    mutationFn: ({ enriched }: { original: string; enriched: string }) =>
      api.supervisorQuery(enriched),
    onSuccess: (data, { original }) => {
      setTurns((prev) => updateTurn(prev, original, { response: data, pending: false, error: false }));
    },
    onError: (_err, { original }) => {
      setTurns((prev) => updateTurn(prev, original, { response: null, pending: false, error: true }));
    },
  });

  function updateTurn(prev: ChatTurn[], q: string, patch: Partial<ChatTurn>): ChatTurn[] {
    const next = [...prev];
    const idx = next.findIndex((t) => t.question === q && t.pending);
    if (idx >= 0) next[idx] = { ...next[idx], ...patch };
    return next;
  }

  async function submit(text?: string) {
    const q = (text ?? question).trim();
    if (q.length < 2 || mut.isPending) return;

    // Auto-inject similar market memory context (★ wow)
    const score = pattern.data?.current?.pattern_score ?? null;
    const missionType =
      score == null
        ? null
        : score >= 70
          ? "HEDGE"
          : score <= 30
            ? "OPPORTUNITY"
            : null;

    let similarCtx: SimilarContext | null = null;
    let contextPrefix = "";
    if (score != null) {
      try {
        const sim = await api.marketMemorySimilar({
          pattern_score: score,
          mission_type: missionType,
          limit: 5,
          score_range: 10,
        });
        if (sim.lakebase_available && sim.summary?.n && sim.summary.n > 0) {
          similarCtx = {
            n: sim.summary.n,
            avg_saving_30d_pct: sim.summary.avg_saving_30d_pct ?? null,
            avg_dubai_change_30d_pct: sim.summary.avg_dubai_change_30d_pct ?? null,
            hit_rate_pct: sim.summary.hit_rate_pct ?? null,
          };
          contextPrefix =
            `[참고 컨텍스트 — 시장 메모리]\n` +
            `현재 위기 점수 ${score.toFixed(0)} (${missionType ?? "관망"} zone).\n` +
            `지난 7년 비슷한 시그널 조합이 ${sim.summary.n}건 발견됨.\n` +
            `평균 30일 후 두바이 가격 변동 ${(sim.summary.avg_dubai_change_30d_pct ?? 0).toFixed(1)}%, ` +
            `AI 추천 적중률 ${(sim.summary.hit_rate_pct ?? 0).toFixed(0)}%, ` +
            `평균 절감 ${(sim.summary.avg_saving_30d_pct ?? 0).toFixed(2)}%.\n\n` +
            `[매니저 질문]\n`;
        }
      } catch {
        // similar fetch 실패 시 context 없이 진행 (graceful)
      }
    }

    const enriched = contextPrefix + q;

    setTurns((prev) => [
      ...prev,
      {
        question: q,
        enriched_question: enriched,
        similar_context: similarCtx,
        response: null,
        pending: true,
        error: false,
      },
    ]);
    setQuestion("");
    mut.mutate({ original: q, enriched });
  }

  return (
    <div className="max-w-4xl mx-auto px-8 py-10">
      {/* Page intro */}
      <header className="mb-10">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-2">AI에게 묻기</div>
        <h1 className="font-display text-[28px] md:text-[32px] font-semibold tracking-tight text-ink-1 mb-2 leading-tight">
          Multi-Agent에 자연어로 질문
        </h1>
        <p className="text-sm text-ink-2 leading-relaxed max-w-2xl">
          Supervisor가 데이터 조회·뉴스 분석·권고 산출 도구를 자동 호출해 답합니다.
        </p>
      </header>

      {/* Chat turns */}
      {turns.length === 0 && (
        <EmptyStateGuide examples={EXAMPLES} onPick={submit} />
      )}

      {turns.map((t, i) => (
        <ChatTurnView key={i} turn={t} />
      ))}

      {/* Input */}
      <div className="sticky bottom-4 mt-8">
        <div className="bg-panel border border-line-1 rounded-xl shadow-sm p-3">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="질문을 입력하고 Enter (Shift+Enter는 줄바꿈)"
            rows={2}
            className="w-full text-sm p-2 focus:outline-none resize-none placeholder:text-ink-3"
          />
          <div className="flex items-center justify-between mt-1 pt-2 border-t border-line-1">
            <div className="text-[11px] text-ink-3">자연어 질의는 Multi-Agent를 통해 응답됩니다</div>
            <button
              type="button"
              onClick={() => submit()}
              disabled={mut.isPending || question.trim().length < 2}
              className="px-3.5 py-1.5 rounded-md bg-ink-1 text-paper text-[12px] font-medium hover:bg-ink-2 disabled:opacity-50 transition-colors"
            >
              {mut.isPending ? "응답 생성 중..." : "보내기"}
            </button>
          </div>
        </div>
      </div>

      {/* Backtest slider */}
      <div className="mt-12">
        <h2 className="font-display text-lg font-semibold text-ink-1 mb-4">과거 권고 검증</h2>
        <BacktestTimeSlider />
      </div>

      <div className="h-20" />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// EmptyStateGuide — Multi-Agent flow diagram + Sample chip (dynamic).
//
// Hover/click 시 chip의 routes에 해당하는 sub-agent 노드가 active 색으로 강조.
// 평가위원 demo: "Supervisor가 어떤 sub-agent 호출하는지 자동" 5초에 인지.
// ────────────────────────────────────────────────────────────────────────
type AgentKey = "genie" | "knowledge" | "mission_plan";

const AGENT_META: Record<
  AgentKey,
  { name: string; role: string; source: string; icon: string }
> = {
  genie: {
    name: "Genie",
    role: "데이터 조회 (SQL)",
    source: "Unity Catalog · gold/silver tables",
    icon: "▤",
  },
  knowledge: {
    name: "Knowledge",
    role: "뉴스·MOMR 검색",
    source: "GDELT + OPEC MOMR PDF + bronze.news",
    icon: "✦",
  },
  mission_plan: {
    name: "Mission Plan",
    role: "권고 산출 (FMA)",
    source: "Claude Haiku 4.5 · target_pct + simulation",
    icon: "◆",
  },
};

function EmptyStateGuide({
  examples,
  onPick,
}: {
  examples: SampleQuery[];
  onPick: (q: string) => void;
}) {
  const [hoveredRoutes, setHoveredRoutes] = useState<AgentKey[] | null>(null);

  return (
    <>
      {/* Multi-Agent flow diagram — hover/active routes 강조 */}
      <div className="bg-panel border border-line-1 rounded-xl p-6 mb-6">
        <div className="flex items-baseline justify-between mb-4">
          <div className="text-[11px] uppercase tracking-wider text-ink-3">Multi-Agent 흐름</div>
          <span className="text-[10px] text-ink-3 italic">
            예시 질문에 hover하면 어떤 sub-agent 호출되는지 강조
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-[110px_24px_1fr] gap-3 md:gap-4 items-stretch">
          {/* 매니저 노드 */}
          <div className="rounded-md border border-line-2 bg-line-1/40 p-3 text-center flex flex-col justify-center">
            <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">매니저</div>
            <div className="text-[12px] text-ink-1 font-medium">자연어 질문</div>
          </div>
          {/* arrow */}
          <div className="hidden md:flex items-center justify-center text-ink-3 text-lg">→</div>
          {/* Supervisor + sub-agents */}
          <div>
            <div className="rounded-md border border-ink-1 bg-ink-1 text-paper p-3 mb-3">
              <div className="flex items-baseline gap-2">
                <span className="text-[14px]">⚡</span>
                <div>
                  <div className="text-[10px] uppercase tracking-wider opacity-70">Supervisor</div>
                  <div className="text-[12px] font-medium">자동 라우팅 — 질문 분석 후 sub-agent 선택</div>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {(Object.keys(AGENT_META) as AgentKey[]).map((key) => {
                const a = AGENT_META[key];
                const active = hoveredRoutes?.includes(key) ?? false;
                return (
                  <div
                    key={key}
                    className={`rounded-md p-2.5 transition-all border ${
                      active
                        ? "border-ink-1 bg-ink-1/5 shadow-sm"
                        : "border-line-1 bg-panel opacity-80"
                    }`}
                  >
                    <div className="flex items-baseline gap-1.5 mb-1">
                      <span
                        className={`text-[12px] ${active ? "text-ink-1" : "text-ink-3"}`}
                        aria-hidden
                      >
                        {a.icon}
                      </span>
                      <div className="text-[10px] uppercase tracking-wider text-ink-3">
                        {a.name}
                      </div>
                      {active && (
                        <span className="ml-auto text-[9px] uppercase tracking-wider bg-crisis-500 text-white px-1.5 py-0.5 rounded">
                          호출 예정
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-ink-2 leading-snug">{a.role}</div>
                    <div className="text-[10px] text-ink-3 mt-1 leading-snug italic">
                      {a.source}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
        <p className="text-[11px] text-ink-3 mt-4 leading-relaxed">
          단일 endpoint 1개 호출 — Supervisor가 자동 분석해 3 sub-agent 중 필요한 것만 delegate.
          응답에 어떤 도구가 호출됐는지 trace 표시.
        </p>
      </div>

      {/* Sample chip — hover로 다이어그램 강조, click으로 즉시 실행 */}
      <div className="bg-panel border border-line-1 rounded-xl p-6 mb-6">
        <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-4">
          예시 질문 — hover로 routing 확인, 클릭으로 즉시 실행
        </div>
        <div className="space-y-2.5">
          {examples.map((ex) => (
            <button
              key={ex.text}
              type="button"
              onMouseEnter={() => setHoveredRoutes(ex.routes as AgentKey[])}
              onMouseLeave={() => setHoveredRoutes(null)}
              onFocus={() => setHoveredRoutes(ex.routes as AgentKey[])}
              onBlur={() => setHoveredRoutes(null)}
              onClick={() => onPick(ex.text)}
              className="w-full text-left rounded-lg border border-line-1 hover:border-ink-3 hover:bg-line-1/30 transition-colors p-3"
            >
              <div className="flex items-baseline justify-between gap-3 mb-1.5">
                <span className="text-[13px] text-ink-1 font-medium">{ex.text}</span>
                <div className="flex items-center gap-1 shrink-0">
                  {ex.routes.map((r) => (
                    <span
                      key={r}
                      className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-line-1 text-ink-2 font-mono"
                    >
                      {AGENT_META[r as AgentKey]?.name ?? r}
                    </span>
                  ))}
                </div>
              </div>
              <div className="text-[11px] text-ink-3 leading-relaxed italic">
                예상 응답: {ex.preview}
              </div>
            </button>
          ))}
        </div>
      </div>
    </>
  );
}

function ChatTurnView({ turn }: { turn: ChatTurn }) {
  return (
    <div className="mb-8">
      {/* Similar context badge — ★ wow: AI가 자동으로 시장 메모리 참조 */}
      {turn.similar_context && (
        <div className="mb-2 text-[11px] text-ink-3 flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-line-1 text-ink-2">
            시장 메모리 자동 참조
          </span>
          <span>
            지난 7년 비슷한 패턴{" "}
            <span className="text-ink-1 font-medium">{turn.similar_context.n}건</span>{" "}
            · 30일 평균{" "}
            <span className="text-ink-1 font-medium">
              {(turn.similar_context.avg_dubai_change_30d_pct ?? 0).toFixed(1)}%
            </span>{" "}
            · 적중률{" "}
            <span className="text-ink-1 font-medium">
              {(turn.similar_context.hit_rate_pct ?? 0).toFixed(0)}%
            </span>
          </span>
        </div>
      )}

      {/* Question */}
      <div className="bg-line-1/60 rounded-lg px-5 py-3 mb-3 ml-auto max-w-xl">
        <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-1">질문</div>
        <p className="text-sm text-ink-1 leading-relaxed">{turn.question}</p>
      </div>

      {/* Response */}
      {turn.pending && (
        <div className="bg-panel border border-line-1 rounded-lg px-5 py-4">
          <div className="flex items-center gap-2 text-sm text-ink-3">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-crisis-500 animate-pulse" />
            <span>Multi-Agent가 분석 중...</span>
          </div>
        </div>
      )}

      {turn.error && (
        <div className="bg-panel border border-line-1 rounded-lg px-5 py-4">
          <div className="text-sm text-crisis-700">요청 처리 중 오류가 발생했습니다.</div>
        </div>
      )}

      {turn.response && <ResponseCard response={turn.response} />}
    </div>
  );
}

function ResponseCard({ response }: { response: SupervisorQueryResponse }) {
  const tools = response.tools_used || [];
  return (
    <div className="bg-panel border border-line-1 rounded-lg px-5 py-4">
      <div className="flex items-center gap-2 mb-3">
        <span
          className={`inline-flex items-center gap-1.5 text-[11px] ${
            response.source === "live" ? "text-opportunity-700" : "text-ink-3"
          }`}
        >
          <span
            className={`inline-block w-1.5 h-1.5 rounded-full ${
              response.source === "live" ? "bg-opportunity-500" : "bg-ink-3/50"
            }`}
          />
          {response.source === "live" ? "실시간 응답" : "캐시된 응답"}
        </span>
      </div>
      <p className="text-[14px] text-ink-1 leading-relaxed whitespace-pre-wrap mb-4">
        {response.answer}
      </p>
      {tools.length > 0 && (
        <div className="pt-3 border-t border-line-1">
          <div className="text-[11px] text-ink-3 mb-2">참고 도구</div>
          <div className="flex flex-wrap gap-1.5">
            {tools.map((t: SubAgentCall, i: number) => (
              <span
                key={`${t.name}-${i}`}
                className="text-[11px] px-2 py-0.5 rounded-full bg-line-1 text-ink-2 border border-line-2"
              >
                {labelAgent(t.name)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
