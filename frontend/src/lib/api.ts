/**
 * API client — typed fetch wrapper.
 * Backend: http://localhost:8000 (dev), Apps deploy URL (prod).
 */
import type {
  BacktestPrediction,
  BacktestResults,
  GenieQueryResponse,
  Mission,
  PatternHistory,
  PatternScoreCurrent,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    credentials: "include",
  });
  if (!resp.ok) {
    let code = "UNKNOWN";
    let msg = resp.statusText;
    try {
      const body = await resp.json();
      code = body?.detail?.code || code;
      msg = body?.detail?.message || msg;
    } catch {
      // ignore
    }
    throw new ApiError(resp.status, code, msg);
  }
  return resp.json() as Promise<T>;
}

// ──────────────────────────────────────────────────────────────────────────
// Missions
// ──────────────────────────────────────────────────────────────────────────
export const api = {
  // health
  health: () => request<{ status: string; version: string }>("/api/health"),

  // missions
  missionsActive: () =>
    request<{ missions: Mission[] }>("/api/missions/active"),
  missionsAll: () =>
    request<{ missions: Mission[] }>("/api/missions/all"),
  missionGet: (id: string) => request<Mission>(`/api/missions/${id}`),
  missionConfirm: (id: string, version: number, via: "apps" | "slack" = "apps") =>
    request<Mission>(`/api/missions/${id}/confirm`, {
      method: "POST",
      body: JSON.stringify({ version, via }),
    }),
  missionReject: (id: string, version: number, reason?: string) =>
    request<Mission>(`/api/missions/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ version, via: "apps", reason }),
    }),
  missionPivot: (
    id: string,
    body: {
      version: number;
      pivot_action: "pivot" | "pause" | "abort" | "continue";
      to_type?: "HEDGE" | "OPPORTUNITY";
      reason: string;
    }
  ) =>
    request<Mission>(`/api/missions/${id}/pivot`, {
      method: "POST",
      body: JSON.stringify({ via: "apps", ...body }),
    }),
  missionModify: (
    id: string,
    body: { version: number; target_pct?: number; duration_days?: number }
  ) =>
    request<Mission>(`/api/missions/${id}/modify`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // pattern score
  patternCurrent: () =>
    request<{ current: PatternScoreCurrent | null; history: PatternHistory[] }>(
      "/api/pattern-score/current"
    ),
  patternHistory: (days = 90) =>
    request<{ history: PatternHistory[] }>(`/api/pattern-score/history?days=${days}`),

  // backtest
  backtestResults: () => request<BacktestResults>("/api/backtest/results"),
  backtestPredictions: (limit = 50) =>
    request<{ predictions: BacktestPrediction[] }>(`/api/backtest/predictions?limit=${limit}`),

  // genie 자연어 질의
  genieQuery: (question: string, conversationId?: string | null) =>
    request<GenieQueryResponse>("/api/genie/query", {
      method: "POST",
      body: JSON.stringify({ question, conversation_id: conversationId ?? null }),
    }),

  // Mission Plan Agent — '지금 새 추천 생성' demo wrapper
  missionRecommendNow: (overrides?: {
    pattern_score?: number;
    bullish_score?: number;
    bearish_score?: number;
    use_demo_signals?: boolean;
  }) =>
    request<{
      action: string;
      mission?: Mission;
      output?: Record<string, unknown>;
      confidence_score?: number;
      llm_endpoint: string;
    }>("/api/missions/recommend_now", {
      method: "POST",
      body: JSON.stringify(overrides ?? {}),
    }),
};

export { ApiError };
export const API_BASE_URL = API_BASE;
