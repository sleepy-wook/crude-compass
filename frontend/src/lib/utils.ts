/** Format helpers (Korean locale) + UI utilities. */
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatScore(s: number | null | undefined): string {
  if (s === null || s === undefined) return "—";
  return s.toFixed(1);
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
