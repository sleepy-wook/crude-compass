/**
 * Sidebar — 좌측 context column.
 *
 * Single page mission-centric 구조에서 좌측에 K-Petroleum 브랜드 + 채점 가시성 + 데이터 출처.
 */
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { GlossaryModal } from "./Glossary";
import { cn } from "../lib/utils";
import { useMissionsActive, queryKeys } from "../lib/queries";
import { useMissionsWebSocket } from "../lib/ws";
import { api } from "../lib/api";

export function Sidebar() {
  const { status } = useMissionsWebSocket();
  const [glossaryOpen, setGlossaryOpen] = useState(false);
  const missions = useMissionsActive();
  const activeCount = missions.data?.missions?.length ?? 0;
  const qc = useQueryClient();
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null);

  const refreshMut = useMutation({
    mutationFn: () => api.refreshCuration(),
    onSuccess: (data) => {
      setRefreshMsg(data.message || "갱신 시작됨");
      // 5초 후 pattern current refetch (job 시작은 즉시 반영 안 됨)
      window.setTimeout(() => {
        qc.invalidateQueries({ queryKey: queryKeys.patternCurrent });
      }, 5000);
      window.setTimeout(() => setRefreshMsg(null), 10_000);
    },
    onError: (err: Error) => {
      const msg = err.message || "갱신 실패";
      // 503 응답에 JOB_NOT_CONFIGURED 포함
      if (msg.includes("JOB_NOT_CONFIGURED") || msg.includes("환경변수")) {
        setRefreshMsg("관리자 설정 필요 (DAILY_CURATION_JOB_ID)");
      } else {
        setRefreshMsg("갱신 실패. 로그 확인 필요.");
      }
      window.setTimeout(() => setRefreshMsg(null), 10_000);
    },
  });

  return (
    <aside className="w-72 bg-sidebar-bg text-white flex flex-col h-screen sticky top-0 border-r border-sidebar-bg2 shrink-0">
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

      {/* Admin — 데이터 갱신 */}
      <div className="px-6 py-4 border-t border-sidebar-bg2">
        <button
          type="button"
          onClick={() => refreshMut.mutate()}
          disabled={refreshMut.isPending}
          className="w-full text-left text-[12px] text-sidebar-muted hover:text-white transition-colors flex items-center justify-between disabled:opacity-50"
        >
          <span>{refreshMut.isPending ? "갱신 요청 중..." : "데이터 갱신"}</span>
          <span className="text-[11px] text-sidebar-muted2">↻</span>
        </button>
        {refreshMsg && (
          <div className="text-[10px] text-sidebar-muted2 mt-2 leading-snug">{refreshMsg}</div>
        )}
      </div>

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
