/**
 * API client — typed fetch wrapper.
 * Backend: http://localhost:8000 (dev), Apps deploy URL (prod).
 */
import type {
  BacktestPredictionsResponse,
  BacktestResults,
  GenieQueryResponse,
  Mission,
  PatternHistory,
  PatternScoreCurrent,
  SupervisorQueryResponse,
} from "./types";

// Production (Apps deploy): same-origin (relative path = "") → 브라우저가 현재 host로 fetch.
// Dev: explicit http://localhost:8000 → vite 5173에서 backend 8000으로 호출.
// VITE_API_BASE env var로 override 가능.
const API_BASE =
  import.meta.env.VITE_API_BASE ??
  (import.meta.env.PROD ? "" : "http://localhost:8000");

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

  fxHistory: (days = 90) =>
    request<{
      pair: string;
      history: {
        date: string;
        rate: number | null;
        delta_1d: number | null;
        delta_7d: number | null;
        vol_30d: number | null;
      }[];
    }>(`/api/market/fx-history?days=${days}`),

  pricesWide: (days = 90) =>
    request<{
      prices: {
        trade_date: string;
        wti_usd: number | null;
        brent_usd: number | null;
        dubai_usd: number | null;
        brent_dubai_spread_usd: number | null;
      }[];
    }>(`/api/market/prices-wide?days=${days}`),

  newsTop: (limit = 20) =>
    request<{
      items: {
        event_date: string;
        source: string | null;
        tier: string | null;
        title: string;
        category: string | null;
        direction: "bullish" | "bearish" | "neutral";
        importance: number | null;
        raw_tone: number | null;
        mention_count: number | null;
        url: string | null;
      }[];
    }>(`/api/market/news-top?limit=${limit}`),

  opecLatest: () =>
    request<{
      latest: {
        report_month: string;
        saudi_kbbl_d: number | null;
        iran_kbbl_d: number | null;
        opec_total_kbbl_d: number | null;
        forecast_demand_kbbl_d: number | null;
        supply_demand_gap_kbbl_d: number | null;
        market_balance: "oversupply" | "undersupply" | "balanced" | null;
        saudi_delta_vs_prev?: number;
      } | null;
      prev: unknown;
      source: string;
    }>("/api/market/opec-latest"),

  signalContribution: () =>
    request<{
      items: {
        signal_type: string;
        direction: "bullish" | "bearish" | "neutral";
        n_signals: number;
        total_contribution: number;
        avg_raw_intensity: number | null;
        avg_credibility: number | null;
        share_pct: number;
      }[];
      window_days: number;
    }>("/api/signals/contribution"),

  // backtest
  backtestResults: () => request<BacktestResults>("/api/backtest/results"),
  backtestPredictions: (limit = 50) =>
    request<BacktestPredictionsResponse>(`/api/backtest/predictions?limit=${limit}`),

  // genie 자연어 질의
  genieQuery: (question: string, conversationId?: string | null) =>
    request<GenieQueryResponse>("/api/genie/query", {
      method: "POST",
      body: JSON.stringify({ question, conversation_id: conversationId ?? null }),
    }),

  // Agent Bricks Supervisor Agent — Multi-Agent orchestration (Genie + KA + FMA Mission Plan)
  supervisorQuery: (question: string) =>
    request<SupervisorQueryResponse>("/api/supervisor/query", {
      method: "POST",
      body: JSON.stringify({ question }),
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
