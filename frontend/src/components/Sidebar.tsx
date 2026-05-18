/**
 * Sidebar — 좌측 nav (Stripe/Linear 풍).
 *
 * 3 nav items + K-Petroleum brand + 기술 스택 + 데이터 출처.
 */
import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { GlossaryModal } from "./Glossary";
import { cn } from "../lib/utils";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queries";

const navItems = [
  { to: "/", label: "오늘", desc: "시장 메모리 + 시그널" },
  { to: "/missions", label: "내 결정", desc: "행동 기록" },
  { to: "/ask", label: "AI에게 묻기", desc: "Multi-Agent" },
];

export function Sidebar() {
  const [glossaryOpen, setGlossaryOpen] = useState(false);
  const qc = useQueryClient();
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null);

  const refreshMut = useMutation({
    mutationFn: () => api.refreshCuration(),
    onSuccess: (data) => {
      setRefreshMsg(data.message || "갱신 시작됨");
      window.setTimeout(() => {
        qc.invalidateQueries({ queryKey: queryKeys.patternCurrent });
      }, 5000);
      window.setTimeout(() => setRefreshMsg(null), 10_000);
    },
    onError: (err: Error) => {
      const msg = err.message || "갱신 실패";
      if (msg.includes("JOB_NOT_CONFIGURED") || msg.includes("환경변수")) {
        setRefreshMsg("관리자 설정 필요");
      } else {
        setRefreshMsg("갱신 실패");
      }
      window.setTimeout(() => setRefreshMsg(null), 10_000);
    },
  });

  return (
    <aside className="w-56 bg-sidebar-bg text-white flex flex-col h-screen sticky top-0 shrink-0">
      {/* Brand */}
      <div className="px-5 py-6 border-b border-sidebar-bg2">
        <div className="text-[10px] uppercase tracking-[0.2em] text-sidebar-muted2 mb-1">
          Crude Compass
        </div>
        <div className="font-display text-base font-semibold tracking-tight">K-Petroleum</div>
        <div className="text-[10px] text-sidebar-muted2 mt-0.5 italic">데모 가상 정유사</div>
      </div>

      {/* Nav */}
      <nav className="p-3">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "block px-3 py-2.5 mb-1 rounded-md transition-colors",
                isActive
                  ? "bg-sidebar-bg3 text-white"
                  : "text-sidebar-muted hover:bg-sidebar-bg2 hover:text-white",
              )
            }
          >
            <div className="text-[13px] font-medium">{item.label}</div>
            <div className="text-[10px] text-sidebar-muted2 mt-0.5">{item.desc}</div>
          </NavLink>
        ))}
      </nav>

      <div className="flex-1" />

      {/* Tech stack */}
      <div className="px-5 py-4 border-t border-sidebar-bg2">
        <div className="text-[9px] uppercase tracking-wider text-sidebar-muted2 mb-2.5">
          기술 스택
        </div>
        <ul className="space-y-1.5 text-[11px]">
          <li className="flex items-center justify-between">
            <span className="text-white/90">Databricks Apps</span>
          </li>
          <li className="flex items-center justify-between">
            <span className="text-white/90">Lakebase</span>
            <span className="w-1.5 h-1.5 rounded-full bg-ok" />
          </li>
          <li className="flex items-center justify-between">
            <span className="text-white/90">Genie</span>
            <span className="w-1.5 h-1.5 rounded-full bg-ok" />
          </li>
          <li className="flex items-center justify-between">
            <span className="text-white/90">Agent Bricks</span>
            <span className="w-1.5 h-1.5 rounded-full bg-ok" />
          </li>
        </ul>
      </div>

      {/* Data sources — Open Data Democratization */}
      <div className="px-5 py-4 border-t border-sidebar-bg2">
        <div className="text-[9px] uppercase tracking-wider text-sidebar-muted2 mb-2">
          공개 데이터 6 source
        </div>
        <ul className="space-y-0.5 text-[10px] text-sidebar-muted leading-relaxed">
          <li>GDELT 글로벌 뉴스</li>
          <li>EIA 미국 재고</li>
          <li>OPEC 월간 보고서</li>
          <li>한국은행 환율</li>
          <li>OPINET 종가</li>
          <li>OilPriceAPI 시세</li>
        </ul>
        <p className="mt-2 text-[10px] text-sidebar-muted2 italic leading-snug">
          Bloomberg · Platts 유료 시스템 없이 무료 동일 인텔리전스.
        </p>
      </div>

      {/* Admin — 데이터 갱신 */}
      <div className="px-5 py-3 border-t border-sidebar-bg2">
        <button
          type="button"
          onClick={() => refreshMut.mutate()}
          disabled={refreshMut.isPending}
          className="w-full text-left text-[11px] text-sidebar-muted hover:text-white transition-colors flex items-center justify-between disabled:opacity-50"
        >
          <span>{refreshMut.isPending ? "갱신 요청 중..." : "데이터 갱신"}</span>
          <span className="text-[10px] text-sidebar-muted2">↻</span>
        </button>
        {refreshMsg && (
          <div className="text-[10px] text-sidebar-muted2 mt-1.5 leading-snug">{refreshMsg}</div>
        )}
      </div>

      {/* Glossary */}
      <button
        type="button"
        onClick={() => setGlossaryOpen(true)}
        className="text-left w-full px-5 py-3 border-t border-sidebar-bg2 text-[11px] text-sidebar-muted hover:text-white hover:bg-sidebar-bg2 transition-colors flex items-center justify-between"
      >
        <span>핵심 용어 보기</span>
        <span className="text-[10px] text-sidebar-muted2">→</span>
      </button>

      <GlossaryModal open={glossaryOpen} onClose={() => setGlossaryOpen(false)} />
    </aside>
  );
}
