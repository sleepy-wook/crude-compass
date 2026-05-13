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

export interface BacktestSummary {
  run_id: string;
  n_total: number;
  n_active: number;
  n_hedge: number;
  n_opp: number;
  avg_save_pct: number | null;
  hit_rate_pct: number | null;
}

export interface BacktestZoneBreakdown {
  zone: string;
  mission_type: MissionType | null;
  n: number;
  avg_save_pct: number | null;
  hit_rate_pct: number | null;
}

export interface BacktestConfBreakdown {
  conf_bin: string;
  n: number;
  avg_save_pct: number | null;
  hit_rate_pct: number | null;
}

export interface BacktestResults {
  summary: BacktestSummary | null;
  by_zone: BacktestZoneBreakdown[];
  by_confidence: BacktestConfBreakdown[];
}

export interface BacktestPrediction {
  as_of_date: string;
  pattern_score: number | null;
  confidence_score: number | null;
  action_type: string | null;
  mission_type: MissionType | null;
  target_pct: number | null;
  duration_days: number | null;
  saving_7d_pct: number | null;
  saving_30d_pct: number | null;
  saving_90d_pct: number | null;
  dubai_at_signal_usd: number | null;
  dubai_30d_usd: number | null;
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
  | { type: "reactive.alert"; title: string; body: string; related_mission_id?: string };
