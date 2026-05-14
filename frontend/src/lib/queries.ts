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
  fleetPositions: ["fleet", "positions"] as const,
  signalContribution: ["signals", "contribution"] as const,
  opecLatest: ["market", "opec-latest"] as const,
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

export function useFleetPositions() {
  return useQuery({
    queryKey: queryKeys.fleetPositions,
    queryFn: () => api.fleetPositions(),
    staleTime: 10_000,
    refetchInterval: 15_000, // 데모 시 live narrative — 15초마다 update
  });
}

export function useBacktestPredictions(limit = 50) {
  return useQuery({
    queryKey: queryKeys.backtestPredictions(limit),
    queryFn: () => api.backtestPredictions(limit),
    staleTime: 3600_000,
  });
}

export function useSignalContribution() {
  return useQuery({
    queryKey: queryKeys.signalContribution,
    queryFn: () => api.signalContribution(),
    staleTime: 60_000,
  });
}

export function usePatternHistory(days: number) {
  return useQuery({
    queryKey: queryKeys.patternHistory(days),
    queryFn: () => api.patternHistory(days),
    staleTime: 60_000,
  });
}

export function useOpecLatest() {
  return useQuery({
    queryKey: queryKeys.opecLatest,
    queryFn: () => api.opecLatest(),
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
