/**
 * CaseThreadEntry — Case Thread 한 줄.
 *
 * 한 줄: [actor icon] [actor name] · [action label] · [time]
 *        [result_preview 요약]
 *        [click → expand]
 *           raw metadata pretty + 관련 artifact link
 */
import { useState } from "react";
import type { ActivityEvent } from "./AgentActivityTimeline";
import { ACTOR_META, ACTION_LABEL } from "./AgentActivityTimeline";
import { cn, relativeTime } from "../lib/utils";

function actorMeta(actor: string) {
  return (
    ACTOR_META[actor] || {
      label: actor,
      icon: "·",
      color: "text-ink-3",
      chip: "bg-line-1 text-ink-3 border-line-2",
    }
  );
}
function actionLabel(action: string): string {
  return ACTION_LABEL[action] || action;
}

export function CaseThreadEntry({ ev }: { ev: ActivityEvent }) {
  const [expanded, setExpanded] = useState(false);
  const meta = actorMeta(ev.actor);
  const label = actionLabel(ev.action);

  const hasDetail = !!(ev.metadata && Object.keys(ev.metadata).length > 0);

  return (
    <li className="relative pl-5 pb-3">
      <span
        className={cn(
          "absolute left-0 top-1 w-3 h-3 rounded-full border-2 border-white text-[8px] leading-[7px] text-center",
          meta.chip,
        )}
      >
        {meta.icon}
      </span>
      <div className="flex items-center gap-2 text-[11px]">
        <span className={cn("font-semibold", meta.color)}>{meta.label}</span>
        <span className="text-ink-3">·</span>
        <span className="text-ink-2 font-medium">{label}</span>
        <span className="text-ink-3 text-[10px]">· {relativeTime(ev.occurred_at)}</span>
        {hasDetail && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="ml-auto text-[10px] text-ink-3 hover:text-ink underline-offset-2 hover:underline"
          >
            {expanded ? "접기" : "raw 펼치기"}
          </button>
        )}
      </div>
      {ev.result_preview && (
        <div className="text-[11px] text-ink-2 mt-0.5 leading-snug">
          {ev.result_preview}
        </div>
      )}
      {expanded && ev.metadata && (
        <div className="mt-2 bg-line-1 rounded p-2 border border-line-2">
          {Array.isArray((ev.metadata as { reasoning_path?: unknown }).reasoning_path) && (
            <div className="mb-2 pb-2 border-b border-line-2">
              <div className="text-[9px] text-ink-3 uppercase font-semibold mb-1">Reasoning Path</div>
              <ol className="list-decimal list-inside text-[11px] text-ink-2 space-y-0.5">
                {((ev.metadata as { reasoning_path: string[] }).reasoning_path).map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </div>
          )}
          <pre className="text-[10px] text-ink-2 leading-snug whitespace-pre-wrap font-mono break-all">
            {JSON.stringify(ev.metadata, null, 2)}
          </pre>
        </div>
      )}
    </li>
  );
}
