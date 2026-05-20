/**
 * AgentActivityTimeline — Agent Bricks orchestration activity 시각화.
 *
 * codex P0 핵심 컴포넌트. recommendation app → agent workflow 인상 전환의 1번 장치.
 *
 * 데이터 source (실제 persisted, frontend 시뮬 X):
 *   GET /api/missions/{id}/activity → Lakebase agent_activity_events table
 *
 * Backend write paths (모두 atomic transaction):
 *   - mission insert → weighted_signal_uc:score_computed + supervisor:case_opened + mission_plan_fma:draft_generated
 *   - manager action → manager:confirmed | modified | pivoted | rejected
 *   - supervisor query → 각 subagent:invoked + supervisor:synthesized
 *
 * mode:
 *   - "compact": 최신 4개만 + 한 줄 layout (Dashboard mini)
 *   - "full":   전체 + vertical timeline + 펼친 preview (MissionsPage detail)
 */
import { useMissionActivity } from "../lib/queries";
import { cn, relativeTime } from "../lib/utils";

// ────────────────────────────────────────────────────────────────────
// actor / action 라벨 + 색
// ────────────────────────────────────────────────────────────────────
type ActorMeta = {
  label: string;
  icon: string;
  /** Tailwind text color class */
  color: string;
  /** chip bg color class */
  chip: string;
};

export const ACTOR_META: Record<string, ActorMeta> = {
  supervisor: {
    label: "Agent Bricks Supervisor",
    icon: "◆",
    color: "text-ink",
    chip: "bg-line-1 text-ink-2 border-line-2",
  },
  genie: {
    label: "Genie (Crude Oil Market)",
    icon: "▤",
    color: "text-opportunity-700",
    chip: "bg-opportunity-50 text-opportunity-700 border-opportunity-100",
  },
  knowledge_assistant: {
    label: "Knowledge Assistant (OPEC)",
    icon: "✦",
    color: "text-crisis-700",
    chip: "bg-crisis-50 text-crisis-700 border-crisis-100",
  },
  mission_plan_fma: {
    label: "Mission Plan (FMA)",
    icon: "◇",
    color: "text-opportunity-700",
    chip: "bg-opportunity-50 text-opportunity-700 border-opportunity-100",
  },
  mission_plan_uc: {
    label: "mission_plan_advice (UC Func)",
    icon: "◇",
    color: "text-opportunity-700",
    chip: "bg-opportunity-50 text-opportunity-700 border-opportunity-100",
  },
  weighted_signal_uc: {
    label: "weighted_signal (UC Func)",
    icon: "∑",
    color: "text-ink-2",
    chip: "bg-line-1 text-ink-2 border-line-2",
  },
  manager: {
    label: "매니저",
    icon: "●",
    color: "text-ink",
    chip: "bg-line-1 text-ink border-line-2",
  },
  reactive: {
    label: "Reactive Trigger",
    icon: "!",
    color: "text-crisis-700",
    chip: "bg-crisis-50 text-crisis-700 border-crisis-100",
  },
  gdelt: {
    label: "GDELT (News Ingest)",
    icon: "✉",
    color: "text-info",
    chip: "bg-paper text-info border-info",
  },
  curation_job: {
    label: "Daily Curation",
    icon: "∆",
    color: "text-warn",
    chip: "bg-paper text-warn border-warn",
  },
  price_job: {
    label: "Price Pipeline",
    icon: "$",
    color: "text-ok",
    chip: "bg-paper text-ok border-ok",
  },
  system: {
    label: "System",
    icon: "○",
    color: "text-ink-3",
    chip: "bg-line-1 text-ink-3 border-line-2",
  },
};

function actorMeta(actor: string): ActorMeta {
  return (
    ACTOR_META[actor] || {
      label: actor,
      icon: "·",
      color: "text-ink-3",
      chip: "bg-line-1 text-ink-3 border-line-2",
    }
  );
}

export const ACTION_LABEL: Record<string, string> = {
  case_opened: "case 개시",
  score_computed: "Pattern Score 계산",
  draft_generated: "Draft 생성",
  confirmed: "승인",
  rejected: "기각",
  modified: "조정",
  pivoted: "재편",
  paused: "모니터링 보류",
  aborted: "종결",
  continued: "계속 진행",
  invoked: "호출",
  synthesized: "응답 종합",
  trigger_fired: "트리거 발화",
  signal_detected: "신호 감지",
  revision_suggested: "재검토 제안",
  tick: "수집",
};

function actionLabel(action: string): string {
  return ACTION_LABEL[action] || action;
}

// ────────────────────────────────────────────────────────────────────
// Props + types
// ────────────────────────────────────────────────────────────────────
export type ActivityEvent = {
  id: string | number;
  mission_id: string | null;
  occurred_at: string;
  actor: string;
  action: string;
  result_preview: string | null;
  metadata: Record<string, unknown> | null;
};

type Props = {
  missionId: string | undefined;
  mode?: "compact" | "full";
  /** compact 모드 limit (default 4) */
  limit?: number;
  /** 헤더 표시 여부 (default true) */
  showHeader?: boolean;
};

// ────────────────────────────────────────────────────────────────────
// Main component
// ────────────────────────────────────────────────────────────────────
export function AgentActivityTimeline({
  missionId,
  mode = "compact",
  limit = 4,
  showHeader = true,
}: Props) {
  const { data, isLoading, isError } = useMissionActivity(missionId);

  // Lakebase 미연동 시 events:[] — 의도된 graceful.
  const allRaw: ActivityEvent[] = data?.events ?? [];
  // Hide noise: supervisor:synthesized with no tool calls (e.g., ping/warmup that
  // returns generic English LLM intro). Keep meaningful synthesized events that
  // actually orchestrated subagents.
  const all = allRaw.filter((e) => {
    if (e.actor !== "supervisor" || e.action !== "synthesized") return true;
    const toolCount = (e.metadata as { tool_count?: number } | null)?.tool_count;
    return typeof toolCount === "number" && toolCount > 0;
  });
  // backend는 occurred_at DESC. timeline은 chronological이 자연 — UI에서 reverse.
  const events = [...all].reverse();
  const display = mode === "compact" ? events.slice(-limit) : events;

  if (!missionId) return null;

  return (
    <section className="bg-white rounded-lg border border-line-2">
      {showHeader && (
        <header className="px-4 py-3 border-b border-line-2 flex items-center justify-between">
          <div>
            <h3 className="text-[13px] font-semibold text-ink tracking-tight">
              Agent Bricks 활동 이력
            </h3>
            <p className="text-[10px] text-ink-3 mt-0.5">
              Lakebase 기록 — Supervisor가 case lifecycle 동안 한 일
            </p>
          </div>
          {events.length > 0 && (
            <span className="text-[10px] text-ink-3">
              {mode === "compact" && events.length > limit
                ? `최근 ${limit} / 전체 ${events.length}건`
                : `${events.length}건`}
            </span>
          )}
        </header>
      )}

      <div className="px-4 py-3">
        {isLoading && (
          <div className="text-[11px] text-ink-3">활동 이력 불러오는 중...</div>
        )}
        {!isLoading && isError && (
          <div className="text-[11px] text-ink-3">활동 이력을 불러올 수 없습니다</div>
        )}
        {!isLoading && !isError && events.length === 0 && (
          <div className="text-[11px] text-ink-3">
            아직 기록된 활동이 없습니다 (case 생성 시점부터 기록)
          </div>
        )}

        {!isLoading && !isError && display.length > 0 && (
          <ol className={mode === "full" ? "relative pl-4" : "space-y-1.5"}>
            {mode === "full" && (
              <span
                aria-hidden
                className="absolute left-[5px] top-1 bottom-1 w-px bg-line-2"
              />
            )}
            {display.map((ev, idx) => (
              <EventRow
                key={ev.id}
                ev={ev}
                mode={mode}
                isLast={idx === display.length - 1}
              />
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}

// ────────────────────────────────────────────────────────────────────
// Single event row
// ────────────────────────────────────────────────────────────────────
function EventRow({
  ev,
  mode,
  isLast,
}: {
  ev: ActivityEvent;
  mode: "compact" | "full";
  isLast: boolean;
}) {
  const meta = actorMeta(ev.actor);
  const action = actionLabel(ev.action);

  if (mode === "compact") {
    // 한 줄 layout: [icon] [actor short] · [action] · [time] · [preview truncated]
    return (
      <li className="flex items-center gap-2 text-[11px] leading-snug">
        <span className={cn("inline-block w-3 text-center shrink-0", meta.color)}>
          {meta.icon}
        </span>
        <span className={cn("font-medium shrink-0", meta.color)}>
          {compactActorLabel(ev.actor)}
        </span>
        <span className="text-ink-3 shrink-0">·</span>
        <span className="text-ink-2 shrink-0">{action}</span>
        <span className="text-ink-3 text-[10px] shrink-0">
          · {relativeTime(ev.occurred_at)}
        </span>
        {ev.result_preview && (
          <span className="text-ink-3 truncate">· {ev.result_preview}</span>
        )}
      </li>
    );
  }

  // full mode — vertical timeline with dot + 2-line layout
  return (
    <li className={cn("relative pl-4", isLast ? "pb-0" : "pb-3")}>
      <span
        className={cn(
          "absolute left-0 top-1 w-[11px] h-[11px] rounded-full border-2 border-white text-[8px] leading-[7px] text-center",
          meta.chip,
        )}
      >
        {meta.icon}
      </span>
      <div className="flex items-center gap-2 text-[11px]">
        <span className={cn("font-semibold", meta.color)}>{meta.label}</span>
        <span className="text-ink-3">·</span>
        <span className="text-ink-2 font-medium">{action}</span>
        <span className="text-ink-3 text-[10px]">· {relativeTime(ev.occurred_at)}</span>
      </div>
      {ev.result_preview && (
        <div className="text-[11px] text-ink-2 mt-0.5 leading-snug">
          {ev.result_preview}
        </div>
      )}
    </li>
  );
}

// compact 한 줄용 short label
const COMPACT_LABEL: Record<string, string> = {
  supervisor: "Supervisor",
  genie: "Genie",
  knowledge_assistant: "KA",
  mission_plan_fma: "Mission Plan",
  mission_plan_uc: "mission_plan_advice",
  weighted_signal_uc: "weighted_signal",
  manager: "매니저",
  reactive: "Reactive",
  system: "System",
};

function compactActorLabel(actor: string): string {
  return COMPACT_LABEL[actor] || actor;
}
