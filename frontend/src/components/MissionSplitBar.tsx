/**
 * MissionSplitBar — Term/Spot 분할 시각화 (해커톤 D-15 사용자 요청).
 *
 * 시나리오 §4: K-Petroleum default Term 60% / Spot 40%.
 * Mission이 권고하는 비중을 평시 baseline과 비교해 한눈에.
 *
 * Layout (stacked horizontal):
 *   권고  ████████████████████████░░░░░░░░  Term 75%  | Spot 25%
 *   평시  ██████████████████░░░░░░░░░░░░░░  Term 60%  | Spot 40%   ← ghost (회색 dashed)
 *         (Term +15%p · Spot -15%p)
 *
 * size="compact": 1 row (권고만, 변화량 inline)
 * size="full":    2 row (권고 + 평시 baseline ghost), narration 분리
 */

type MissionType = "HEDGE" | "OPPORTUNITY";

interface Props {
  missionType: MissionType;
  /** target_pct: HEDGE면 Term ratio, OPPORTUNITY면 Spot ratio (AI 권고) */
  targetPct: number;
  /**
   * 현재 운영 중인 Term 비중 (회사가 실제로 가지고 있는 portfolio).
   * 이전 active mission의 target_pct 기반.
   * 데이터 없으면 평시 default 60 (시나리오 §4).
   */
  currentTermPct?: number;
  /** 현재 운영 비중의 출처 — "지난 mission 5/15 기록" 또는 "회사 평시 기준 (history 없음)" */
  currentSourceLabel?: string;
  size?: "compact" | "full";
}

interface Split {
  termTarget: number;
  spotTarget: number;
  termCurrent: number;
  spotCurrent: number;
  termDelta: number;
  spotDelta: number;
}

function computeSplit(
  missionType: MissionType,
  targetPct: number,
  currentTermPct: number,
): Split {
  const currentSpotPct = 100 - currentTermPct;
  let termTarget: number;
  let spotTarget: number;
  if (missionType === "HEDGE") {
    // target_pct = Term ratio (Term ↑)
    termTarget = targetPct;
    spotTarget = 100 - targetPct;
  } else {
    // OPPORTUNITY: target_pct = Spot ratio (Spot ↑)
    spotTarget = targetPct;
    termTarget = 100 - targetPct;
  }
  return {
    termTarget,
    spotTarget,
    termCurrent: currentTermPct,
    spotCurrent: currentSpotPct,
    termDelta: termTarget - currentTermPct,
    spotDelta: spotTarget - currentSpotPct,
  };
}

export function MissionSplitBar({
  missionType,
  targetPct,
  currentTermPct = 60,
  currentSourceLabel,
  size = "full",
}: Props) {
  const s = computeSplit(missionType, targetPct, currentTermPct);
  const termHigher = s.termDelta > 0;
  const spotHigher = s.spotDelta > 0;

  // primary action color: Term ↑ → crisis (위기방어), Spot ↑ → opportunity
  // (tokens는 500/700 단계만 정의 — 600 사용 시 transparent fallback)
  const termAccent = termHigher ? "bg-crisis-500" : "bg-ink-3/30";
  const spotAccent = spotHigher ? "bg-opportunity-500" : "bg-ink-3/30";

  return (
    <div className="w-full">
      {/* 현재 운영 비중 — 회사가 실제로 가지고 있는 portfolio (이전 active mission target 또는 평시 default) */}
      <div className="mb-3">
        <div className="flex items-baseline justify-between mb-1.5">
          <div className="text-[11px] uppercase tracking-wider text-ink-3/80 font-medium">
            현재 비중
          </div>
          <div className="flex items-baseline gap-3 text-[12px] text-ink-2">
            <span className="font-display tabular-nums">Term {s.termCurrent}%</span>
            <span className="text-ink-3">·</span>
            <span className="font-display tabular-nums">Spot {s.spotCurrent}%</span>
          </div>
        </div>
        <div className="flex h-5 rounded-md overflow-hidden border border-dashed border-line-2 bg-line-1/30">
          <div
            className="bg-ink-3/25"
            style={{ width: `${s.termCurrent}%` }}
            title={`현재 Term (장기 계약) ${s.termCurrent}%`}
          />
          <div
            className="bg-ink-3/40"
            style={{ width: `${s.spotCurrent}%` }}
            title={`현재 Spot (즉시 매입) ${s.spotCurrent}%`}
          />
        </div>
        {size === "full" && currentSourceLabel && (
          <div className="text-[10px] text-ink-3 mt-1 italic">↑ {currentSourceLabel}</div>
        )}
      </div>

      {/* AI 권고 (target) */}
      <div className="mb-3">
        <div className="flex items-baseline justify-between mb-1.5">
          <div className="text-[11px] uppercase tracking-wider text-ink-3 font-medium">
            AI 권고 비중
          </div>
          <div className="flex items-baseline gap-3 text-[12px]">
            <span className="text-ink-1 font-display font-semibold tabular-nums">
              Term {s.termTarget}%
            </span>
            <span className="text-ink-3">·</span>
            <span className="text-ink-1 font-display font-semibold tabular-nums">
              Spot {s.spotTarget}%
            </span>
          </div>
        </div>
        <div className="flex h-7 rounded-md overflow-hidden border border-line-1">
          <div
            className={`flex items-center justify-end px-2 text-[11px] font-medium text-white tabular-nums ${termAccent}`}
            style={{ width: `${s.termTarget}%` }}
            title={`AI 권고 Term (장기 계약) ${s.termTarget}%`}
          >
            {s.termTarget >= 15 && `${s.termTarget}%`}
          </div>
          <div
            className={`flex items-center justify-start px-2 text-[11px] font-medium text-white tabular-nums ${spotAccent}`}
            style={{ width: `${s.spotTarget}%` }}
            title={`AI 권고 Spot (즉시 매입) ${s.spotTarget}%`}
          >
            {s.spotTarget >= 15 && `${s.spotTarget}%`}
          </div>
        </div>
      </div>

      {/* 변화량 narration — 둘 다 0이면 단일 "변경 없음" chip */}
      <div className="flex items-center gap-3 text-[12px] text-ink-2">
        {s.termDelta === 0 && s.spotDelta === 0 ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-line-1 text-ink-3">
            변경 없음
          </span>
        ) : (
          <>
            <DeltaPill label="Term" delta={s.termDelta} />
            <DeltaPill label="Spot" delta={s.spotDelta} />
          </>
        )}
      </div>
    </div>
  );
}

function DeltaPill({ label, delta }: { label: string; delta: number }) {
  if (delta === 0) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-line-1 text-ink-3">
        {label} 동일
      </span>
    );
  }
  const isUp = delta > 0;
  const cls = isUp
    ? "bg-crisis-50 text-crisis-700 border-crisis-100"
    : "bg-opportunity-50 text-opportunity-700 border-opportunity-100";
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[11px] font-medium tabular-nums ${cls}`}
    >
      {label} {isUp ? "+" : ""}
      {delta}%p
    </span>
  );
}
