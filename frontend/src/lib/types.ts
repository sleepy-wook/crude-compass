/**
 * TypeScript types — backend Pydantic v2 schema 1:1 mapping.
 * docs/api_contract.md §1.1, backend/app/schemas/mission.py
 */

export interface PatternScoreCurrent {
  date: string;
  pattern_score: number | null;
  mission_type: string | null;
  bullish_score: number | null;
  bearish_score: number | null;
  cross_val_bonus: number | null;
  confidence_score: number | null;
  signal_count_90d: number | null;
}

export interface PatternHistory {
  date: string;
  pattern_score: number | null;
  mission_type?: string | null;
  bullish_score?: number | null;
  bearish_score?: number | null;
}

/** Pulse / Agent activity event (Lakebase agent_activity row). */
export type ActivityEvent = {
  id: string | number;
  mission_id: string | null;
  occurred_at: string;
  actor: string;
  action: string;
  result_preview: string | null;
  metadata: Record<string, unknown> | null;
};

/** Agent Bricks Supervisor Agent — Multi-Agent orchestration (3 sub-agents) */

export interface SubAgentCall {
  name: string;
  arguments: string | null;
  result_preview: string | null;
}

export interface SupervisorQueryResponse {
  answer: string;
  source: "live" | "fallback";
  tools_used: SubAgentCall[];
  /** 'fallback' 모드 시 genie 4-tier 정보 (transparency) */
  fallback_genie_source?: string;
  fallback_sql?: string | null;
  fallback_data?: Record<string, unknown>[] | null;
}

// ──────────────────────────────────────────────────────────────────────────
// Reports model (2026-05-21) — event-driven AI report inbox + 06:30 daily
// docs/api_contract.md §8.8, §8.9
// ──────────────────────────────────────────────────────────────────────────
export type TriggerType = "gdelt_signal" | "price_spike" | "pattern_drift";

export type ReportStatus = "pending" | "kept" | "dropped" | "ai_dropped" | "archived";

export type StatusActor = "manager" | "ai";

export type Recommendation =
  | "HOLD"
  | "DEFER SPOT"
  | "ACCELERATE SPOT"
  | "REVIEW TERM"
  | "HEDGE"
  | "DIVERSIFY";

export interface AgentBricksToolCall {
  name: string;
  preview?: string;
}

export interface ReportReasoning {
  key_signals?: string[];
  logic?: string;
  risk_factors?: string[];
  recommendation_text?: string;
  agent_bricks_tools?: AgentBricksToolCall[];
}

export interface RelatedSignal {
  title?: string;
  source?: string;
  category?: string;
  direction?: string;
  importance?: number;
  url?: string | null;
}

export interface Report {
  report_id: string;
  parent_id: string | null;
  trigger_type: TriggerType;
  trigger_meta: Record<string, unknown>;
  status: ReportStatus;
  status_changed_at: string | null;
  status_changed_by: StatusActor | null;
  headline: string;
  summary: string;
  reasoning: ReportReasoning;
  recommendation: Recommendation | null;
  related_signals: RelatedSignal[];
  revisits_id: string | null;
  ai_drop_reason: string | null;
  version: number;
  created_at: string;
}

export interface ReportThreadResponse {
  root: Report;
  thread: Report[];
  thread_length: number;
}

export interface RatioScenario {
  name: string;
  expected_saving_pct: number;
}

export interface AgentBricksTrace {
  enabled?: boolean;
  synthesis?: string;
  tools_used?: AgentBricksToolCall[];
}

export interface RatioSuggestion {
  direction?: "lean_hedge" | "neutral" | "lean_opportunity";
  term_delta_pct?: string;
  spot_delta_pct?: string;
  qualitative?: string;
  scenarios?: RatioScenario[];
  agent_bricks?: AgentBricksTrace;
}

export interface DailyReport {
  daily_id: string;
  report_date: string;
  prev_daily_id: string | null;
  kept_report_ids: string[];
  kept_count: number;
  kept_summary: string | null;
  prev_daily_summary: string | null;
  market_context: string | null;
  ratio_suggestion: RatioSuggestion;
  reasoning: string | null;
  confidence: number | null;
  created_at: string;
}

