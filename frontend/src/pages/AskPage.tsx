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

const EXAMPLES = [
  "오늘 위기 점수 어디서 왔어?",
  "OPEC 5월 사우디 감산 근거는?",
  "최근 OPEC 사우디 공급 수치 보여줘",
  "두바이유 7일 추세와 매입 비중 추천",
];

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
  question: string;
  response: SupervisorQueryResponse | null;
  pending: boolean;
  error: boolean;
}

export function AskPage() {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);

  const mut = useMutation({
    mutationFn: (q: string) => api.supervisorQuery(q),
    onSuccess: (data, q) => {
      setTurns((prev) => updateTurn(prev, q, { response: data, pending: false, error: false }));
    },
    onError: (_err, q) => {
      setTurns((prev) => updateTurn(prev, q, { response: null, pending: false, error: true }));
    },
  });

  function updateTurn(prev: ChatTurn[], q: string, patch: Partial<ChatTurn>): ChatTurn[] {
    const next = [...prev];
    const idx = next.findIndex((t) => t.question === q && t.pending);
    if (idx >= 0) next[idx] = { ...next[idx], ...patch };
    return next;
  }

  function submit(text?: string) {
    const q = (text ?? question).trim();
    if (q.length < 2 || mut.isPending) return;
    setTurns((prev) => [...prev, { question: q, response: null, pending: true, error: false }]);
    setQuestion("");
    mut.mutate(q);
  }

  return (
    <div className="max-w-4xl mx-auto px-8 py-10">
      {/* Page intro */}
      <header className="mb-10">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-2">AI에게 묻기</div>
        <h1 className="font-display text-[28px] md:text-[32px] font-semibold tracking-tight text-ink-1 mb-2 leading-tight">
          Multi-Agent에게 자연어로 질문
        </h1>
        <p className="text-sm text-ink-2 leading-relaxed max-w-2xl">
          Supervisor가 데이터 조회·뉴스 분석·권고 산출 도구를 자동 호출해 답합니다.
        </p>
      </header>

      {/* Chat turns */}
      {turns.length === 0 && (
        <div className="bg-panel border border-line-1 rounded-xl p-10 mb-6 text-center">
          <p className="text-sm text-ink-2 mb-5">아래에서 예시를 선택하거나 질문을 입력하세요.</p>
          <div className="flex flex-wrap gap-2 justify-center">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => submit(ex)}
                className="text-xs px-3 py-1.5 rounded-full border border-line-2 text-ink-2 hover:bg-line-1 hover:border-ink-3 transition-colors"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
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

function ChatTurnView({ turn }: { turn: ChatTurn }) {
  return (
    <div className="mb-8">
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
