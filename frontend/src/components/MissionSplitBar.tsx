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
  /** target_pct: HEDGE면 Term ratio, OPPORTUNITY면 Spot ratio */
  targetPct: number;
  /** 평시 baseline. default Term=60, Spot=40 (시나리오 §4). */
  baselineTermPct?: number;
  size?: "compact" | "full";
}

interface Split {
  termTarget: number;
  spotTarget: number;
  termBaseline: number;
  spotBaseline: number;
  termDelta: number;
  spotDelta: number;
}

function computeSplit(missionType: MissionType, targetPct: number, baselineTermPct: number): Split {
  const baselineSpotPct = 100 - baselineTermPct;
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
    termBaseline: baselineTermPct,
    spotBaseline: baselineSpotPct,
    termDelta: termTarget - baselineTermPct,
    spotDelta: spotTarget - baselineSpotPct,
  };
}

export function MissionSplitBar({
  missionType,
  targetPct,
  baselineTermPct = 60,
  size = "full",
}: Props) {
  const s = computeSplit(missionType, targetPct, baselineTermPct);
  const termHigher = s.termDelta > 0;
  const spotHigher = s.spotDelta > 0;

  // primary action color: Term ↑ → crisis (위기방어), Spot ↑ → opportunity
  const termAccent = termHigher ? "bg-crisis-600" : "bg-ink-3/30";
  const spotAccent = spotHigher ? "bg-opportunity-600" : "bg-ink-3/30";

  return (
    <div className="w-full">
      {/* 권고 (target) */}
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
            title={`Term (장기 계약) ${s.termTarget}%`}
          >
            {s.termTarget >= 15 && `${s.termTarget}%`}
          </div>
          <div
            className={`flex items-center justify-start px-2 text-[11px] font-medium text-white tabular-nums ${spotAccent}`}
            style={{ width: `${s.spotTarget}%` }}
            title={`Spot (즉시 매입) ${s.spotTarget}%`}
          >
            {s.spotTarget >= 15 && `${s.spotTarget}%`}
          </div>
        </div>
      </div>

      {/* 평시 baseline (ghost) — full mode만 */}
      {size === "full" && (
        <div className="mb-3">
          <div className="flex items-baseline justify-between mb-1.5">
            <div className="text-[11px] uppercase tracking-wider text-ink-3/70 font-medium">
              평시 기준 비중
            </div>
            <div className="flex items-baseline gap-3 text-[12px] text-ink-3">
              <span className="font-display tabular-nums">Term {s.termBaseline}%</span>
              <span>·</span>
              <span className="font-display tabular-nums">Spot {s.spotBaseline}%</span>
            </div>
          </div>
          <div className="flex h-5 rounded-md overflow-hidden border border-dashed border-line-2 bg-line-1/40">
            <div
              className="bg-ink-3/15"
              style={{ width: `${s.termBaseline}%` }}
              title="Term baseline"
            />
            <div
              className="bg-ink-3/25"
              style={{ width: `${s.spotBaseline}%` }}
              title="Spot baseline"
            />
          </div>
        </div>
      )}

      {/* 변화량 narration */}
      <div className="flex items-center gap-3 text-[12px] text-ink-2">
        <DeltaPill label="Term" delta={s.termDelta} />
        <DeltaPill label="Spot" delta={s.spotDelta} />
        {size === "full" && (
          <span className="text-[11px] text-ink-3 italic ml-auto">
            평시 → 권고 비중 차이
          </span>
        )}
      </div>
      {size === "full" && (
        <div className="mt-3 pt-3 border-t border-line-1 text-[11px] text-ink-3 leading-relaxed">
          <span className="text-ink-2 font-medium">Term</span> 장기 계약 (OSP linked, 월간 갱신) ·{" "}
          <span className="text-ink-2 font-medium">Spot</span> 즉시 매입 (현물, 가격 추적)
        </div>
      )}
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
