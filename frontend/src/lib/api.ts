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

  /** Agent Bricks orchestration activity timeline (Lakebase `agent_activity_events`). */
  missionActivity: (id: string) =>
    request<{
      events: {
        id: string | number;
        mission_id: string | null;
        occurred_at: string;
        actor: string;
        action: string;
        result_preview: string | null;
        metadata: Record<string, unknown> | null;
      }[];
    }>(`/api/missions/${id}/activity`),

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

  intradaySummary: () =>
    request<{
      tickers: {
        ticker: string;
        price_usd: number | null;
        fetched_at: string;
        delta_30min_pct: number | null;
        delta_24h_pct: number | null;
        biggest_spike_pct: number | null;
        biggest_spike_at: string | null;
        sample_count: number;
      }[];
    }>("/api/market/intraday-summary"),

  intradayPrices: (hours = 24) =>
    request<{
      hours: number;
      series: {
        ticker: string;
        points: { price_usd: number; fetched_at: string }[];
      }[];
    }>(`/api/market/intraday-prices?hours=${hours}`),

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

  /** Signal Lifecycle — 4-stage forensic view (bronze + silver + gold). Trace-a-Signal Investigation. */
  signalLifecycle: (signalId: string) =>
    request<{
      signal_id: string;
      stages: {
        detected: Record<string, unknown> | null;
        scored: {
          importance: number | null;
          direction: string | null;
          horizon: string | null;
          confidence: number | null;
        } | null;
        decay: Array<{
          as_of_date: string;
          weight: number;
          lambda: number;
          days_since_event: number;
        }>;
        contribution: {
          total_contribution: number;
          peak_contribution: number;
          peak_date: string;
          referenced_case_ids: string[];
        } | null;
      };
    }>(`/api/signals/${encodeURIComponent(signalId)}/lifecycle`),

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

  // Agent Bricks Supervisor Agent — Multi-Agent orchestration (Genie + KA + UC Function mission_plan_advice)
  // missionId 전달 시 agent_activity_events에 그 case의 tools_used + synthesized 기록.
  supervisorQuery: (question: string, missionId?: string) =>
    request<SupervisorQueryResponse>("/api/supervisor/query", {
      method: "POST",
      body: JSON.stringify({ question, mission_id: missionId }),
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

  // Admin — daily_curation 수동 trigger + freshness 확인
  refreshCuration: () =>
    request<{ ok: boolean; run_id: number; job_id: number; message: string }>(
      "/api/admin/refresh-curation",
      { method: "POST" },
    ),
  curationStatus: () =>
    request<{ latest_date: string | null }>("/api/admin/curation-status"),

  // ──────────────────────────────────────────────────────────────────────
  // Pulse — cross-mission Agent activity stream (Live AI Pulse / Case Thread)
  // ──────────────────────────────────────────────────────────────────────

  /** Cross-mission 최근 N개 events. Live AI Pulse 초기 fetch. */
  pulseRecent: (limit = 50) =>
    request<{
      events: {
        id: string | number;
        mission_id: string | null;
        occurred_at: string;
        actor: string;
        action: string;
        result_preview: string | null;
        metadata: Record<string, unknown> | null;
      }[];
      count: number;
    }>(`/api/pulse/recent?limit=${limit}`),

  /** Daily Loop Clock — 오늘 24h 내 crude-compass job run summary. */
  jobsRunsToday: () =>
    request<{
      runs: Array<{
        job_name: string;
        label: string;
        run_id: number;
        start_time: number | null;
        end_time: number | null;
        result_state: string | null;
        duration_ms: number | null;
      }>;
      summary: Record<string, { count: number; success: number; fail: number }>;
    }>("/api/jobs/runs/today"),

  /** 24h 누적 통계. */
  pulseStats: () =>
    request<{
      total_24h: number;
      by_actor: Record<string, number>;
      by_action: Record<string, number>;
      active_cases: number;
    }>("/api/pulse/stats"),

  // Market Memory — Similar Pattern Retrieve (D-4 ★ Wow 1)
  marketMemorySimilar: (body: {
    pattern_score: number;
    mission_type?: string | null;
    limit?: number;
    score_range?: number;
  }) =>
    request<{
      input: { pattern_score: number; mission_type?: string | null; score_range?: number };
      summary: {
        n?: number;
        avg_saving_30d_pct?: number;
        avg_saving_7d_pct?: number;
        avg_saving_90d_pct?: number;
        best_saving_30d_pct?: number;
        worst_saving_30d_pct?: number;
        avg_dubai_change_30d_pct?: number;
        hit_rate_pct?: number;
      };
      top_matches: Array<{
        as_of_date: string;
        pattern_score: number | null;
        confidence_score: number | null;
        mission_type: string | null;
        target_pct: number | null;
        saving_7d_pct: number | null;
        saving_30d_pct: number | null;
        saving_90d_pct: number | null;
        dubai_at_signal_usd: number | null;
        dubai_30d_usd: number | null;
        distance: number | null;
      }>;
      lakebase_available: boolean;
      reason?: string;
    }>("/api/market-memory/similar", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export { ApiError };
export const API_BASE_URL = API_BASE;
