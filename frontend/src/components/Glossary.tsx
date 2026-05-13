/**
 * Glossary — 7개 핵심 용어 hover tooltip.
 *
 * 사용:
 *   <Term name="PATTERN_SCORE">위기 신호 점수</Term>
 *   <Term name="HEDGE">HEDGE</Term>
 *
 * 디자인:
 * - 자체 group-hover Tailwind (radix-ui 의존 무추가)
 * - whitespace-normal + w-64로 긴 정의도 2-3줄 자연 줄바꿈
 * - position prop ("top" default | "bottom") — 카드 상단의 단어는 "bottom"으로 분기
 *
 * 페이지별 첫 등장에만 wrap, 두 번째 이후는 plain text 유지 (underline 도배 방지).
 */
import type { ReactNode } from "react";

export const GLOSSARY: Record<string, { label: string; definition: string }> = {
  PATTERN_SCORE: {
    label: "위기 신호 점수",
    definition:
      "위기 신호 누적 점수 (0~100). 70 이상 = HEDGE, 30 이하 = OPP. 7년 backtest 75% 적중.",
  },
  HEDGE: {
    label: "위험 방어",
    definition:
      "위험 방어 — 장기계약(Term) 비중을 늘려 가격 spike에 대비. 예: Term 60% → 75%.",
  },
  OPPORTUNITY: {
    label: "기회 포착",
    definition:
      "기회 포착 — 즉시구매(Spot) 비중을 늘려 평시 가격 하락을 활용. 예: Spot 40% → 60%.",
  },
  TERM: {
    label: "장기계약",
    definition:
      "장기계약 (Term) — 산유국과 1~6개월 단위 사전 합의된 안정 매입. 가격 변동 작음.",
  },
  SPOT: {
    label: "즉시구매",
    definition:
      "즉시구매 (Spot) — 시장 가격으로 즉시 매입. 변동성 ↑, 단가 변화 빠름.",
  },
  PIVOT: {
    label: "방향 전환",
    definition:
      "방향 전환 — HEDGE → OPP 또는 OPP → HEDGE 전환. 시장 regime 변화 대응.",
  },
  DUBAI: {
    label: "Dubai유",
    definition:
      "Dubai유 — 한국 정유사 원유 수입 핵심 벤치마크 (한국석유공사 OPINET 일별 종가).",
  },
};

interface TermProps {
  name: keyof typeof GLOSSARY | string;
  children?: ReactNode;
  position?: "top" | "bottom";
}

export function Term({ name, children, position = "top" }: TermProps) {
  const entry = GLOSSARY[name];
  // Unknown term → render children only
  if (!entry) return <>{children}</>;

  const tooltipPosClass =
    position === "top"
      ? "bottom-full mb-1.5"
      : "top-full mt-1.5";

  return (
    <span className="group relative inline-block underline decoration-dotted decoration-ink-3 underline-offset-2 cursor-help">
      {children ?? entry.label}
      <span
        className={`absolute left-1/2 -translate-x-1/2 ${tooltipPosClass} w-64 px-3 py-2 bg-ink text-white text-xs leading-snug rounded-md shadow-lg z-50 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-normal text-left`}
      >
        <span className="block font-medium mb-0.5">{entry.label}</span>
        <span className="block text-white/85">{entry.definition}</span>
      </span>
    </span>
  );
}
