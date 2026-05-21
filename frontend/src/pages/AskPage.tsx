/**
 * AskPage — /ask (Investigation, ChatGPT-style, 2026-05-21 redesign).
 *
 * Layout:
 *   ┌─ Sidebar 256px ──┐ ┌─ Main ────────────┐
 *   │ [+ 새 대화]       │ │ Header             │
 *   │ conversation list │ │ Messages / Empty   │
 *   └───────────────────┘ │ Sticky composer    │
 *                         └────────────────────┘
 *
 * 대화 기록: localStorage (`crude-compass:chats:v1`), 최대 50개.
 * Multi-Agent backend: /api/supervisor/query → Agent Bricks Supervisor.
 */
import { useEffect, useRef, useState } from "react";
import { ArrowUp, Network } from "lucide-react";
import { api, supervisorQueryStream } from "../lib/api";
import { useChatHistory } from "../lib/useChatHistory";
import { ChatHistorySidebar } from "../components/ChatHistorySidebar";
import { ChatMessage } from "../components/ChatMessage";
import { cn } from "../lib/utils";
import type { SubAgentCall } from "../lib/types";

const SAMPLE_QUERIES: string[] = [
  "지금 같은 시장 상황은 과거에 어떻게 됐어?",
  "호르무즈 긴장 누적될 때 평균 가격 반영은?",
  "OPEC 사우디 최근 공급 추세 알려줘",
  "지금 추세에서 30일 후 가격 예측은?",
];

export function AskPage() {
  const history = useChatHistory();
  const turns = history.active?.turns ?? [];

  const [question, setQuestion] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new message
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns.length]);

  // streaming state — pending 동안 ChatMessage가 점진 갱신됨
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  async function runStream(enriched: string) {
    setStreaming(true);
    const abort = new AbortController();
    abortRef.current = abort;
    let accumulated = "";
    const tools: SubAgentCall[] = [];
    try {
      // 1차 시도: streaming
      await supervisorQueryStream(enriched, {
        signal: abort.signal,
        onEvent: (ev) => {
          if (ev.type === "delta") {
            accumulated += ev.text;
            history.updateLastTurn({ content: accumulated, pending: true });
          } else if (ev.type === "tool_call") {
            tools.push({ name: ev.name, arguments: null, result_preview: null });
            history.updateLastTurn({ toolsUsed: [...tools], pending: true });
          } else if (ev.type === "done") {
            const finalTools: SubAgentCall[] = ev.tools_used.map((t) => ({
              name: t.name,
              arguments: t.arguments ?? null,
              result_preview: t.result_preview ?? null,
            }));
            history.updateLastTurn({
              content: ev.answer || accumulated || "(응답 비어있음)",
              toolsUsed: finalTools,
              source: "live",
              pending: false,
              error: false,
            });
          } else if (ev.type === "error") {
            history.updateLastTurn({ pending: false, error: true });
          } else if (ev.type === "fallback") {
            // Supervisor 미설정 → 일반 query API로 fallback
            api.supervisorQuery(enriched).then((data) => {
              history.updateLastTurn({
                content: data.answer || "(응답 비어있음)",
                toolsUsed: data.tools_used,
                source: data.source,
                pending: false,
                error: false,
              });
            }).catch(() => history.updateLastTurn({ pending: false, error: true }));
          }
        },
      });
    } catch (e) {
      if (!abort.signal.aborted) {
        history.updateLastTurn({ pending: false, error: true });
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }

  async function submit(text?: string) {
    const q = (text ?? question).trim();
    if (q.length < 2 || streaming) return;

    // history에 append (active 없으면 자동 새 conversation)
    history.appendTurn({
      question: q,
      enriched: q,
      similarCtx: null,
      message: {
        role: "assistant",
        content: "",
        pending: true,
      },
    });
    setQuestion("");
    void runStream(q);
  }

  const isEmpty = turns.length === 0;

  return (
    <div className="flex h-full max-h-[calc(100vh-3.5rem)]">
      <ChatHistorySidebar
        conversations={history.conversations}
        activeId={history.activeId}
        onSelect={history.select}
        onNew={history.startNew}
        onRemove={history.remove}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="px-8 pt-8 pb-4 border-b border-line-1 flex items-baseline justify-between flex-wrap gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-1">
              Investigation
            </div>
            <h1 className="font-display text-xl font-semibold text-ink-1 tracking-tight">
              AI에게 묻기
            </h1>
            <p className="text-[12px] text-ink-3 mt-1">
              Agent Bricks Supervisor — Genie (데이터) · Knowledge Assistant (문서) · 권고 sub-agent
            </p>
          </div>
        </header>

        {/* Body */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-8 py-6">
            {isEmpty ? (
              <EmptyState samples={SAMPLE_QUERIES} onPick={(s) => submit(s)} />
            ) : (
              turns.map((t, i) => (
                <div key={i}>
                  <ChatMessage msg={{ role: "user", content: t.question }} />
                  <ChatMessage msg={t.message} />
                </div>
              ))
            )}
          </div>
        </div>

        {/* Composer */}
        <div className="border-t border-line-1 bg-paper">
          <div className="max-w-3xl mx-auto px-8 py-4">
            <Composer
              value={question}
              onChange={setQuestion}
              onSubmit={() => submit()}
              disabled={streaming}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyState({
  samples,
  onPick,
}: {
  samples: string[];
  onPick: (s: string) => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] text-center">
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-line-1 mb-4">
        <Network className="w-5 h-5 text-ink-2" />
      </div>
      <h2 className="font-display text-2xl font-semibold text-ink-1 tracking-tight mb-2">
        무엇이 궁금하세요?
      </h2>
      <p className="text-[13px] text-ink-3 mb-8">
        시장·뉴스·과거 사례 — 자연어로 질문
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-2xl">
        {samples.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onPick(s)}
            className="px-4 py-2.5 text-[12.5px] text-ink-2 text-left bg-white border border-line-2 rounded-lg hover:bg-line-1 hover:text-ink-1 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function Composer({
  value,
  onChange,
  onSubmit,
  disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled: boolean;
}) {
  function onKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  }
  const canSubmit = !disabled && value.trim().length >= 2;

  return (
    <div className="relative">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKey}
        placeholder="질문을 입력하세요... (Enter = 전송, Shift+Enter = 줄바꿈)"
        rows={2}
        className="w-full pr-12 pl-4 py-3 text-[13px] border border-line-2 rounded-xl bg-white text-ink-1 placeholder:text-ink-3 focus:outline-none focus:border-ink-3 resize-none leading-relaxed"
      />
      <button
        type="button"
        onClick={onSubmit}
        disabled={!canSubmit}
        className={cn(
          "absolute right-2 bottom-2.5 w-8 h-8 rounded-lg flex items-center justify-center transition-colors",
          canSubmit
            ? "bg-ink-1 text-paper hover:bg-ink-2"
            : "bg-line-1 text-ink-3 cursor-not-allowed",
        )}
        aria-label="전송"
      >
        <ArrowUp className="w-4 h-4" />
      </button>
    </div>
  );
}
