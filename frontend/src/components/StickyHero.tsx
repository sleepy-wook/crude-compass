/**
 * StickyHero — Discovery sticky hero band.
 * Linear/Stripe 풍 절제 hero: score+mode prominent, 자연어 추론, backend variable 노출 0.
 */
import { formatConfidence, formatRoundedScore } from "../lib/utils";
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

const SIGNAL_NAME: Record<string, string> = {
  news_tone: "호르무즈 긴장",
  eia_inventory: "미국 재고 변동",
  opec_momr: "OPEC 공급 시그널",
  fx_krw_usd: "원화 약세",
  price_spike: "유가 급변동",
};

function decideMode(
  cur: PatternScoreCurrent | null | undefined,
  topMission: Mission | null | undefined,
): Mode {
  if (topMission?.mission_type === "HEDGE") return "HEDGE";
  if (topMission?.mission_type === "OPPORTUNITY") return "OPPORTUNITY";
  if (cur?.mission_type === "HEDGE") return "HEDGE";
  if (cur?.mission_type === "OPPORTUNITY") return "OPPORTUNITY";
  return "STABLE";
}

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

/** Subhead — 자연어 reasoning (arrow noise 제거). */
function buildSubhead(mode: Mode, topSignals: TopSignal[]): string {
  if (topSignals.length === 0) {
    if (mode === "STABLE") return "주요 시그널 정상 범위, 관망을 권장합니다";
    return mode === "HEDGE"
      ? "위기 시그널이 누적되어 사전 방어를 권장합니다"
      : "약세 시그널이 누적되어 즉시 매수를 권장합니다";
  }
  const action =
    mode === "HEDGE"
      ? "사전 방어를 권장합니다"
      : mode === "OPPORTUNITY"
        ? "즉시 매수를 권장합니다"
        : "관망을 권장합니다";
  const [s1, s2] = topSignals;
  const name1 = SIGNAL_NAME[s1.signal_type] ?? s1.signal_type;
  if (!s2) {
    return `${name1}이 두드러져 ${action}`;
  }
  const name2 = SIGNAL_NAME[s2.signal_type] ?? s2.signal_type;
  return `${name1}과 ${name2}이 함께 누적되어 ${action}`;
}

function badgeVariant(
  kind: TriggerKind,
  cur: PatternScoreCurrent | null | undefined,
): { tone: "neutral" | "alert" | "active"; wording: string; pulse: boolean } {
  switch (kind) {
    case "price_spike":
      return { tone: "alert", wording: "유가 급변동 감지, 재계산 중", pulse: true };
    case "manual_query":
      return { tone: "active", wording: "분석 진행 중", pulse: true };
    case "manual_recommend":
      return { tone: "active", wording: "분석 완료", pulse: false };
    case "daily_cron":
    default: {
      const date = cur?.date ? cur.date.slice(5, 10).replace("-", "/") : null;
      return {
        tone: "neutral",
        wording: date ? `${date} 06:30 갱신` : "최신",
        pulse: false,
      };
    }
  }
}

function modeChipColor(mode: Mode): string {
  if (mode === "HEDGE") return "bg-crisis-50 text-crisis-700";
  if (mode === "OPPORTUNITY") return "bg-opportunity-50 text-opportunity-700";
  return "bg-line-1 text-ink-3";
}

function modeLabel(mode: Mode): string {
  if (mode === "HEDGE") return "위험방어";
  if (mode === "OPPORTUNITY") return "기회포착";
  return "관망";
}

function scoreColor(mode: Mode): string {
  if (mode === "HEDGE") return "text-crisis-700";
  if (mode === "OPPORTUNITY") return "text-opportunity-700";
  return "text-ink-2";
}

export function StickyHero({
  cur,
  topMission,
  topSignals,
  triggerKind,
  isLoading,
}: StickyHeroProps) {
  const mode = decideMode(cur, topMission);
  const h1 = buildH1(mode, topMission);
  const subhead = buildSubhead(mode, topSignals);
  const badge = badgeVariant(triggerKind, cur);
  const score = cur?.pattern_score ?? null;

  const badgeToneClass =
    badge.tone === "alert"
      ? "text-crisis-700"
      : badge.tone === "active"
        ? "text-opportunity-700"
        : "text-ink-3";
  const badgeDotClass =
    badge.tone === "alert"
      ? "bg-crisis-500"
      : badge.tone === "active"
        ? "bg-opportunity-500"
        : "bg-ink-3/40";

  return (
    <div className="sticky top-0 z-40 -mx-8 px-8 backdrop-blur-xl bg-paper/85 border-b border-line-1">
      <div className="max-w-5xl mx-auto py-7">
        {/* Top row — mode + score (왼쪽), trigger badge (오른쪽) */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <span
              className={`inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-medium tracking-wide ${modeChipColor(mode)}`}
            >
              {modeLabel(mode)}
            </span>
            {score != null && (
              <span className={`font-display text-[28px] font-semibold leading-none ${scoreColor(mode)}`}>
                {formatRoundedScore(score)}
              </span>
            )}
          </div>
          <div className={`inline-flex items-center gap-2 text-[12px] ${badgeToneClass}`}>
            <span
              className={`inline-block w-1.5 h-1.5 rounded-full ${badgeDotClass} ${badge.pulse ? "animate-pulse" : ""}`}
            />
            <span>{badge.wording}</span>
          </div>
        </div>

        {/* h1 */}
        {isLoading ? (
          <div className="font-display text-2xl text-ink-3 mb-3">불러오는 중</div>
        ) : (
          <h1 className="font-display text-[28px] md:text-[36px] lg:text-[44px] font-semibold tracking-tight mb-3 leading-[1.15] text-ink-1">
            {h1}
          </h1>
        )}

        {/* Subhead — 자연어 */}
        {!isLoading && (
          <p className="text-[15px] md:text-base text-ink-2 leading-relaxed max-w-3xl">
            {subhead}
          </p>
        )}

        {/* Meta strip — bottom, 절제된 정보 */}
        <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[12px] text-ink-3">
          <span>
            신뢰도 <span className="text-ink-1 font-medium">{formatConfidence(cur?.confidence_score)}</span>
          </span>
          {cur?.signal_count_90d != null && (
            <span>
              최근 90일 시그널{" "}
              <span className="text-ink-1 font-medium">{cur.signal_count_90d.toLocaleString()}건</span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
