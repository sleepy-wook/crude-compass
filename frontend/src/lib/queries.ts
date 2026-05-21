/**
 * React Query hooks — one per endpoint.
 * Cache strategy: missions (short, 5s for sync), pattern (1min), backtest (1h).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

export const queryKeys = {
  health: ["health"] as const,
  missionsActive: ["missions", "active"] as const,
  missionsAll: ["missions", "all"] as const,
  mission: (id: string) => ["missions", id] as const,
  missionActivity: (id: string) => ["missions", id, "activity"] as const,
  patternCurrent: ["pattern", "current"] as const,
  patternHistory: (days: number) => ["pattern", "history", days] as const,
  backtestResults: ["backtest", "results"] as const,
  signalContribution: ["signals", "contribution"] as const,
  opecLatest: ["market", "opec-latest"] as const,
  opecHistory: (limit: number) => ["market", "opec-history", limit] as const,
  pricesWide: (days: number) => ["market", "prices-wide", days] as const,
  newsTop: (limit: number) => ["market", "news-top", limit] as const,
  fxHistory: (days: number) => ["market", "fx-history", days] as const,

  // Reports model (2026-05-21)
  reportsInbox: (limit: number) => ["reports", "inbox", limit] as const,
  reportDetail: (id: string) => ["reports", id] as const,
  reportsArchive: (status: string, limit: number) =>
    ["reports", "archive", status, limit] as const,
  dailyReportToday: ["daily-reports", "today"] as const,
  dailyReportsRecent: (limit: number) => ["daily-reports", "recent", limit] as const,
};

// ──────────────────────────────────────────────────────────────────────────
// Read
// ──────────────────────────────────────────────────────────────────────────
export function useMissionsActive() {
  return useQuery({
    queryKey: queryKeys.missionsActive,
    queryFn: () => api.missionsActive(),
    staleTime: 120_000, // 2분 — tab switch 시 instant render
    refetchInterval: 60_000, // 1분마다 background refetch (UI block X)
  });
}

export function useMission(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.mission(id || ""),
    queryFn: () => api.missionGet(id!),
    enabled: !!id,
  });
}

/**
 * Agent Bricks orchestration activity timeline.
 * Lakebase `agent_activity_events` table read. Lakebase 미연동 시 events=[].
 */
export function useMissionActivity(id: string | undefined, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.missionActivity(id || ""),
    queryFn: () => api.missionActivity(id!),
    enabled: !!id && (options?.enabled ?? true),
    staleTime: 60_000, // 1분 — manager action 시 mutation hook이 invalidate (실시간성 유지)
    refetchInterval: 60_000,
  });
}

export function usePatternCurrent() {
  return useQuery({
    queryKey: queryKeys.patternCurrent,
    queryFn: () => api.patternCurrent(),
    staleTime: 300_000, // 5분 — TopBar / Decision Room core, frequent re-render 방지
  });
}

export function useBacktestResults() {
  return useQuery({
    queryKey: queryKeys.backtestResults,
    queryFn: () => api.backtestResults(),
    staleTime: 3600_000,
  });
}

export function useMarketMemorySimilar(
  pattern_score: number | null | undefined,
  mission_type: string | null | undefined,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ["market-memory", "similar", pattern_score, mission_type],
    queryFn: () =>
      api.marketMemorySimilar({
        pattern_score: pattern_score ?? 50,
        mission_type: mission_type ?? null,
        limit: 7,
        score_range: 10.0,
      }),
    staleTime: 300_000,
    enabled: (options?.enabled ?? true) && pattern_score !== null && pattern_score !== undefined,
  });
}


export function useSignalContribution() {
  return useQuery({
    queryKey: queryKeys.signalContribution,
    queryFn: () => api.signalContribution(),
    staleTime: 300_000, // 5분 — daily 갱신이라 자주 fetch X
  });
}

/** Signal Lifecycle — 4-stage forensic view for a single signal (article_id). */
export function useSignalLifecycle(signalId: string | undefined) {
  return useQuery({
    queryKey: ["signal", "lifecycle", signalId] as const,
    queryFn: () => api.signalLifecycle(signalId!),
    enabled: !!signalId,
    staleTime: 60_000,
  });
}

export function usePatternHistory(days: number) {
  return useQuery({
    queryKey: queryKeys.patternHistory(days),
    queryFn: () => api.patternHistory(days),
    staleTime: 600_000, // 10분 — long history는 거의 변동 X
  });
}

export function useOpecLatest() {
  return useQuery({
    queryKey: queryKeys.opecLatest,
    queryFn: () => api.opecLatest(),
    staleTime: 3600_000,
  });
}

export function useOpecHistory(limit = 24) {
  return useQuery({
    queryKey: queryKeys.opecHistory(limit),
    queryFn: () => api.opecHistory(limit),
    staleTime: 3600_000,
  });
}

export function usePricesWide(days: number) {
  return useQuery({
    queryKey: queryKeys.pricesWide(days),
    queryFn: () => api.pricesWide(days),
    staleTime: 300_000,
  });
}

export function useIntradaySummary() {
  return useQuery({
    queryKey: ["market", "intraday-summary"] as const,
    queryFn: () => api.intradaySummary(),
    staleTime: 60_000, // 60s — backend cache 60s와 동일
    refetchInterval: 60_000,
  });
}

export function useIntradayPrices(hours: number) {
  return useQuery({
    queryKey: ["market", "intraday-prices", hours] as const,
    queryFn: () => api.intradayPrices(hours),
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}

export function useNewsTop(limit: number) {
  return useQuery({
    queryKey: queryKeys.newsTop(limit),
    queryFn: () => api.newsTop(limit),
    staleTime: 300_000, // 5분 — GDELT 15분 cron이라 더 자주 fetch X
  });
}

export function useFxHistory(days: number) {
  return useQuery({
    queryKey: queryKeys.fxHistory(days),
    queryFn: () => api.fxHistory(days),
    staleTime: 300_000,
  });
}

// ──────────────────────────────────────────────────────────────────────────
// Pulse — cross-mission Agent activity stream (Live AI Pulse / Case Thread)
// ──────────────────────────────────────────────────────────────────────────

/**
 * Live AI Pulse — cross-mission stream.
 * 초기 snapshot은 REST 1회. 이후 실시간은 WS push가 담당하므로 WS 연결 시 polling 중지.
 * (REST polling이 매번 Lakebase를 깨워 scale-to-zero를 무력화하던 비용 누수 차단.)
 */
export function useRecentPulse(
  limit = 50,
  options?: { enabled?: boolean; refetchMs?: number | false },
) {
  return useQuery({
    queryKey: ["pulse", "recent", limit] as const,
    queryFn: () => api.pulseRecent(limit),
    refetchInterval: options?.refetchMs ?? 30_000,
    staleTime: 2_000,
    enabled: options?.enabled !== false,
  });
}

/** Daily Loop Clock — 오늘 24h 내 crude-compass job run summary. */
export function useJobRunsToday() {
  return useQuery({
    queryKey: ["jobs", "runs", "today"] as const,
    queryFn: () => api.jobsRunsToday(),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function usePulseStats() {
  return useQuery({
    queryKey: ["pulse", "stats"] as const,
    queryFn: () => api.pulseStats(),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}

// ──────────────────────────────────────────────────────────────────────────
// Decision Room — multi-case queue + delta strip
// ──────────────────────────────────────────────────────────────────────────

export function useDecisionQueue() {
  return useQuery({
    queryKey: ["decision-room", "queue"] as const,
    queryFn: () => api.decisionRoomQueue(),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

export function useDecisionDelta() {
  return useQuery({
    queryKey: ["decision-room", "delta"] as const,
    queryFn: () => api.decisionRoomDelta(),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useDecisionLastSeen() {
  return useQuery({
    queryKey: ["decision-room", "last-seen"] as const,
    queryFn: () => api.decisionRoomLastSeen(),
    staleTime: 60_000,
  });
}

export function useDecisionTouch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.decisionRoomTouch(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["decision-room", "delta"] });
      qc.invalidateQueries({ queryKey: ["decision-room", "last-seen"] });
    },
  });
}

// ──────────────────────────────────────────────────────────────────────────
// Write (mutations) — auto-invalidate on success
// ──────────────────────────────────────────────────────────────────────────
export function useMissionConfirm() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, version }: { id: string; version: number }) =>
      api.missionConfirm(id, version),
    onSuccess: (m) => {
      qc.invalidateQueries({ queryKey: queryKeys.missionsActive });
      qc.setQueryData(queryKeys.mission(m.mission_id), m);
      // Agent Bricks activity timeline 즉시 갱신 (Lakebase에 새 event row 기록됨)
      qc.invalidateQueries({ queryKey: queryKeys.missionActivity(m.mission_id) });
    },
  });
}

export function useMissionReject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, version, reason }: { id: string; version: number; reason?: string }) =>
      api.missionReject(id, version, reason),
    onSuccess: (m) => {
      qc.invalidateQueries({ queryKey: queryKeys.missionsActive });
      qc.setQueryData(queryKeys.mission(m.mission_id), m);
      // Agent Bricks activity timeline 즉시 갱신 (Lakebase에 새 event row 기록됨)
      qc.invalidateQueries({ queryKey: queryKeys.missionActivity(m.mission_id) });
    },
  });
}

export function useMissionPivot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      id: string;
      version: number;
      pivot_action: "pivot" | "pause" | "abort" | "continue";
      to_type?: "HEDGE" | "OPPORTUNITY";
      reason: string;
    }) => {
      const { id, ...rest } = body;
      return api.missionPivot(id, rest);
    },
    onSuccess: (m) => {
      qc.invalidateQueries({ queryKey: queryKeys.missionsActive });
      qc.setQueryData(queryKeys.mission(m.mission_id), m);
      // Agent Bricks activity timeline 즉시 갱신 (Lakebase에 새 event row 기록됨)
      qc.invalidateQueries({ queryKey: queryKeys.missionActivity(m.mission_id) });
    },
  });
}

export function useMissionModify() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      version,
      target_pct,
      duration_days,
    }: {
      id: string;
      version: number;
      target_pct?: number;
      duration_days?: number;
    }) => api.missionModify(id, { version, target_pct, duration_days }),
    onSuccess: (m) => {
      qc.invalidateQueries({ queryKey: queryKeys.missionsActive });
      qc.setQueryData(queryKeys.mission(m.mission_id), m);
      // Agent Bricks activity timeline 즉시 갱신 (Lakebase에 새 event row 기록됨)
      qc.invalidateQueries({ queryKey: queryKeys.missionActivity(m.mission_id) });
    },
  });
}

// ──────────────────────────────────────────────────────────────────────────
// Reports model (2026-05-21) — event-driven inbox + daily summary
// ──────────────────────────────────────────────────────────────────────────
import type { ReportStatus } from "./types";

export function useReportsInbox(limit = 10) {
  return useQuery({
    queryKey: queryKeys.reportsInbox(limit),
    queryFn: () => api.reportsInbox(limit),
    staleTime: 30_000, // 30s — manager가 빠르게 keep/drop 시 invalidation으로 즉시 갱신
    refetchInterval: 60_000,
  });
}

export function useReportDetail(reportId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.reportDetail(reportId || ""),
    queryFn: () => api.reportDetail(reportId!),
    enabled: !!reportId,
    staleTime: 60_000,
  });
}

export function useReportsArchive(status: ReportStatus = "kept", limit = 50) {
  return useQuery({
    queryKey: queryKeys.reportsArchive(status, limit),
    queryFn: () => api.reportsArchive(status, limit),
    staleTime: 120_000,
  });
}

export function useDailyReportToday() {
  return useQuery({
    queryKey: queryKeys.dailyReportToday,
    queryFn: () => api.dailyReportToday(),
    staleTime: 300_000, // 5분 — 06:30 cron 후 fix됨
    refetchInterval: 600_000, // 10분
  });
}

export function useDailyReportsRecent(limit = 7) {
  return useQuery({
    queryKey: queryKeys.dailyReportsRecent(limit),
    queryFn: () => api.dailyReportsRecent(limit),
    staleTime: 300_000,
  });
}

// ─────────────────────────────────────────────
// Mutations (manager action)
// ─────────────────────────────────────────────
function invalidateReports(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["reports"] });
}

export function useKeepReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reportId: string) => api.reportKeep(reportId),
    onSuccess: () => invalidateReports(qc),
  });
}

export function useDropReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reportId: string) => api.reportDrop(reportId),
    onSuccess: () => invalidateReports(qc),
  });
}

export function useInvestigateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reportId: string) => api.reportInvestigate(reportId),
    onSuccess: () => invalidateReports(qc),
  });
}
