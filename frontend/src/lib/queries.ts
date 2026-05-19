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
  backtestPredictions: (limit: number) => ["backtest", "predictions", limit] as const,
  signalContribution: ["signals", "contribution"] as const,
  opecLatest: ["market", "opec-latest"] as const,
  pricesWide: (days: number) => ["market", "prices-wide", days] as const,
  newsTop: (limit: number) => ["market", "news-top", limit] as const,
  fxHistory: (days: number) => ["market", "fx-history", days] as const,
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


export function useBacktestPredictions(limit = 50, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.backtestPredictions(limit),
    queryFn: () => api.backtestPredictions(limit),
    staleTime: 3600_000,
    enabled: options?.enabled ?? true,
  });
}

export function useSignalContribution() {
  return useQuery({
    queryKey: queryKeys.signalContribution,
    queryFn: () => api.signalContribution(),
    staleTime: 300_000, // 5분 — daily 갱신이라 자주 fetch X
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
