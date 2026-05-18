/** Format helpers (Korean locale) + UI utilities. */
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ────────────────────────────────────────────────────────────────────
// Scenario label normalizer — LLM이 schema placeholder를 literal key로
// 흘리거나 underscore 자연어 라벨로 만들 때 사람이 보기 좋게 변환.
// MissionHero, MissionsPage detail 둘 다 사용.
// ────────────────────────────────────────────────────────────────────
const SCENARIO_POSITION_LABEL = ["낙관 시나리오", "기본 시나리오", "비관 시나리오"];
const RAW_KEY_OVERRIDES: Record<string, string> = {
  best_case_label: "낙관 시나리오",
  base_case_label: "기본 시나리오",
  worst_case_label: "비관 시나리오",
  best_case: "낙관 시나리오",
  base_case: "기본 시나리오",
  worst_case: "비관 시나리오",
};

export function normalizeScenarioLabel(rawKey: string, idx: number): string {
  const lower = rawKey.toLowerCase();
  if (lower in RAW_KEY_OVERRIDES) return RAW_KEY_OVERRIDES[lower];
  // 영문 snake_case placeholder 패턴이면 위치 기반 fallback
  if (/^[a-z_]+$/.test(lower) && lower.endsWith("_label")) {
    return SCENARIO_POSITION_LABEL[idx] ?? rawKey;
  }
  // 한글/숫자 포함 자연어 라벨이면 underscore 만 공백으로 정리
  return rawKey.replace(/_/g, " ");
}

export function formatScore(s: number | null | undefined): string {
  if (s === null || s === undefined) return "—";
  return s.toFixed(1);
}

/** Score를 정수 + 천 단위 콤마. 정유사 매니저용 round 표기. */
export function formatRoundedScore(s: number | null | undefined): string {
  if (s === null || s === undefined) return "—";
  return Math.round(s).toLocaleString();
}

/** 신뢰도 표기 — 99.5% 이상은 "95+"로 clamp (AI 100% 비현실 회피). */
export function formatConfidence(c: number | null | undefined): string {
  if (c === null || c === undefined) return "—";
  if (c >= 99.5) return "95+%";
  return `${c.toFixed(0)}%`;
}

export function formatPct(p: number | null | undefined, digits = 1): string {
  if (p === null || p === undefined) return "—";
  return `${p.toFixed(digits)}%`;
}

export function formatUsd(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `$${v.toFixed(2)}`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function formatDateShort(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("ko-KR", { month: "2-digit", day: "2-digit" });
  } catch {
    return iso.slice(0, 10);
  }
}

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diff = (now - then) / 1000;
  if (diff < 60) return "방금 전";
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  return `${Math.floor(diff / 86400)}일 전`;
}

/** Mission status → human label */
export function statusLabel(status: string): string {
  const map: Record<string, string> = {
    proposed: "제안됨",
    active: "진행 중",
    on_track: "정상",
    at_risk: "주의",
    paused: "일시중지",
    pivoted: "전환됨",
    aborted: "중단",
    completed: "완료",
  };
  return map[status] || status;
}

/** Mission type → Korean */
export function missionTypeLabel(t: string): string {
  if (t === "HEDGE") return "위험 방어";
  if (t === "OPPORTUNITY") return "기회 포착";
  return t;
}

/** Mission type → 계약 형태 한글 (Term/Spot 영문 잔재 제거) */
export function termSpotLabel(t: string): string {
  if (t === "HEDGE") return "장기계약";
  if (t === "OPPORTUNITY") return "즉시구매";
  return t;
}

/** Mission type → 영문 잔재 없는 한글 비중 표기 (예: "장기계약 75%") */
export function termSpotPct(t: string, pct: number | null | undefined): string {
  if (pct === null || pct === undefined) return "—";
  return `${termSpotLabel(t)} ${pct}%`;
}
