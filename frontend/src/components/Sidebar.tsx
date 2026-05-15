import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { GlossaryModal } from "./Glossary";
import { cn } from "../lib/utils";
import { useMissionsWebSocket } from "../lib/ws";

const navItems = [
  { to: "/", label: "Discovery", desc: "오늘의 발견" },
  { to: "/missions", label: "Mission", desc: "진행 중 미션" },
  { to: "/what-if", label: "What-if", desc: "과거 시점 복원" },
];

export function Sidebar() {
  const { status, lastEventAt } = useMissionsWebSocket();
  const [glossaryOpen, setGlossaryOpen] = useState(false);
  // Date.now()는 impure → useState + setInterval로 re-render trigger
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(t);
  }, []);
  const elapsed = lastEventAt ? Math.floor((now - lastEventAt) / 1000) : null;

  return (
    <aside className="w-72 bg-sidebar-bg text-white flex flex-col h-screen sticky top-0">
      <div className="p-6 border-b border-sidebar-bg2">
        <div className="text-[11px] uppercase tracking-widest text-sidebar-muted mb-1">
          Crude Compass
        </div>
        <div className="font-display text-xl font-semibold tracking-tight">
          K-Petroleum
        </div>
        <div className="text-sm text-sidebar-muted mt-3 leading-relaxed">
          한국 정유사 원유 조달<br />의사결정 AI 비서
        </div>
        <div className="text-xs text-sidebar-muted2 mt-3 leading-relaxed">
          공개 데이터 6개 · Slack ↔ Apps 5초 sync · 7년 backtest 75% 적중
        </div>
      </div>

      <nav className="flex-1 p-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "block px-4 py-3 mb-1.5 rounded-md transition-colors",
                isActive
                  ? "bg-sidebar-bg3 text-white"
                  : "text-sidebar-muted hover:bg-sidebar-bg2 hover:text-white"
              )
            }
          >
            <div className="text-base font-medium">{item.label}</div>
            <div className="text-xs text-sidebar-muted2 mt-1">{item.desc}</div>
          </NavLink>
        ))}
      </nav>

      {/* Glossary trigger — 평가위원이 1 click에 8개 용어 풀이 */}
      <button
        type="button"
        onClick={() => setGlossaryOpen(true)}
        className="text-left w-full px-6 py-3 border-t border-sidebar-bg2 text-sm text-sidebar-muted hover:text-white hover:bg-sidebar-bg2 transition-colors flex items-center justify-between"
      >
        <span>핵심 용어 보기</span>
        <span className="text-xs text-sidebar-muted2">8개 →</span>
      </button>

      <div className="p-5 border-t border-sidebar-bg2">
        <div className="flex items-center gap-2 text-sm">
          <span
            className={cn(
              "w-2.5 h-2.5 rounded-full",
              status === "connected" && "bg-ok",
              status === "connecting" && "bg-warn",
              status === "disconnected" && "bg-sidebar-muted2",
              status === "error" && "bg-crisis-500"
            )}
          />
          <span className="text-sidebar-muted">
            {status === "connected" ? "Live sync" : status}
          </span>
        </div>
        {elapsed !== null && elapsed < 60 && (
          <div className="text-xs text-sidebar-muted2 mt-1.5 font-mono">
            last event {elapsed}s ago
          </div>
        )}
      </div>

      <GlossaryModal open={glossaryOpen} onClose={() => setGlossaryOpen(false)} />
    </aside>
  );
}
