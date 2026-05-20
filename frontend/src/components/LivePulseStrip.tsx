/**
 * LivePulseStrip — Decision Room hero. Bloomberg Terminal 풍 streaming feed.
 *
 * Top: 24h 누적 통계 (gdelt N / price N / supervisor N / mission N)
 * Body: 최근 events 위에서 아래로 stream. 새 entry는 위에 push, slide-down animation.
 * Empty: "watching..." pulse animation
 */
import { useMemo } from "react";
import { Link } from "react-router-dom";
import { usePulseStream } from "../hooks/usePulseStream";
import { usePulseStats } from "../lib/queries";
import { cn, relativeTime } from "../lib/utils";
import { ACTOR_META, ACTION_LABEL } from "./AgentActivityTimeline";

const ROW_LIMIT = 14;

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

const ACTOR_SHORT: Record<string, string> = {
  supervisor: "Supervisor",
  genie: "Genie",
  knowledge_assistant: "KA",
  mission_plan_fma: "Mission Plan",
  mission_plan_uc: "mission_plan_advice",
  weighted_signal_uc: "weighted_signal",
  gdelt: "GDELT",
  curation_job: "Curation",
  price_job: "Price",
  reactive: "Reactive",
  manager: "매니저",
  system: "System",
};

export function LivePulseStrip() {
  const { events, connected } = usePulseStream(50);
  const { data: stats } = usePulseStats();

  const top = useMemo(() => events.slice(0, ROW_LIMIT), [events]);

  return (
    <section className="bg-white rounded-lg border border-line-2 overflow-hidden">
      <header className="px-4 py-2 border-b border-line-2 flex items-center gap-3 bg-paper">
        <div className="flex items-center gap-1.5">
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              connected ? "bg-opportunity-500 animate-pulse" : "bg-ink-3",
            )}
            aria-hidden
          />
          <span className="text-[11px] font-semibold text-ink">Live AI Pulse</span>
          <span className="text-[10px] text-ink-3">
            {connected ? "실시간" : "재연결 중"}
          </span>
        </div>
        {stats && (
          <div className="ml-auto flex items-center gap-3 text-[10px] text-ink-3">
            <span>24h 활동 {stats.total_24h}건</span>
            <span>· 활성 case {stats.active_cases}</span>
            <span>· gdelt {stats.by_actor.gdelt ?? 0}</span>
            <span>· price {stats.by_actor.price_job ?? 0}</span>
            <span>· supervisor {stats.by_actor.supervisor ?? 0}</span>
          </div>
        )}
      </header>

      <ol className="max-h-[340px] overflow-y-auto">
        {top.length === 0 && (
          <li className="px-4 py-6 text-[11px] text-ink-3 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-ink-3 animate-pulse" aria-hidden />
            watching... (AI 활동 대기)
          </li>
        )}
        {top.map((ev) => {
          const m = actorMeta(ev.actor);
          const short = ACTOR_SHORT[ev.actor] ?? ev.actor;
          const rowClass =
            "block px-4 py-1.5 hover:bg-paper text-[11px] leading-snug";
          const inner = (
            <>
              <span className="text-[10px] text-ink-3 mr-2 tabular-nums">
                {relativeTime(ev.occurred_at)}
              </span>
              <span className={cn("inline-block w-3 text-center mr-1", m.color)}>
                {m.icon}
              </span>
              <span className={cn("font-medium mr-1", m.color)}>{short}</span>
              <span className="text-ink-2 mr-1">·</span>
              <span className="text-ink-2 mr-2">
                {ACTION_LABEL[ev.action] ?? ev.action}
              </span>
              {ev.result_preview && (
                <span className="text-ink-3 truncate inline-block max-w-[60%] align-bottom">
                  · {ev.result_preview}
                </span>
              )}
            </>
          );
          // gdelt entry는 article_id metadata 있으면 /ask?signal_id=... deep link.
          // mission_id가 우선 — case 진입이 forensic view보다 더 명시적인 narrative.
          const articleId = (ev.metadata as { article_id?: string } | null)?.article_id;
          const linkTo = ev.mission_id
            ? `/missions/${ev.mission_id}`
            : articleId
              ? `/ask?signal_id=${encodeURIComponent(articleId)}`
              : null;
          return (
            <li key={ev.id} className="border-b border-line-1 last:border-b-0">
              {linkTo ? (
                <Link to={linkTo} className={rowClass}>
                  {inner}
                </Link>
              ) : (
                <div className={rowClass}>{inner}</div>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
