import { cn, statusLabel } from "../lib/utils";

type Variant = "crisis" | "opportunity" | "ok" | "warn" | "ink3";

// Outline 톤 — MissionTypePill의 solid 톤과 시각 구분.
// 같은 row에 [TypePill solid] + [StatusPill outline] 배치 시 위계 분리.
const variantClass: Record<Variant, string> = {
  crisis: "bg-paper text-crisis-700 border-crisis-200",
  opportunity: "bg-paper text-opportunity-700 border-opportunity-200",
  ok: "bg-paper text-opportunity-700 border-opportunity-200",
  warn: "bg-paper text-amber-700 border-amber-300",
  ink3: "bg-paper text-ink-3 border-line-2",
};

const statusToVariant: Record<string, Variant> = {
  proposed: "crisis",
  active: "crisis",
  on_track: "ok",
  at_risk: "warn",
  paused: "ink3",
  pivoted: "opportunity",
  aborted: "ink3",
  completed: "ok",
};

export function StatusPill({ status, label }: { status: string; label?: string }) {
  const variant: Variant = statusToVariant[status] || "ink3";
  // default fallback — label 미전달 시 한국어 자동 라벨 (영문 노출 방지)
  const display = label || statusLabel(status);
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-[10px] tracking-wider border font-medium",
        variantClass[variant]
      )}
    >
      {display}
    </span>
  );
}

export function MissionTypePill({ type }: { type: "HEDGE" | "OPPORTUNITY" }) {
  const isHedge = type === "HEDGE";
  const label = isHedge ? "위험방어" : "기회포착";
  const title = isHedge
    ? "위험 방어 — 장기계약(Term) 비중 ↑ 가격 spike 대비"
    : "기회 포착 — 즉시구매(Spot) 비중 ↑ 평시 가격 하락 활용";
  return (
    <span
      title={title}
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] border font-medium",
        isHedge
          ? "bg-crisis-50 text-crisis-700 border-crisis-100"
          : "bg-opportunity-50 text-opportunity-700 border-opportunity-100"
      )}
    >
      {label}
    </span>
  );
}
