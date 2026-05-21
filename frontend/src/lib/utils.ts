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

