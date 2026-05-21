/**
 * SelectedReportDetail — Decision Room 우측 (reports model 2026-05-21).
 *
 * 구성:
 *  - Pills: trigger type + status + age
 *  - Headline + Summary
 *  - Reasoning (key_signals / logic / risk_factors) collapsible
 *  - Related signals (있을 때)
 *  - Thread (parent_id chain, 자식 reports)
 *  - Actions: [보관] [추가 조사] [drop]
 */
import { useState } from "react";
import { Activity, AlertTriangle, DollarSign, Lightbulb, ListTree, Network, Newspaper, Target } from "lucide-react";
import type { ReactNode } from "react";
import type { ComponentType } from "react";
import { cn } from "../lib/utils";
import { useDropReport, useInvestigateReport, useKeepReport, useReportDetail } from "../lib/queries";
import { MarkdownBody, labelTool } from "./ChatMessage";
import type { Report, TriggerType } from "../lib/types";

/**
 * AI 응답에 새는 raw markup 정리 — footnote([^x]), pipe leak(|0|..|HEDGE|),
 * <name> 태그, 과다 공백. (Supervisor 응답이 한글 prose에 SQL/citation 잔재를 섞는 경우 대응)
 */
function cleanReportText(s: string | null | undefined): string {
  if (!s) return "";
  return s
    .replace(/<name>[^<]*<\/name>/g, "")
    .replace(/\[\^[^\]]+\]/g, "")
    .replace(/\|[^\n|]{0,40}(?:\|[^\n|]{0,40}){2,}/g, "")
    // agentic 서두 — 첫 문장에 확인/조회/분석 등 + "겠습니다"면 제거
    .replace(/^\s*[^.\n]*(?:확인|조회|분석|검토|살펴|파악|검증)[^.\n]*겠습니다[.!]\s*/, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

interface Props {
  reportId: string | undefined;
  isLoading: boolean;
  /**
   * thread 자식 보고서 클릭 시 콜백.
   * Dashboard: inbox에 있으면 선택 변경, 없으면 /archive로 navigate.
   * ArchivePage: archive list에 있으면 선택 변경, 없으면 다른 status filter로.
   */
  onSelectThread?: (reportId: string) => void;
}

interface TriggerMeta {
  Icon: ComponentType<{ className?: string }>;
  label: string;
  pillClass: string;
}

const TRIGGER_META: Record<TriggerType, TriggerMeta> = {
  gdelt_signal: { Icon: Newspaper, label: "뉴스 시그널", pillClass: "bg-info-50 text-info-700 border-info-200" },
  price_spike: { Icon: DollarSign, label: "가격 변동", pillClass: "bg-opportunity-50 text-opportunity-700 border-opportunity-200" },
  pattern_drift: { Icon: Activity, label: "추세 변화", pillClass: "bg-amber-50 text-amber-700 border-amber-200" },
};

const REC_TONE: Record<string, string> = {
  HOLD: "bg-line-1 text-ink-2 border-line-2",
  "DEFER SPOT": "bg-amber-50 text-amber-700 border-amber-200",
  "ACCELERATE SPOT": "bg-opportunity-50 text-opportunity-700 border-opportunity-200",
  "REVIEW TERM": "bg-info-50 text-info-700 border-info-200",
  HEDGE: "bg-crisis-50 text-crisis-700 border-crisis-200",
  DIVERSIFY: "bg-info-50 text-info-700 border-info-200",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "검토 대기",
  kept: "활성화됨",
  archived: "보관됨",
  dropped: "Drop됨",
  ai_dropped: "AI Drop됨",
};

function ageLabel(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "방금";
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  return `${Math.floor(diff / 86400)}일 전`;
}

export function SelectedReportDetail({ reportId, isLoading, onSelectThread }: Props) {
  const { data, isLoading: detailLoading } = useReportDetail(reportId);

  if (isLoading || detailLoading) {
    return (
      <div className="bg-white border border-line-2 rounded-2xl p-8 flex items-center text-sm text-ink-3 h-[680px] shadow-sm">
        불러오는 중...
      </div>
    );
  }

  if (!reportId || !data) {
    return (
      <div className="bg-white border border-line-2 rounded-2xl p-6 h-[680px] flex flex-col justify-center shadow-sm">
        <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">보고서</div>
        <div className="text-base text-ink-1 mb-3">선택된 보고서 없음</div>
        <p className="text-[13px] text-ink-3 leading-relaxed">
          좌측에서 보고서를 선택하거나, 새 트리거 신호 발생 시 자동으로 보고서가 추가됩니다.
        </p>
      </div>
    );
  }

  // 선택된 report를 thread에서 찾음. 없으면 root 사용.
  const selected = data.thread.find((r) => r.report_id === reportId) ?? data.root;
  const otherInThread = data.thread.filter((r) => r.report_id !== selected.report_id);

  return <DetailBody selected={selected} thread={otherInThread} onSelectThread={onSelectThread} />;
}

function DetailBody({
  selected,
  thread,
  onSelectThread,
}: {
  selected: Report;
  thread: Report[];
  onSelectThread?: (reportId: string) => void;
}) {
  const meta = TRIGGER_META[selected.trigger_type];
  const Icon = meta.Icon;
  const recTone = selected.recommendation ? REC_TONE[selected.recommendation] : null;
  const isPending = selected.status === "pending";

  const keepMut = useKeepReport();
  const dropMut = useDropReport();
  const investigateMut = useInvestigateReport();
  const [showReasoning, setShowReasoning] = useState(true);

  // 판단 논리가 본문(summary)과 동일하면 중복이므로 숨김 (investigate child report 케이스).
  const r = selected.reasoning;
  const logicShown =
    !!r?.logic && cleanReportText(r.logic) !== cleanReportText(selected.summary);
  const hasReasoning = !!(
    r &&
    (logicShown ||
      (r.key_signals?.length ?? 0) > 0 ||
      (r.risk_factors?.length ?? 0) > 0 ||
      r.recommendation_text ||
      (r.agent_bricks_tools?.length ?? 0) > 0)
  );

  return (
    <div className="bg-white border border-line-2 rounded-2xl p-6 flex flex-col h-[680px] overflow-y-auto shadow-sm">
      {/* Pills row */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span
          className={cn(
            "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] tracking-wider border font-medium",
            meta.pillClass,
          )}
        >
          <Icon className="w-3 h-3" />
          {meta.label}
        </span>
        {selected.recommendation && recTone && (
          <span
            className={cn(
              "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] tracking-wider border font-medium",
              recTone,
            )}
          >
            {selected.recommendation}
          </span>
        )}
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] tracking-wider border font-medium bg-transparent text-ink-3 border-line-2">
          {STATUS_LABEL[selected.status] || selected.status}
        </span>
        <span className="ml-auto text-[10px] text-ink-3 tabular-nums">
          {ageLabel(selected.created_at)} · #{selected.report_id.slice(0, 6)}
        </span>
      </div>

      {/* Headline */}
      <h3 className="font-display text-[17px] font-semibold text-ink-1 leading-snug mb-3">
        {selected.headline}
      </h3>

      {/* Summary — markdown 렌더 + raw markup 정제 */}
      <div className="text-[13px] text-ink-2 mb-4">
        <MarkdownBody content={cleanReportText(selected.summary)} />
      </div>

      {/* Reasoning collapsible */}
      {hasReasoning && (
        <div className="border-t border-line-1 pt-3 mb-4">
          <button
            type="button"
            onClick={() => setShowReasoning((v) => !v)}
            className="text-[10px] uppercase tracking-wider text-ink-3 hover:text-ink-1 transition-colors mb-2"
          >
            AI 분석 근거 {showReasoning ? "▲" : "▼"}
          </button>
          {showReasoning && (
            <div className="space-y-3 text-[12.5px] text-ink-2">
              {selected.reasoning.key_signals && selected.reasoning.key_signals.length > 0 && (
                <ReasoningBlock
                  icon={<ListTree className="w-3 h-3" />}
                  label="핵심 신호"
                  tone="info"
                >
                  <ul className="space-y-0.5 ml-3 list-disc">
                    {selected.reasoning.key_signals.map((s, i) => (
                      <li key={i} className="leading-snug">{s}</li>
                    ))}
                  </ul>
                </ReasoningBlock>
              )}
              {logicShown && (
                <ReasoningBlock
                  icon={<Lightbulb className="w-3 h-3" />}
                  label="판단 논리"
                  tone="ink"
                >
                  <div className="text-[12.5px]">
                    <MarkdownBody content={cleanReportText(selected.reasoning.logic)} />
                  </div>
                </ReasoningBlock>
              )}
              {selected.reasoning.risk_factors && selected.reasoning.risk_factors.length > 0 && (
                <ReasoningBlock
                  icon={<AlertTriangle className="w-3 h-3" />}
                  label="위험 요인"
                  tone="crisis"
                >
                  <ul className="space-y-0.5 ml-3 list-disc">
                    {selected.reasoning.risk_factors.map((s, i) => (
                      <li key={i} className="leading-snug">{s}</li>
                    ))}
                  </ul>
                </ReasoningBlock>
              )}
              {selected.reasoning.recommendation_text && (
                <ReasoningBlock
                  icon={<Target className="w-3 h-3" />}
                  label="권고"
                  tone="recommend"
                >
                  <p className="text-ink-1 leading-relaxed">{selected.reasoning.recommendation_text}</p>
                </ReasoningBlock>
              )}
              {selected.reasoning.agent_bricks_tools && selected.reasoning.agent_bricks_tools.length > 0 && (
                <ReasoningBlock
                  icon={<Network className="w-3 h-3" />}
                  label="Agent Bricks Supervisor"
                  tone="info"
                >
                  <div className="text-[11.5px] text-ink-3 mb-2">
                    {selected.reasoning.agent_bricks_tools.length} sub-agent 호출됨
                  </div>
                  <ul className="space-y-1">
                    {selected.reasoning.agent_bricks_tools.map((t, i) => (
                      <li key={`${t.name}-${i}`} className="flex items-baseline gap-2 text-[12px]">
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9.5px] font-semibold uppercase tracking-wider bg-info-100 text-info-700 shrink-0">
                          {labelTool(t.name)}
                        </span>
                        {t.preview && (
                          <span className="text-ink-3 truncate">{t.preview}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </ReasoningBlock>
              )}
            </div>
          )}
        </div>
      )}

      {/* Related signals */}
      {selected.related_signals && selected.related_signals.length > 0 && (
        <div className="border-t border-line-1 pt-3 mb-4">
          <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-2">관련 신호 ({selected.related_signals.length})</div>
          <ul className="space-y-1 text-[12px]">
            {selected.related_signals.slice(0, 4).map((s, i) => (
              <li key={i} className="flex items-baseline gap-2 text-ink-2">
                <span className="text-ink-3 shrink-0 text-[10.5px]">·</span>
                <span className="truncate">{s.title || "—"}</span>
                {s.direction && (
                  <span className={cn(
                    "shrink-0 text-[10px] px-1 py-0.5 rounded",
                    s.direction === "bullish" ? "bg-crisis-50 text-crisis-700"
                      : s.direction === "bearish" ? "bg-opportunity-50 text-opportunity-700"
                      : "bg-line-1 text-ink-3",
                  )}>
                    {s.direction === "bullish" ? "위험" : s.direction === "bearish" ? "안정" : "중립"}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Thread (다른 자식 reports) */}
      {thread.length > 0 && (
        <div className="border-t border-line-1 pt-3 mb-4">
          <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-2">
            연관 보고서 ({thread.length})
          </div>
          <ul className="space-y-1.5 text-[12px]">
            {thread.map((t) => {
              const clickable = !!onSelectThread;
              const inner = (
                <>
                  <span className="text-ink-3 shrink-0 text-[10.5px] mt-0.5">↳</span>
                  <div className="flex-1 min-w-0">
                    <div className="truncate text-ink-1">{t.headline}</div>
                    <div className="text-[10.5px] text-ink-3 mt-0.5">
                      {ageLabel(t.created_at)} · {STATUS_LABEL[t.status]}
                    </div>
                  </div>
                  {clickable && (
                    <span className="text-ink-3 shrink-0 text-[12px] mt-0.5" aria-hidden>
                      ›
                    </span>
                  )}
                </>
              );
              return (
                <li key={t.report_id}>
                  {clickable ? (
                    <button
                      type="button"
                      onClick={() => onSelectThread!(t.report_id)}
                      className="w-full flex items-start gap-2 text-ink-2 text-left rounded-md px-1 -mx-1 py-0.5 hover:bg-line-1 transition-colors"
                    >
                      {inner}
                    </button>
                  ) : (
                    <div className="flex items-start gap-2 text-ink-2">{inner}</div>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="mt-auto pt-4 border-t border-line-1 flex items-center gap-2 flex-wrap">
        <button
          type="button"
          onClick={() => keepMut.mutate(selected.report_id)}
          disabled={!isPending || keepMut.isPending}
          className={cn(
            "px-3.5 py-2 rounded-md text-[12px] font-semibold transition-colors",
            "bg-ink-1 text-paper hover:bg-ink-2 disabled:opacity-40 disabled:cursor-not-allowed",
          )}
          title="활성화 — 내일 일일 보고서 input으로 사용"
        >
          {keepMut.isPending ? "활성화 중..." : "활성화"}
        </button>
        <button
          type="button"
          onClick={() => investigateMut.mutate(selected.report_id)}
          disabled={investigateMut.isPending || selected.status === "dropped"}
          title="Agent Bricks Supervisor가 Genie · Knowledge Assistant · 권고 sub-agent로 cross-check (10-30초)"
          className={cn(
            "px-3 py-2 rounded-md text-[12px] font-medium border transition-colors",
            "border-line-2 bg-white text-ink-1 hover:bg-line-1 disabled:opacity-40 disabled:cursor-not-allowed",
          )}
        >
          {investigateMut.isPending ? (
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full border-2 border-ink-3 border-t-transparent animate-spin" />
              Supervisor 호출 중...
            </span>
          ) : (
            "추가 조사"
          )}
        </button>
        <button
          type="button"
          onClick={() => dropMut.mutate(selected.report_id)}
          disabled={!isPending || dropMut.isPending}
          className={cn(
            "px-3 py-2 rounded-md text-[12px] font-medium border transition-colors",
            "border-line-2 bg-white text-crisis-700 hover:bg-crisis-50 disabled:opacity-40 disabled:cursor-not-allowed",
          )}
        >
          {dropMut.isPending ? "drop 중..." : "Drop"}
        </button>
      </div>
    </div>
  );
}

type ReasoningTone = "info" | "ink" | "crisis" | "recommend";

const REASONING_TONE: Record<ReasoningTone, { card: string; chip: string }> = {
  info: {
    card: "border-info-100 bg-info-50/40",
    chip: "bg-info-50 text-info-700",
  },
  ink: {
    card: "border-line-1 bg-paper",
    chip: "bg-line-1 text-ink-2",
  },
  crisis: {
    card: "border-crisis-100 bg-crisis-50/40",
    chip: "bg-crisis-50 text-crisis-700",
  },
  recommend: {
    card: "border-ink-1/15 bg-ink-1/[0.04]",
    chip: "bg-ink-1 text-paper",
  },
};

function ReasoningBlock({
  icon,
  label,
  tone,
  children,
}: {
  icon: ReactNode;
  label: string;
  tone: ReasoningTone;
  children: ReactNode;
}) {
  const t = REASONING_TONE[tone];
  return (
    <div className={cn("rounded-md border px-3 py-2.5", t.card)}>
      <div className={cn(
        "inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider mb-1.5",
        t.chip,
      )}>
        {icon}
        {label}
      </div>
      <div className="text-ink-2">{children}</div>
    </div>
  );
}
