/**
 * Sidebar — 좌측 nav (Stripe/Linear 풍).
 *
 * 4-tab nav: 오늘 / 시장 데이터 / AI 도우미 / 내 결정 기록
 * 하단 admin 영역: 데이터 갱신 button만 minimal하게 (기술 스택 / source 목록 / glossary cut)
 */
import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { cn } from "../lib/utils";
import { api } from "../lib/api";
import { queryKeys } from "../lib/queries";

const navItems = [
  { to: "/", label: "오늘", desc: "시장 메모리 + 시그널" },
  { to: "/market", label: "시장 데이터", desc: "가격 · 환율 · 공급 · 뉴스" },
  { to: "/ask", label: "AI 도우미", desc: "Multi-Agent" },
  { to: "/missions", label: "내 결정 기록", desc: "행동 기록" },
];

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
