/**
 * TypeScript types — backend Pydantic v2 schema 1:1 mapping.
 * docs/api_contract.md §1.1, backend/app/schemas/mission.py
 */

export type MissionType = "HEDGE" | "OPPORTUNITY";

export type MissionStatus =
  | "proposed"
  | "active"
  | "on_track"
  | "at_risk"
  | "paused"
  | "pivoted"
  | "aborted"
  | "completed";

export type MissionUrgency = "optional" | "default" | "urgent";

export interface PivotEntry {
  from_type: MissionType;
  to_type: MissionType;
  occurred_at: string;
  reason: string;
  pattern_score_at: number;
}

export interface SupplierAllocation {
  supplier_name: string;
  delta_bpd: number;
  rationale: string;
}

export interface SimulationAssumptions {
  scenario_label: string;
  brent_usd: number;
  usd_krw: number;
  vlcc_freight_multiplier: number;
}

export interface SimulationScenario {
  name: "worst" | "likely" | "best";
  label: string;
  assumptions: SimulationAssumptions;
  saving_pct: number;
  saving_krw_oku: number;
  confidence_note?: string | null;
}

export interface DeltaVsPrevious {
  previous_date: string;
  previous_mission_type: MissionType;
  previous_target_pct: number | null;
  direction_changed: boolean;
  reason: string;
  new_signals: string[];
  weakened_signals: string[];
}

export interface Mission {
  mission_id: string;
  mission_type: MissionType;
  status: MissionStatus;
  goal_text: string;
  pattern_score: number;
  reasoning: string;
  simulation_roi: Record<string, number>;
  urgency: MissionUrgency;
  target_pct: number | null;
  duration_days: number;
  created_at: string;
  confirmed_at: string | null;
  confirmed_by: string | null;
  confirmed_via: "slack" | "apps" | null;
  completed_at: string | null;
  pivot_history: PivotEntry[];
  version: number;
  // Sub-A — actionable recommendations (옵션, backward compat)
  cycle?: string | null;
  supplier_mix?: SupplierAllocation[];
  // Sub-B — honest simulation (옵션, backward compat)
  simulation_scenarios?: SimulationScenario[];
  // AI Agent 어제 vs 오늘 변동 narrative (D-3 추가, 옵션)
  delta_vs_previous?: DeltaVsPrevious | null;
}

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

/** WebSocket events — docs/api_contract.md §5 */
export type WSEvent =
  | { type: "connected"; ts: number }
  | { type: "ping"; ts: number }
  | { type: "subscribed" }
  | { type: "mission.proposed"; mission: Mission }
  | { type: "mission.confirmed"; mission: Mission }
  | { type: "mission.pivoted"; mission: Mission; pivot?: PivotEntry }
  | { type: "mission.updated"; mission: Mission }
  | { type: "pattern.changed"; pattern_score: number; mission_type: MissionType }
  | {
      type: "reactive.alert";
      title: string;
      body: string;
      related_mission_id?: string;
      // Phase 6 OilPriceAPI spike payload
      ticker?: string;
      price_usd?: number;
      delta_pct_5min?: number;
      direction?: "bullish" | "bearish";
    };
