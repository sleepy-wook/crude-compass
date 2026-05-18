/**
 * MissionHero — Discovery 페이지 hero card (mission-centric redesign).
 *
 * 매니저가 5초 안에 "오늘 권고 + 신뢰도 + 액션"을 인지하도록 설계.
 * 3 state: proposed (신규 권고) · active (진행 중) · 관망 (mission 없음)
 *
 * Mission 정보 전체를 카드 하나에 통합 — 별도 detail page 없이 expand 가능.
 */
import { useState } from "react";
import {
  useMissionConfirm,
  useMissionPivot,
  useMissionReject,
} from "../lib/queries";
import { formatConfidence, formatRoundedScore } from "../lib/utils";
import type { Mission, PatternScoreCurrent } from "../lib/types";

type Mode = "HEDGE" | "OPPORTUNITY" | "STABLE";

export type TriggerKind = "daily_cron" | "price_spike" | "manual_query" | "manual_recommend";

interface TopSignal {
  signal_type: string;
  direction: "bullish" | "bearish" | "neutral";
  share_pct: number;
}

interface MissionHeroProps {
  cur: PatternScoreCurrent | null | undefined;
  topMission: Mission | null | undefined;
  topSignals: TopSignal[];
  triggerKind: TriggerKind;
  isLoading?: boolean;
  /** 분석 다시 요청 — MultiAgentTrace로 scroll */
  onRequestAnalysis?: () => void;
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

function buildReasoning(mode: Mode, topSignals: TopSignal[]): string {
  if (topSignals.length === 0) {
    if (mode === "STABLE") return "주요 시그널이 정상 범위에 있어 평시 비중 유지를 권장합니다.";
    return mode === "HEDGE"
      ? "위기 시그널이 누적되어 사전 방어를 권장합니다."
      : "약세 시그널이 누적되어 즉시 매수를 권장합니다.";
  }
  const action =
    mode === "HEDGE"
      ? "사전 방어를 권장합니다"
      : mode === "OPPORTUNITY"
        ? "즉시 매수를 권장합니다"
        : "관망을 권장합니다";
  const [s1, s2] = topSignals;
  const n1 = SIGNAL_NAME[s1.signal_type] ?? s1.signal_type;
  if (!s2) return `${n1}이 두드러져 ${action}.`;
  const n2 = SIGNAL_NAME[s2.signal_type] ?? s2.signal_type;
  return `${n1}과 ${n2}이 함께 누적되어 ${action}.`;
}

function modeLabel(mode: Mode): string {
  if (mode === "HEDGE") return "위험방어";
  if (mode === "OPPORTUNITY") return "기회포착";
  return "관망";
}

function modeChipColor(mode: Mode): string {
  if (mode === "HEDGE") return "bg-crisis-50 text-crisis-700";
  if (mode === "OPPORTUNITY") return "bg-opportunity-50 text-opportunity-700";
  return "bg-line-1 text-ink-3";
}

function triggerBadge(kind: TriggerKind, cur: PatternScoreCurrent | null | undefined) {
  switch (kind) {
    case "price_spike":
      return { tone: "alert" as const, label: "가격 급변동 감지, 재계산 중", pulse: true };
    case "manual_query":
      return { tone: "active" as const, label: "AI 분석 진행 중", pulse: true };
    case "manual_recommend":
      return { tone: "active" as const, label: "분석 완료", pulse: false };
    case "daily_cron":
    default: {
      const date = cur?.date ? cur.date.slice(5, 10).replace("-", "/") : null;
      return {
        tone: "neutral" as const,
        label: date ? `${date} 06:30 갱신` : "최신",
        pulse: false,
      };
    }
  }
}

export function MissionHero({
  cur,
  topMission,
  topSignals,
  triggerKind,
  isLoading,
  onRequestAnalysis,
}: MissionHeroProps) {
  const mode = decideMode(cur, topMission);
  const reasoning = buildReasoning(mode, topSignals);
  const badge = triggerBadge(triggerKind, cur);
  const score = cur?.pattern_score ?? null;
  const confidence = cur?.confidence_score ?? null;

  // Status 판정
  const status = topMission?.status;
  const isProposed = status === "proposed";
  const isActive =
    status === "active" || status === "on_track" || status === "at_risk";
  const isStable = mode === "STABLE" || !topMission;

  return (
    <section className="mb-16">
      {/* Top metadata strip */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-medium tracking-wide ${modeChipColor(mode)}`}
          >
            {modeLabel(mode)}
          </span>
          {isProposed && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-medium bg-ink-1 text-paper">
              신규 권고
            </span>
          )}
          {isActive && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-medium bg-opportunity-50 text-opportunity-700">
              진행 중
            </span>
          )}
        </div>
        <TriggerBadge {...badge} />
      </div>

      {/* Loading state */}
      {isLoading && <HeroSkeleton />}

      {/* Stable mode (no mission) */}
      {!isLoading && isStable && (
        <StableHero
          score={score}
          confidence={confidence}
          reasoning={reasoning}
          onRequestAnalysis={onRequestAnalysis}
        />
      )}

      {/* Mission card */}
      {!isLoading && !isStable && topMission && (
        <MissionCard
          mission={topMission}
          mode={mode}
          score={score}
          confidence={confidence}
          reasoning={reasoning}
          isProposed={isProposed}
          isActive={isActive}
        />
      )}
    </section>
  );
}

function TriggerBadge({
  tone,
  label,
  pulse,
}: {
  tone: "neutral" | "alert" | "active";
  label: string;
  pulse: boolean;
}) {
  const textColor =
    tone === "alert" ? "text-crisis-700" : tone === "active" ? "text-opportunity-700" : "text-ink-3";
  const dotColor =
    tone === "alert"
      ? "bg-crisis-500"
      : tone === "active"
        ? "bg-opportunity-500"
        : "bg-ink-3/40";
  return (
    <div className={`inline-flex items-center gap-2 text-[12px] ${textColor}`}>
      <span
        className={`inline-block w-1.5 h-1.5 rounded-full ${dotColor} ${pulse ? "animate-pulse" : ""}`}
      />
      <span>{label}</span>
    </div>
  );
}

function HeroSkeleton() {
  return (
    <div className="bg-panel border border-line-1 rounded-2xl p-10">
      <div className="h-10 bg-line-1 rounded animate-pulse mb-5 w-3/4" />
      <div className="h-5 bg-line-1 rounded animate-pulse w-1/2" />
    </div>
  );
}

function StableHero({
  score,
  confidence,
  reasoning,
  onRequestAnalysis,
}: {
  score: number | null;
  confidence: number | null;
  reasoning: string;
  onRequestAnalysis?: () => void;
}) {
  return (
    <div className="bg-panel border border-line-1 rounded-2xl p-10">
      <h1 className="font-display text-[32px] md:text-[40px] lg:text-[48px] font-semibold tracking-tight leading-[1.15] text-ink-1 mb-4">
        오늘은 큰 신호 없음
      </h1>
      <p className="text-base text-ink-2 leading-relaxed mb-8 max-w-2xl">
        {reasoning}
      </p>
      <div className="flex flex-wrap items-center gap-x-8 gap-y-2 mb-8 pb-8 border-b border-line-1">
        <Stat label="위기 점수" value={formatRoundedScore(score)} />
        <Stat label="신뢰도" value={formatConfidence(confidence)} />
      </div>
      {onRequestAnalysis && (
        <button
          type="button"
          onClick={onRequestAnalysis}
          className="inline-flex items-center px-5 py-2.5 rounded-md bg-ink-1 text-paper text-[13px] font-medium hover:bg-ink-2 transition-colors"
        >
          AI 분석 다시 요청
        </button>
      )}
    </div>
  );
}

function MissionCard({
  mission,
  mode,
  score,
  confidence,
  reasoning,
  isProposed,
  isActive,
}: {
  mission: Mission;
  mode: Mode;
  score: number | null;
  confidence: number | null;
  reasoning: string;
  isProposed: boolean;
  isActive: boolean;
}) {
  const confirmMut = useMissionConfirm();
  const rejectMut = useMissionReject();
  const pivotMut = useMissionPivot();
  const [showDetail, setShowDetail] = useState(false);
  const [showPivot, setShowPivot] = useState(false);
  const [pivotReason, setPivotReason] = useState("");

  const baseline = mode === "HEDGE" ? 60 : 40;
  const target = mission.target_pct ?? baseline;
  const action = mode === "HEDGE" ? "장기계약 비중" : "즉시구매 비중";

  // Simulation ROI — 3 시나리오 정렬
  const roiEntries = Object.entries(mission.simulation_roi || {});

  return (
    <div className="bg-panel border border-line-1 rounded-2xl p-8 md:p-10">
      {/* Headline */}
      <div className="text-[13px] text-ink-3 mb-3">
        오늘 두바이 {action}
      </div>
      <h1 className="font-display text-[36px] md:text-[48px] lg:text-[56px] font-semibold tracking-tight leading-[1.1] text-ink-1 mb-5">
        {baseline}% <span className="text-ink-3 mx-2">→</span> {target}%
      </h1>
      <p className="text-base text-ink-2 leading-relaxed mb-8 max-w-2xl">{reasoning}</p>

      {/* Stat row */}
      <div className="flex flex-wrap items-center gap-x-10 gap-y-4 mb-8 pb-8 border-b border-line-1">
        <Stat label="위기 점수" value={formatRoundedScore(score)} />
        <Stat label="신뢰도" value={formatConfidence(confidence)} />
        <Stat label="기간" value={`${mission.duration_days}일`} />
      </div>

      {/* Simulation ROI strip */}
      {roiEntries.length > 0 && (
        <div className="mb-8 pb-8 border-b border-line-1">
          <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-3">
            예상 시나리오
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {roiEntries.map(([scenario, roi]) => (
              <div key={scenario}>
                <div className="text-xs text-ink-3 mb-1">{scenario}</div>
                <div
                  className={`font-display text-xl font-semibold ${
                    roi > 0 ? "text-opportunity-700" : roi < 0 ? "text-crisis-700" : "text-ink-1"
                  }`}
                >
                  {roi > 0 ? "+" : ""}
                  {roi}억원
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      {isProposed && (
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() =>
              confirmMut.mutate({ id: mission.mission_id, version: mission.version })
            }
            disabled={confirmMut.isPending}
            className="px-5 py-2.5 rounded-md bg-ink-1 text-paper text-[13px] font-medium hover:bg-ink-2 disabled:opacity-50 transition-colors"
          >
            {confirmMut.isPending ? "처리 중..." : "권고 채택"}
          </button>
          <button
            type="button"
            onClick={() =>
              rejectMut.mutate({
                id: mission.mission_id,
                version: mission.version,
                reason: "매니저 거절",
              })
            }
            disabled={rejectMut.isPending}
            className="px-5 py-2.5 rounded-md border border-line-2 text-ink-2 text-[13px] font-medium hover:bg-line-1 transition-colors"
          >
            거절
          </button>
          <button
            type="button"
            onClick={() => setShowDetail((s) => !s)}
            className="px-5 py-2.5 rounded-md text-ink-3 text-[13px] font-medium hover:text-ink-1 transition-colors"
          >
            {showDetail ? "접기" : "세부 보기"}
          </button>
        </div>
      )}

      {isActive && (
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => setShowPivot((s) => !s)}
            className="px-5 py-2.5 rounded-md border border-line-2 text-ink-2 text-[13px] font-medium hover:bg-line-1 transition-colors"
          >
            방향 전환
          </button>
          <button
            type="button"
            onClick={() => setShowDetail((s) => !s)}
            className="px-5 py-2.5 rounded-md text-ink-3 text-[13px] font-medium hover:text-ink-1 transition-colors"
          >
            {showDetail ? "접기" : "세부 보기"}
          </button>
        </div>
      )}

      {/* Pivot form */}
      {showPivot && (
        <div className="mt-6 pt-6 border-t border-line-1">
          <div className="text-sm text-ink-2 mb-3">
            현재 {modeLabel(mode)} → {mode === "HEDGE" ? "기회포착" : "위험방어"}으로 전환
          </div>
          <textarea
            value={pivotReason}
            onChange={(e) => setPivotReason(e.target.value)}
            placeholder="전환 사유 (예: 휴전 임박 + 미국 비축유 방출로 약세 신호 누적)"
            rows={2}
            className="w-full text-sm p-3 border border-line-2 rounded-md focus:outline-none focus:border-ink-3 mb-3"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() =>
                pivotMut.mutate({
                  id: mission.mission_id,
                  version: mission.version,
                  pivot_action: "pivot",
                  to_type: mission.mission_type === "HEDGE" ? "OPPORTUNITY" : "HEDGE",
                  reason: pivotReason || "방향 전환",
                })
              }
              disabled={pivotMut.isPending || !pivotReason}
              className="px-4 py-2 rounded-md bg-opportunity-600 text-white text-[13px] font-medium hover:bg-opportunity-700 disabled:opacity-50"
            >
              전환 실행
            </button>
            <button
              type="button"
              onClick={() => setShowPivot(false)}
              className="px-4 py-2 rounded-md border border-line-2 text-ink-3 text-[13px]"
            >
              취소
            </button>
          </div>
        </div>
      )}

      {/* Detail expand */}
      {showDetail && (
        <div className="mt-6 pt-6 border-t border-line-1 space-y-5">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">AI 추론 근거</div>
            <p className="text-sm text-ink-1 leading-relaxed">{mission.reasoning}</p>
          </div>
          {mission.pivot_history.length > 0 && (
            <div>
              <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">방향 전환 이력</div>
              <div className="space-y-2">
                {mission.pivot_history.map((p, i) => (
                  <div key={i} className="text-sm text-ink-2">
                    <span className="text-ink-3 mr-2">{p.occurred_at?.slice(5, 10)}</span>
                    {modeLabel(p.from_type as Mode)} → {modeLabel(p.to_type as Mode)} · {p.reason}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error feedback */}
      {(confirmMut.error || rejectMut.error || pivotMut.error) && (
        <div className="mt-4 text-xs text-crisis-700">
          요청 처리 중 오류가 발생했습니다.
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-1">{label}</div>
      <div className="font-display text-2xl font-semibold text-ink-1">{value}</div>
    </div>
  );
}
