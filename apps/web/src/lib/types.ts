// API 응답 타입 — Phase 3에서 Lakebase schema와 정합 맞춤

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

export interface RiskScoreContributor {
  name: string
  kr: string
  value: number
  delta: number
  spark: number[]
  color: string
}

export interface RiskScoreSummary {
  value: number
  level: RiskLevel
  delta: number
  contributors: RiskScoreContributor[]
  ai_recommendation: {
    current_term_pct: number
    current_spot_pct: number
    suggested_term_pct: number
    suggested_spot_pct: number
    reasoning: string
  }
}

export type DiscoveryCardKind = 'risk' | 'cargo' | 'osp' | 'rfq' | 'mission_checkpoint'

export interface DiscoveryCard {
  id: string
  kind: DiscoveryCardKind
  category: string
  urgent: boolean
  title: string
  subtitle: string
  meta: string
  body: unknown
  cta_primary: string
  cta_secondary: string
}

export interface MissionEvent {
  day: number
  kind: 'ai' | 'mgr'
  title: string
  time: string
  detail: string
}

export interface Mission {
  mission_id: string
  goal: string
  start_date: string
  current_day: number
  target_day: number
  status: 'active' | 'completed' | 'paused'
  events: MissionEvent[]
}

export interface GenieResult {
  status: 'ok' | 'timeout' | 'error'
  fallback?: boolean
  chart?: unknown
  ai_bi_url?: string
}
