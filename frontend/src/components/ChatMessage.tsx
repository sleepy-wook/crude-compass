/**
 * ChatMessage — Investigation 채팅 메시지 bubble (2026-05-21).
 *
 * - user: 오른쪽 정렬, ink-1 bg
 * - assistant: 왼쪽 정렬, paper bg, 본문 + collapsible "▾ AI 분석 단계"
 *
 * AI 분석 단계 = Agent Bricks Supervisor의 sub-agent calls (Genie / KA / 권고).
 */
import { useState } from "react";
import { ChevronDown, Network } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "../lib/utils";
import type { SubAgentCall } from "../lib/types";

/**
 * ChatStep — Supervisor 스트림의 순서 보존 trace.
 * SSE가 delta/tool_call을 순서대로 보내므로, 이를 순서대로 쌓아
 * "사고 과정"(마지막 tool_call까지) ↔ "최종 답변"(그 이후 텍스트)으로 분리 렌더.
 */
export type ChatStep =
  | { kind: "text"; text: string }
  | { kind: "tool"; name: string };

export interface ChatMessageData {
  role: "user" | "assistant";
  content: string;
  toolsUsed?: SubAgentCall[];
  /** 순서 보존 trace (있으면 사고과정↔답변 분리 렌더; 없으면 legacy content 렌더) */
  steps?: ChatStep[];
  source?: "live" | "fallback";
  pending?: boolean;
  error?: boolean;
  similarContext?: {
    n: number;
    avg_saving_30d_pct: number | null;
    avg_dubai_change_30d_pct: number | null;
    hit_rate_pct: number | null;
  } | null;
}

interface Props {
  msg: ChatMessageData;
}

export function ChatMessage({ msg }: Props) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[80%] bg-ink-1 text-paper rounded-2xl rounded-tr-md px-4 py-2.5 text-[13px] leading-relaxed whitespace-pre-wrap">
          {msg.content}
        </div>
      </div>
    );
  }
  return <AssistantMessage msg={msg} />;
}

function AssistantMessage({ msg }: { msg: ChatMessageData }) {
  const [showTrace, setShowTrace] = useState(true);
  const isStreaming = msg.pending && msg.content.length > 0;
  const isInitialWait = msg.pending && msg.content.length === 0;

  // 초기 대기 — 첫 token 도착 전 spinner
  if (isInitialWait) {
    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[85%] bg-paper border border-line-1 rounded-2xl rounded-tl-md px-4 py-3 text-[13px] text-ink-3">
          <span className="inline-flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full border-2 border-ink-3 border-t-transparent animate-spin" />
            Supervisor가 분석 중...
          </span>
          <div className="text-[10.5px] text-ink-3 mt-1.5">
            Genie · Knowledge Assistant · 권고 sub-agent 호출
          </div>
          {msg.toolsUsed && msg.toolsUsed.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {msg.toolsUsed.map((t, i) => (
                <span
                  key={`${t.name}-${i}`}
                  className="inline-flex items-center px-1.5 py-0.5 rounded text-[9.5px] font-semibold uppercase tracking-wider bg-info-50 text-info-700"
                >
                  {labelTool(t.name)}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (msg.error) {
    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[85%] bg-crisis-50 border border-crisis-100 rounded-2xl rounded-tl-md px-4 py-3 text-[13px] text-crisis-700">
          분석 실패 — 다시 시도해주세요.
        </div>
      </div>
    );
  }

  // ── steps 기반 렌더: 순서 보존 trace에 tool_call이 하나라도 있으면
  //    "사고 과정"(마지막 tool까지) ↔ "최종 답변"(그 이후) 분리 ──
  if (msg.steps && msg.steps.some((s) => s.kind === "tool")) {
    const { reasoning, answer, toolCount } = splitSteps(msg.steps);
    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[85%] bg-paper border border-line-1 rounded-2xl rounded-tl-md px-4 py-3 text-[13px] text-ink-1 leading-relaxed">
          {reasoning.length > 0 && (
            <div className="mb-3">
              <button
                type="button"
                onClick={() => setShowTrace((v) => !v)}
                className="inline-flex items-center gap-1.5 text-[10.5px] text-ink-3 hover:text-ink-1 transition-colors"
              >
                <Network className="w-3 h-3" />
                사고 과정 · sub-agent {toolCount}개 호출
                <ChevronDown
                  className={cn("w-3 h-3 transition-transform", showTrace && "rotate-180")}
                />
              </button>
              {showTrace && (
                <div className="mt-2 pl-3 border-l-2 border-line-1 space-y-1.5">
                  {reasoning.map((s, i) =>
                    s.kind === "tool" ? (
                      <div key={i}>
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9.5px] font-semibold uppercase tracking-wider bg-info-50 text-info-700">
                          <Network className="w-2.5 h-2.5" />
                          {labelTool(s.name)} 호출
                        </span>
                      </div>
                    ) : (
                      s.text.trim() && (
                        <p key={i} className="text-[12px] text-ink-3 whitespace-pre-wrap leading-relaxed">
                          {s.text.trim()}
                        </p>
                      )
                    ),
                  )}
                </div>
              )}
            </div>
          )}

          {/* 최종 답변 — 사고 과정과 시각 분리 */}
          {answer ? (
            <MarkdownBody content={answer} />
          ) : (
            isStreaming && <span className="text-[12px] text-ink-3">답변 작성 중…</span>
          )}
          {isStreaming && (
            <span className="inline-block w-2 h-3.5 -mb-0.5 bg-ink-3 animate-pulse ml-0.5" aria-label="streaming" />
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[85%] bg-paper border border-line-1 rounded-2xl rounded-tl-md px-4 py-3 text-[13px] text-ink-1 leading-relaxed">
        {/* main answer — Markdown 렌더링 (### bold list 등) */}
        <MarkdownBody content={msg.content} />
        {isStreaming && (
          <span className="inline-block w-2 h-3.5 -mb-0.5 bg-ink-3 animate-pulse ml-0.5" aria-label="streaming" />
        )}

        {/* Agent Bricks 사용 badge — tools_used 비어도 source=live면 표시 */}
        {(!msg.toolsUsed || msg.toolsUsed.length === 0) && msg.source === "live" && (
          <div className="mt-3 pt-2.5 border-t border-line-1">
            <div className="inline-flex items-center gap-1.5 text-[10.5px] text-info-700">
              <Network className="w-3 h-3" />
              <span className="font-medium">Agent Bricks Supervisor</span>
              <span className="text-ink-3">— sub-agent 자동 라우팅</span>
            </div>
          </div>
        )}

        {/* AI 분석 단계 toggle */}
        {msg.toolsUsed && msg.toolsUsed.length > 0 && (
          <div className="mt-3 pt-2.5 border-t border-line-1">
            <button
              type="button"
              onClick={() => setShowTrace((v) => !v)}
              className="inline-flex items-center gap-1.5 text-[10.5px] text-ink-3 hover:text-ink-1 transition-colors"
            >
              <Network className="w-3 h-3" />
              AI 분석 단계 ({msg.toolsUsed.length})
              <ChevronDown
                className={cn(
                  "w-3 h-3 transition-transform",
                  showTrace && "rotate-180",
                )}
              />
            </button>
            {showTrace && (
              <ul className="mt-2 space-y-1">
                {msg.toolsUsed.map((t, i) => (
                  <li
                    key={`${t.name}-${i}`}
                    className="text-[11.5px] flex items-baseline gap-2"
                  >
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9.5px] font-semibold uppercase tracking-wider bg-info-50 text-info-700 shrink-0">
                      {labelTool(t.name)}
                    </span>
                    {t.result_preview && (
                      <span className="text-ink-3 truncate">{t.result_preview}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * splitSteps — 순서 보존 steps를 "사고 과정"(마지막 tool_call까지) ↔
 * "최종 답변"(그 이후 텍스트)으로 분리. tool_call이 없으면 reasoning 빈 배열.
 */
function splitSteps(steps: ChatStep[]): {
  reasoning: ChatStep[];
  answer: string;
  toolCount: number;
} {
  let lastTool = -1;
  let toolCount = 0;
  steps.forEach((s, i) => {
    if (s.kind === "tool") {
      lastTool = i;
      toolCount += 1;
    }
  });
  const reasoning = lastTool >= 0 ? steps.slice(0, lastTool + 1) : [];
  const answerSteps = lastTool >= 0 ? steps.slice(lastTool + 1) : steps;
  const answer = answerSteps
    .filter((s): s is { kind: "text"; text: string } => s.kind === "text")
    .map((s) => s.text)
    .join("");
  return { reasoning, answer, toolCount };
}

export function labelTool(name: string): string {
  const n = name.toLowerCase();
  if (n.includes("genie")) return "Genie";
  if (n.includes("ka-") || n.includes("knowledge")) return "Knowledge Assistant";
  if (n.includes("mission_plan")) return "권고 sub-agent";
  if (n.includes("haiku") || n.includes("claude")) return "Haiku 종합";
  return name.slice(0, 30);
}

/**
 * MarkdownBody — Supervisor 응답 markdown 렌더링.
 * remark-gfm으로 GFM (tables, strikethrough 등) 지원.
 * 작은 chat bubble 안에서 자연스럽게 보이도록 size/spacing override.
 */
export function MarkdownBody({ content }: { content: string }) {
  return (
    <div className="markdown-body text-[13px] leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // 헤더는 chat bubble 안에 너무 크지 않게
          h1: ({ children }) => (
            <h1 className="font-display text-[15px] font-semibold text-ink-1 mt-3 mb-1.5 first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="font-display text-[14px] font-semibold text-ink-1 mt-3 mb-1.5 first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="font-display text-[13.5px] font-semibold text-ink-1 mt-2.5 mb-1 first:mt-0">
              {children}
            </h3>
          ),
          p: ({ children }) => <p className="my-1.5 leading-relaxed">{children}</p>,
          strong: ({ children }) => (
            <strong className="font-semibold text-ink-1">{children}</strong>
          ),
          em: ({ children }) => <em className="text-ink-2 italic">{children}</em>,
          ul: ({ children }) => (
            <ul className="my-1.5 ml-4 list-disc space-y-0.5 marker:text-ink-3">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="my-1.5 ml-4 list-decimal space-y-0.5 marker:text-ink-3">
              {children}
            </ol>
          ),
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          code: ({ children }) => (
            <code className="px-1 py-0.5 rounded bg-line-1 text-ink-1 text-[11.5px] font-mono">
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="my-2 p-2.5 rounded-md bg-line-1 text-[11.5px] font-mono overflow-x-auto whitespace-pre-wrap">
              {children}
            </pre>
          ),
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-info-700 hover:underline"
            >
              {children}
            </a>
          ),
          hr: () => <hr className="my-3 border-line-1" />,
          blockquote: ({ children }) => (
            <blockquote className="my-2 pl-3 border-l-2 border-line-2 text-ink-3 italic">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="my-2 overflow-x-auto">
              <table className="min-w-full text-[11.5px] border-collapse">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-line-2 px-2 py-1 bg-line-1 text-left font-medium">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-line-2 px-2 py-1">{children}</td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
