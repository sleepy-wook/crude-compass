/**
 * StickyHero — Discovery 페이지 §1 결정 (sticky band ~280px)
 *
 * spec: docs/superpowers/specs/2026-05-18-d0-ai-assistant-narrative-redesign.md §4
 *
 * 구성:
 *   ┌──────────────────────────────────────────────┐
 *   │ Crude Compass            [ trigger badge ]    │
 *   │                                                │
 *   │ 오늘 두바이 장기계약 비중 60% → 75%   ← h1     │
 *   │ 호르무즈 긴장↑ + spread↓ → 사전 방어 권고      │
 *   │                                                │
 *   │ 신뢰도 91% · pattern_score 78 · [HEDGE 78]    │
 *   └──────────────────────────────────────────────┘
 *
 * Mode-aware morph: HEDGE/OPPORTUNITY/STABLE → typography/chip 색만.
 *   bg는 panel(white) 고정 (산만함 회피).
 */
import { formatConfidence, formatRoundedScore, missionTypeLabel } from "../lib/utils";
import type { Mission, PatternScoreCurrent } from "../lib/types";

type Mode = "HEDGE" | "OPPORTUNITY" | "STABLE";

export type TriggerKind = "daily_cron" | "price_spike" | "manual_query" | "manual_recommend";

interface TopSignal {
  signal_type: string;
  direction: "bullish" | "bearish" | "neutral";
  share_pct: number;
}

interface StickyHeroProps {
  cur: PatternScoreCurrent | null | undefined;
  topMission: Mission | null | undefined;
  topSignals: TopSignal[];
  triggerKind: TriggerKind;
  isLoading?: boolean;
}

const SIGNAL_LABEL_KO: Record<string, string> = {
  news_tone: "호르무즈 긴장",
  eia_inventory: "EIA 미국 재고",
  opec_momr: "OPEC MOMR",
  fx_krw_usd: "USD/KRW 환율",
  price_spike: "유가 급변동",
};

/** Mode 결정 우선순위: activeMission > cur.mission_type > STABLE */
function decideMode(cur: PatternScoreCurrent | null | undefined, topMission: Mission | null | undefined): Mode {
  if (topMission?.mission_type === "HEDGE") return "HEDGE";
  if (topMission?.mission_type === "OPPORTUNITY") return "OPPORTUNITY";
  if (cur?.mission_type === "HEDGE") return "HEDGE";
  if (cur?.mission_type === "OPPORTUNITY") return "OPPORTUNITY";
  return "STABLE";
}

/** Hero h1 — 실제 mission 데이터에 align. Fictional quantity 금지. */
function buildH1(mode: Mode, topMission: Mission | null | undefined): string {
  if (mode === "STABLE" || !topMission) {
    return "오늘은 큰 신호 없음, 통상 운영";
  }
  const crude = mode === "HEDGE" ? "두바이" : "WTI";
  const action = mode === "HEDGE" ? "장기계약 비중" : "즉시구매 비중";
  const baseline = mode === "HEDGE" ? 60 : 40;
  const target = topMission.target_pct ?? baseline;
  return `오늘 ${crude} ${action} ${baseline}% → ${target}%`;
}

/** Subhead — top 2 signal direction 추론 chain. */
function buildSubhead(mode: Mode, topSignals: TopSignal[]): string {
  if (topSignals.length === 0) {
    if (mode === "STABLE") return "주요 시그널 정상 범위 — 관망";
    return mode === "HEDGE" ? "위기 시그널 누적 — 사전 방어 권고" : "약세 시그널 누적 — 기회 매수 권고";
  }
  const action =
    mode === "HEDGE" ? "사전 방어 권고" : mode === "OPPORTUNITY" ? "기회 매수 권고" : "관망 권고";
  const [s1, s2] = topSignals;
  const label1 = SIGNAL_LABEL_KO[s1.signal_type] ?? s1.signal_type;
  const arrow1 = s1.direction === "bullish" ? "↑" : s1.direction === "bearish" ? "↓" : "·";
  if (!s2) {
    return `${label1}${arrow1} → ${action}`;
  }
  const label2 = SIGNAL_LABEL_KO[s2.signal_type] ?? s2.signal_type;
  const arrow2 = s2.direction === "bullish" ? "↑" : s2.direction === "bearish" ? "↓" : "·";
  return `${label1}${arrow1} + ${label2}${arrow2}  →  ${action}`;
}

/** Trigger badge variants — wording + color. */
function badgeVariant(kind: TriggerKind, cur: PatternScoreCurrent | null | undefined): {
  bg: string;
  text: string;
  dot: string | null;
  wording: string;
} {
  switch (kind) {
    case "price_spike":
      return {
        bg: "bg-crisis-50",
        text: "text-crisis-700",
        dot: "bg-crisis-500 animate-pulse",
        wording: "● 가격 spike 감지 · 재계산 중",
      };
    case "manual_query":
      return {
        bg: "bg-opportunity-50",
        text: "text-opportunity-700",
        dot: "bg-opportunity-500 animate-pulse",
        wording: "● 매니저 요청 · Multi-Agent 추론 중",
      };
    case "manual_recommend":
      return {
        bg: "bg-opportunity-50",
        text: "text-opportunity-700",
        dot: "bg-opportunity-500",
        wording: "● 수동 재호출 완료",
      };
    case "daily_cron":
    default: {
      const date = cur?.date ? cur.date.slice(5, 10).replace("-", "/") : "오늘";
      return {
        bg: "bg-line-1",
        text: "text-ink-3",
        dot: null,
        wording: `${date} 정기 갱신`,
      };
    }
  }
}

/** Mode-aware text color (h1). */
function modeTextColor(mode: Mode): string {
  if (mode === "HEDGE") return "text-ink";
  if (mode === "OPPORTUNITY") return "text-opportunity-700";
  return "text-ink-2";
}

/** Mode chip styles. */
function modeChipStyle(mode: Mode): string {
  if (mode === "HEDGE") return "bg-crisis-50 text-crisis-700 border-crisis-100";
  if (mode === "OPPORTUNITY") return "bg-opportunity-50 text-opportunity-700 border-opportunity-100";
  return "bg-line-1 text-ink-3 border-line-2";
}

export function StickyHero({ cur, topMission, topSignals, triggerKind, isLoading }: StickyHeroProps) {
  const mode = decideMode(cur, topMission);
  const h1 = buildH1(mode, topMission);
  const subhead = buildSubhead(mode, topSignals);
  const badge = badgeVariant(triggerKind, cur);
  const score = cur?.pattern_score ?? null;

  return (
    <div className="sticky top-0 z-40 -mx-8 px-8 backdrop-blur-md bg-paper/90 border-b border-line-1">
      <div className="max-w-5xl mx-auto py-7">
        {/* Top row — logo + trigger badge */}
        <div className="flex items-center justify-between mb-5">
          <div className="text-[11px] uppercase tracking-[0.25em] text-ink-3 font-mono">
            Crude Compass
          </div>
          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono ${badge.bg} ${badge.text}`}
          >
            {badge.dot && <span className={`inline-block w-1.5 h-1.5 rounded-full ${badge.dot}`} />}
            <span>{badge.wording}</span>
          </div>
        </div>

        {/* h1 — mode-aware */}
        {isLoading ? (
          <div className="font-display text-3xl text-ink-3 mb-3">데이터 로딩...</div>
        ) : (
          <h1
            className={`font-display text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight mb-3 leading-tight transition-colors duration-300 ${modeTextColor(mode)}`}
          >
            {h1}
          </h1>
        )}

        {/* Subhead — 추론 chain */}
        {!isLoading && (
          <p className="text-sm md:text-base text-ink-2 mb-4 leading-relaxed">{subhead}</p>
        )}

        {/* Meta strip — mono */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[12px] font-mono text-ink-3">
          <span>신뢰도 {formatConfidence(cur?.confidence_score)}</span>
          <span className="text-line-2">·</span>
          <span>pattern_score {formatRoundedScore(score)}</span>
          <span className="text-line-2">·</span>
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[11px] font-medium ${modeChipStyle(mode)}`}
          >
            {mode === "STABLE" ? "관망" : missionTypeLabel(mode)} {formatRoundedScore(score)}
          </span>
          {cur?.signal_count_90d != null && (
            <>
              <span className="text-line-2">·</span>
              <span>90일 시그널 {cur.signal_count_90d.toLocaleString()}건</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
