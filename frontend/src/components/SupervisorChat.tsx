/**
 * SupervisorChat — 자연어 질의 → Multi-Agent Supervisor 응답.
 *
 * Discovery Zone 3 (탐색) 내 component. WhatIf에서 추출 + production SaaS 풍 단순화.
 */
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { SupervisorQueryResponse } from "../lib/types";

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

export function SupervisorChat() {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<SupervisorQueryResponse | null>(null);

  const mut = useMutation({
    mutationFn: (q: string) => api.supervisorQuery(q),
    onSuccess: (data) => setResponse(data),
  });

  function submit() {
    if (question.trim().length < 2) return;
    mut.mutate(question);
  }

  return (
    <section className="mb-10 bg-panel border border-line-1 rounded-xl p-7">
      <div className="flex items-baseline justify-between mb-4">
        <h3 className="font-display text-lg font-semibold text-ink-1">AI 어시스턴트</h3>
        <span className="text-[11px] text-ink-3">자연어로 질문</span>
      </div>

      {/* Examples */}
      <div className="flex flex-wrap gap-2 mb-3">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => setQuestion(ex)}
            className="text-xs px-3 py-1.5 rounded-full border border-line-2 text-ink-2 hover:bg-line-1 hover:border-ink-3 transition-colors"
          >
            {ex}
          </button>
        ))}
      </div>

      {/* Input */}
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="궁금한 점을 자유롭게 입력하세요"
        rows={2}
        className="w-full text-sm p-3 border border-line-2 rounded-md focus:outline-none focus:border-ink-3 mb-3 resize-none"
      />
      <div className="flex items-center justify-between mb-2">
        <button
          type="button"
          onClick={submit}
          disabled={mut.isPending || question.trim().length < 2}
          className="px-4 py-2 rounded-md bg-ink-1 text-paper text-[13px] font-medium hover:bg-ink-2 disabled:opacity-50 transition-colors"
        >
          {mut.isPending ? "분석 중..." : "질문하기"}
        </button>
        {mut.isError && (
          <span className="text-xs text-crisis-700">요청 처리 중 오류가 발생했습니다.</span>
        )}
      </div>

      {/* Response */}
      {response && (
        <div className="border-t border-line-1 pt-5 mt-5">
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
          {response.tools_used && response.tools_used.length > 0 && (
            <div className="pt-3 border-t border-line-1">
              <div className="text-[11px] text-ink-3 mb-2">참고 도구</div>
              <div className="flex flex-wrap gap-1.5">
                {response.tools_used.map((t, i) => (
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
      )}
    </section>
  );
}
