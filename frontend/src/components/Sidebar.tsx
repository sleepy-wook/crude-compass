import { useState } from "react";
import { NavLink } from "react-router-dom";
import { GlossaryModal } from "./Glossary";
import { cn } from "../lib/utils";
import { useMissionsWebSocket } from "../lib/ws";

const navItems = [
  { to: "/", label: "오늘의 결정", desc: "AI 권고와 근거" },
  { to: "/missions", label: "임무", desc: "진행 중 임무" },
  { to: "/what-if", label: "시뮬레이션", desc: "과거 검증과 자연어 질의" },
];

export function Sidebar() {
  const { status } = useMissionsWebSocket();
  const [glossaryOpen, setGlossaryOpen] = useState(false);

  return (
    <aside className="w-72 bg-sidebar-bg text-white flex flex-col h-screen sticky top-0">
      <div className="p-6 border-b border-sidebar-bg2">
        <div className="text-[11px] uppercase tracking-widest text-sidebar-muted mb-1">
          Crude Compass
        </div>
        <div className="font-display text-xl font-semibold tracking-tight">
          K-Petroleum
        </div>
        <div className="text-[10px] text-sidebar-muted2 mt-1 leading-snug italic">
          데모용 가상 정유사 · 100% open data
        </div>
        <div className="text-sm text-sidebar-muted mt-3 leading-relaxed">
          한국 정유사 원유 조달<br />의사결정 AI 비서
        </div>
        <div className="text-xs text-sidebar-muted2 mt-3 leading-relaxed">
          공개 데이터 6개 · Slack ↔ Apps 5초 sync · 양방향 Mission (위기+기회)
        </div>
      </div>

      {/* Databricks 4 tool 가시성 */}
      <div className="px-6 py-4 border-b border-sidebar-bg2">
        <div className="text-[10px] uppercase tracking-widest text-sidebar-muted2 mb-2.5">
          기술 스택
        </div>
        <ul className="text-[11px] text-sidebar-muted space-y-1.5 leading-snug">
          <li className="flex items-center justify-between"><span className="text-white/90">Databricks Apps</span></li>
          <li className="flex items-center justify-between"><span className="text-white/90">Lakebase</span><span className="inline-block w-1.5 h-1.5 rounded-full bg-ok" /></li>
          <li className="flex items-center justify-between"><span className="text-white/90">Genie</span><span className="inline-block w-1.5 h-1.5 rounded-full bg-ok" /></li>
          <li className="flex items-center justify-between"><span className="text-white/90">Agent Bricks</span><span className="inline-block w-1.5 h-1.5 rounded-full bg-ok" /></li>
        </ul>
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

      {/* Glossary trigger — 평가위원이 1 click에 12개 용어 풀이 */}
      <button
        type="button"
        onClick={() => setGlossaryOpen(true)}
        className="text-left w-full px-6 py-3 border-t border-sidebar-bg2 text-sm text-sidebar-muted hover:text-white hover:bg-sidebar-bg2 transition-colors flex items-center justify-between"
      >
        <span>핵심 용어 보기</span>
        <span className="text-xs text-sidebar-muted2">12개 →</span>
      </button>

      <div className="p-5 border-t border-sidebar-bg2">
        <div className="flex items-center gap-2 text-xs">
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              status === "connected" && "bg-ok",
              status === "connecting" && "bg-warn",
              (status === "disconnected" || status === "error") && "bg-sidebar-muted2",
            )}
          />
          <span className="text-sidebar-muted">
            {status === "connected" ? "실시간 연결됨" : "재연결 중"}
          </span>
        </div>
      </div>

      <GlossaryModal open={glossaryOpen} onClose={() => setGlossaryOpen(false)} />
    </aside>
  );
}
