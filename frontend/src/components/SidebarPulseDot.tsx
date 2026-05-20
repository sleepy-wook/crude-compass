/**
 * SidebarPulseDot — sidebar 하단 mini AI activity indicator.
 *
 * 표시:
 *   - 녹색 깜빡임 + "AI 활동 중" + 마지막 entry relativeTime (예: "30초 전")
 *   - WS 연결 안 됨: 회색 dot + "재연결 중"
 *   - 24h 누적 count 한 줄
 *
 * Sidebar는 dark theme이므로 sidebar-muted 계열 색 사용.
 */
import { usePulseStream } from "../hooks/usePulseStream";
import { usePulseStats } from "../lib/queries";
import { relativeTime } from "../lib/utils";

export function SidebarPulseDot() {
  const { events, connected } = usePulseStream(10);
  const { data: stats } = usePulseStats();
  const latest = events[0];

  return (
    <div className="border-t border-sidebar-bg2 pt-3 mt-3 px-3 text-[10px]">
      <div className="flex items-center gap-1.5">
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            connected ? "bg-opportunity-500 animate-pulse" : "bg-sidebar-muted2"
          }`}
          aria-hidden
        />
        <span className="text-sidebar-muted font-medium">
          {connected ? "AI 활동 중" : "재연결 중"}
        </span>
        {latest && (
          <span className="text-sidebar-muted2 ml-auto">
            {relativeTime(latest.occurred_at)}
          </span>
        )}
      </div>
      {stats && (
        <div className="text-sidebar-muted2 mt-1 leading-snug">
          24h {stats.total_24h}건 · {stats.active_cases} active case
        </div>
      )}
    </div>
  );
}
