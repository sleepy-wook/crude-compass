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
  patternCurrent: ["pattern", "current"] as const,
  patternHistory: (days: number) => ["pattern", "history", days] as const,
  backtestResults: ["backtest", "results"] as const,
  backtestPredictions: (limit: number) => ["backtest", "predictions", limit] as const,
};

// ──────────────────────────────────────────────────────────────────────────
// Read
// ──────────────────────────────────────────────────────────────────────────
export function useMissionsActive() {
  return useQuery({
    queryKey: queryKeys.missionsActive,
    queryFn: () => api.missionsActive(),
    staleTime: 5_000,
    refetchInterval: 30_000,
  });
}

export function useMission(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.mission(id || ""),
    queryFn: () => api.missionGet(id!),
    enabled: !!id,
  });
}

export function usePatternCurrent() {
  return useQuery({
    queryKey: queryKeys.patternCurrent,
    queryFn: () => api.patternCurrent(),
    staleTime: 60_000,
  });
}

export function useBacktestResults() {
  return useQuery({
    queryKey: queryKeys.backtestResults,
    queryFn: () => api.backtestResults(),
    staleTime: 3600_000,
  });
}

export function useBacktestPredictions(limit = 50) {
  return useQuery({
    queryKey: queryKeys.backtestPredictions(limit),
    queryFn: () => api.backtestPredictions(limit),
    staleTime: 3600_000,
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
    },
  });
}
