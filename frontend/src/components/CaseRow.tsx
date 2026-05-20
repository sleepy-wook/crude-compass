/**
 * CaseRow — ActionQueue 한 줄 (44px fixed height).
 *
 * Layout:
 *   [●/○] [urgency dot] [type chip] [Term 60→75%] [score X/10] [age Xh|Xd] [status pill]
 *
 * Selected = bg-line-1 + border-l-2 border-ink-1 + chevron right.
 */
import { StatusPill, MissionTypePill } from "./StatusPill";
import { cn } from "../lib/utils";
import type { Mission } from "../lib/types";

interface Props {
  mission: Mission;
  selected: boolean;
  onSelect: (id: string) => void;
}

function ageLabel(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return `${Math.floor(diff / 86400)}d`;
}

function urgencyTone(u: string): string {
  if (u === "urgent") return "bg-crisis-500";
  if (u === "default") return "bg-amber-400";
  return "bg-line-2";
}

export function CaseRow({ mission, selected, onSelect }: Props) {
  const targetPct = mission.target_pct ?? (mission.mission_type === "HEDGE" ? 75 : 70);
  const score = Math.round(mission.pattern_score / 10);
  // Term ratio 환산 — HEDGE면 target_pct가 그대로 Term, OPPORTUNITY면 100-target
  const termTarget = mission.mission_type === "HEDGE" ? targetPct : 100 - targetPct;
  const termCurrent = 60; // 평시 default — 정밀하게 알려면 op mission 주입 필요하지만 row dense view라 OK

  return (
    <button
      type="button"
      onClick={() => onSelect(mission.mission_id)}
      title={mission.goal_text}
      className={cn(
        "w-full h-11 flex items-center gap-2.5 pl-2.5 pr-3 text-[12px] text-left transition-colors",
        "border-l-2",
        selected
          ? "bg-line-1 border-ink-1"
          : "border-transparent hover:bg-line-1/60",
      )}
    >
      <span
        className={cn(
          "shrink-0 w-2 h-2 rounded-full",
          selected ? "bg-ink-1" : "border border-line-2",
        )}
        aria-hidden
      />
      <span
        className={cn("shrink-0 w-1.5 h-1.5 rounded-full", urgencyTone(mission.urgency))}
        aria-hidden
        title={`urgency: ${mission.urgency}`}
      />
      <span className="shrink-0">
        <MissionTypePill type={mission.mission_type} />
      </span>
      <span className="shrink-0 tabular-nums text-ink-2 text-[11px]">
        Term {termCurrent}→{termTarget}%
      </span>
      <span className="shrink-0 tabular-nums text-ink-3 text-[11px]" title="Pattern Score / 10">
        {score}/10
      </span>
      <span className="shrink-0 tabular-nums text-ink-3 text-[11px]" title={mission.created_at}>
        {ageLabel(mission.created_at)}
      </span>
      <span className="ml-auto shrink-0 flex items-center gap-1.5">
        <StatusPill status={mission.status} />
        {selected && <span className="text-ink-3 text-[12px]" aria-hidden>›</span>}
      </span>
    </button>
  );
}
