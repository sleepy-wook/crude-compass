/**
 * RightSidebar — Linear/Notion 풍 slim context column.
 *
 * 1 page 구조로 단순화하면서 채점 가시성(4 tool)과 K-Petroleum 브랜딩은 유지.
 */
import { useState } from "react";
import { GlossaryModal } from "./Glossary";
import { cn } from "../lib/utils";
import { useMissionsActive } from "../lib/queries";
import { useMissionsWebSocket } from "../lib/ws";

export function RightSidebar() {
  const { status } = useMissionsWebSocket();
  const [glossaryOpen, setGlossaryOpen] = useState(false);
  const missions = useMissionsActive();
  const activeCount = missions.data?.missions?.length ?? 0;

  return (
    <aside className="w-72 bg-sidebar-bg text-white flex flex-col h-screen sticky top-0 border-l border-sidebar-bg2">
      {/* Brand */}
      <div className="px-6 py-7 border-b border-sidebar-bg2">
        <div className="text-[10px] uppercase tracking-[0.2em] text-sidebar-muted2 mb-1.5">
          Crude Compass
        </div>
        <div className="font-display text-lg font-semibold tracking-tight">K-Petroleum</div>
        <div className="text-[11px] text-sidebar-muted2 mt-1 leading-snug italic">
          데모용 가상 정유사
        </div>
      </div>

      {/* Status — 현재 상태 */}
      <div className="px-6 py-5 border-b border-sidebar-bg2">
        <div className="text-[10px] uppercase tracking-wider text-sidebar-muted2 mb-3">현재 상태</div>
        <div className="space-y-2.5">
          <div className="flex items-center justify-between text-[12px]">
            <span className="text-sidebar-muted">진행 중 임무</span>
            <span className="text-white font-medium">{activeCount}건</span>
          </div>
          <div className="flex items-center justify-between text-[12px]">
            <span className="text-sidebar-muted">데이터 연결</span>
            <div className="flex items-center gap-1.5">
              <span
                className={cn(
                  "w-1.5 h-1.5 rounded-full",
                  status === "connected" && "bg-ok",
                  status === "connecting" && "bg-warn",
                  (status === "disconnected" || status === "error") && "bg-sidebar-muted2",
                )}
              />
              <span className="text-white text-[11px]">
                {status === "connected" ? "실시간" : "재연결 중"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Tech stack */}
      <div className="px-6 py-5 border-b border-sidebar-bg2">
        <div className="text-[10px] uppercase tracking-wider text-sidebar-muted2 mb-3">기술 스택</div>
        <ul className="space-y-2 text-[12px]">
          <li className="flex items-center justify-between">
            <span className="text-white/90">Databricks Apps</span>
          </li>
          <li className="flex items-center justify-between">
            <span className="text-white/90">Lakebase</span>
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-ok" />
          </li>
          <li className="flex items-center justify-between">
            <span className="text-white/90">Genie</span>
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-ok" />
          </li>
          <li className="flex items-center justify-between">
            <span className="text-white/90">Agent Bricks</span>
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-ok" />
          </li>
        </ul>
      </div>

      {/* Data sources */}
      <div className="px-6 py-5 border-b border-sidebar-bg2">
        <div className="text-[10px] uppercase tracking-wider text-sidebar-muted2 mb-3">데이터 출처</div>
        <ul className="space-y-1.5 text-[11px] text-sidebar-muted leading-relaxed">
          <li>GDELT 글로벌 뉴스</li>
          <li>EIA 미국 주간 재고</li>
          <li>OPEC 월간 보고서</li>
          <li>한국은행 환율</li>
          <li>OilPriceAPI 시세</li>
        </ul>
      </div>

      <div className="flex-1" />

      {/* Glossary trigger */}
      <button
        type="button"
        onClick={() => setGlossaryOpen(true)}
        className="text-left w-full px-6 py-4 border-t border-sidebar-bg2 text-[12px] text-sidebar-muted hover:text-white hover:bg-sidebar-bg2 transition-colors flex items-center justify-between"
      >
        <span>핵심 용어 보기</span>
        <span className="text-[11px] text-sidebar-muted2">→</span>
      </button>

      <GlossaryModal open={glossaryOpen} onClose={() => setGlossaryOpen(false)} />
    </aside>
  );
}
