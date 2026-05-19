/**
 * Sidebar — 좌측 nav (Stripe/Linear 풍).
 *
 * 4-tab IA (codex P0): Decision Room / Market Watch / Investigation / Case File.
 * Korean track demo이지만 codex narrative (Agent Bricks orchestration) 용어를 label로
 * 노출해 5-sec 인상에서 "decision room"으로 읽히게 함. desc는 한글로 부연.
 *
 * 하단 admin 영역: 데이터 갱신 button만 minimal하게 (기술 스택 / source 목록 / glossary cut)
 */
import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { cn } from "../lib/utils";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queries";

const navItems = [
  { to: "/", label: "Decision Room", desc: "오늘 운영 case + Agent" },
  { to: "/market", label: "Market Watch", desc: "가격 · 환율 · 뉴스 근거" },
  { to: "/ask", label: "Investigation", desc: "Supervisor 조사 콘솔" },
  { to: "/missions", label: "Case File", desc: "결정 기록 + 재편" },
];

// Prefetch on hover — tab 클릭 전 미리 fetch → tab switch instant.
// 각 페이지 critical fetch만 (전체 prefetch X — over-fetch 방지).
function prefetchForRoute(qc: QueryClient, to: string): void {
  const prefetch = (key: readonly unknown[], fn: () => Promise<unknown>, staleTime = 120_000) =>
    qc.prefetchQuery({ queryKey: key, queryFn: fn, staleTime });
  if (to === "/") {
    prefetch(queryKeys.missionsActive, () => api.missionsActive());
    prefetch(queryKeys.patternCurrent, () => api.patternCurrent(), 300_000);
  } else if (to === "/market") {
    prefetch(queryKeys.patternCurrent, () => api.patternCurrent(), 300_000);
    prefetch(queryKeys.newsTop(5), () => api.newsTop(5), 300_000);
    prefetch(queryKeys.opecLatest, () => api.opecLatest(), 3_600_000);
    prefetch(queryKeys.pricesWide(90), () => api.pricesWide(90), 300_000);
    prefetch(queryKeys.fxHistory(90), () => api.fxHistory(90), 300_000);
  } else if (to === "/ask") {
    prefetch(queryKeys.patternCurrent, () => api.patternCurrent(), 300_000);
  } else if (to === "/missions") {
    prefetch(queryKeys.missionsActive, () => api.missionsActive());
  }
}

export function Sidebar() {
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
            onMouseEnter={() => prefetchForRoute(qc, item.to)}
            onFocus={() => prefetchForRoute(qc, item.to)}
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

      {/* Footer — admin refresh only */}
      <div className="px-5 py-4 border-t border-sidebar-bg2">
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
    </aside>
  );
}
