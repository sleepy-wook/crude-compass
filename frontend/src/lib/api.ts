/**
 * API client — typed fetch wrapper.
 * Backend: http://localhost:8000 (dev), Apps deploy URL (prod).
 */
import type {
  DailyReport,
  PatternHistory,
  PatternScoreCurrent,
  Report,
  ReportStatus,
  ReportThreadResponse,
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

export const api = {
  // health
  health: () => request<{ status: string; version: string }>("/api/health"),

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
        market_balance: "increase" | "decrease" | "steady" | null;
        saudi_delta_vs_prev?: number;
      } | null;
      prev: unknown;
      source: string;
    }>("/api/market/opec-latest"),

  opecHistory: (limit = 24) =>
    request<{
      count: number;
      items: {
        report_month: string;
        saudi_kbbl_d: number | null;
        iran_kbbl_d: number | null;
        opec_total_kbbl_d: number | null;
        forecast_demand_kbbl_d: number | null;
        supply_demand_gap_kbbl_d: number | null;
        market_balance: "increase" | "decrease" | "steady" | null;
        saudi_delta_vs_prev: number | null;
      }[];
    }>(`/api/market/opec-history?limit=${limit}`),

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

  // Agent Bricks Supervisor Agent — Multi-Agent orchestration (Genie + KA + UC Function mission_plan_advice)
  // missionId 전달 시 agent_activity_events에 그 case의 tools_used + synthesized 기록.
  supervisorQuery: (question: string, missionId?: string) =>
    request<SupervisorQueryResponse>("/api/supervisor/query", {
      method: "POST",
      body: JSON.stringify({ question, mission_id: missionId }),
    }),

  // Admin — daily_curation 수동 trigger
  refreshCuration: () =>
    request<{ ok: boolean; run_id: number; job_id: number; message: string }>(
      "/api/admin/refresh-curation",
      { method: "POST" },
    ),

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

  // ──────────────────────────────────────────────────────────────────────
  // Reports model (D-1, 2026-05-21) — docs/api_contract.md §8.8
  // ──────────────────────────────────────────────────────────────────────
  reportsInbox: (limit = 10) =>
    request<{ count: number; items: Report[] }>(
      `/api/reports/inbox?limit=${limit}`
    ),

  reportDetail: (reportId: string) =>
    request<ReportThreadResponse>(`/api/reports/${reportId}`),

  reportsArchive: (status: ReportStatus = "kept", limit = 50) =>
    request<{ status: string; count: number; items: Report[] }>(
      `/api/reports/archive?status=${status}&limit=${limit}`
    ),

  reportKeep: (reportId: string) =>
    request<{
      ok: boolean;
      report_id: string;
      new_status?: ReportStatus;
      no_change?: boolean;
      current_status?: ReportStatus;
    }>(`/api/reports/${reportId}/keep`, { method: "POST" }),

  reportDrop: (reportId: string) =>
    request<{
      ok: boolean;
      report_id: string;
      new_status?: ReportStatus;
      no_change?: boolean;
      current_status?: ReportStatus;
    }>(`/api/reports/${reportId}/drop`, { method: "POST" }),

  reportInvestigate: (reportId: string) =>
    request<{
      ok: boolean;
      status: string;
      new_report_id?: string;
      tools_used?: string[];
      answer?: string;
      note?: string;
    }>(`/api/reports/${reportId}/investigate`, { method: "POST" }),

  // ──────────────────────────────────────────────────────────────────────
  // Daily Reports — docs/api_contract.md §8.9
  // ──────────────────────────────────────────────────────────────────────
  dailyReportToday: () =>
    request<{ daily_report: DailyReport | null }>("/api/daily-reports/today"),

  dailyReportsRecent: (limit = 7) =>
    request<{ count: number; items: DailyReport[] }>(
      `/api/daily-reports/recent?limit=${limit}`
    ),
};

// ──────────────────────────────────────────────────────────────────────
// SSE stream — Supervisor query (D-1, 2026-05-21)
// ──────────────────────────────────────────────────────────────────────
export type SupervisorStreamEvent =
  | { type: "delta"; text: string }
  | { type: "tool_call"; name: string }
  | { type: "done"; answer: string; tools_used: Array<{ name: string; arguments?: string | null; result_preview?: string | null }> }
  | { type: "error"; message: string }
  | { type: "fallback"; reason: string };

/**
 * Supervisor streaming — fetch + ReadableStream parser.
 * `onEvent`가 각 SSE 이벤트마다 호출됨. AbortController로 cancel 가능.
 */
export async function supervisorQueryStream(
  question: string,
  options: {
    missionId?: string;
    onEvent: (e: SupervisorStreamEvent) => void;
    signal?: AbortSignal;
  },
): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/supervisor/query/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    credentials: "include",
    signal: options.signal,
    body: JSON.stringify({ question, mission_id: options.missionId ?? null }),
  });
  if (!resp.ok || !resp.body) {
    throw new ApiError(resp.status, "STREAM_FAILED", resp.statusText || "stream failed");
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    // SSE 라인 단위 parse: "data: {...}\n\n"
    let idx;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const line = chunk.trim();
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      try {
        const ev = JSON.parse(payload) as SupervisorStreamEvent;
        options.onEvent(ev);
        if (ev.type === "done" || ev.type === "error" || ev.type === "fallback") {
          return;
        }
      } catch {
        // ignore malformed chunk
      }
    }
  }
}

export { ApiError };
export const API_BASE_URL = API_BASE;
