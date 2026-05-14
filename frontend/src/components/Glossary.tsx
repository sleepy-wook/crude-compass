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
import { useEffect, type ReactNode } from "react";

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


// ════════════════════════════════════════════════════════════════════════
// GlossaryModal — Sidebar '용어 보기 (7)' 버튼으로 trigger.
// 전체 7개 entry를 한 화면에 노출하여 평가위원이 1 click에 용어 풀이 가능.
// 자체 fixed inset-0 + backdrop, radix-ui 의존 무추가.
// ════════════════════════════════════════════════════════════════════════
interface GlossaryModalProps {
  open: boolean;
  onClose: () => void;
}

export function GlossaryModal({ open, onClose }: GlossaryModalProps) {
  // ESC keydown → close
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="glossary-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-ink/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Panel */}
      <div className="relative z-10 w-full max-w-2xl max-h-[80vh] overflow-y-auto bg-paper rounded-xl shadow-2xl">
        <header className="sticky top-0 bg-paper border-b border-line-1 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 id="glossary-title" className="font-display text-xl font-semibold text-ink">
              핵심 용어 7개
            </h2>
            <p className="text-xs text-ink-3 mt-1">
              한국 정유사 원유 조달 의사결정에 사용되는 용어
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-ink-3 hover:text-ink p-1 rounded-md hover:bg-line-1 transition-colors"
            aria-label="닫기"
          >
            <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </header>
        <div className="px-6 py-4 divide-y divide-line-1">
          {Object.entries(GLOSSARY).map(([key, entry]) => (
            <div key={key} className="py-4 first:pt-2 last:pb-2">
              <div className="font-display text-base font-semibold text-ink mb-1">
                {entry.label}
                <span className="ml-2 text-[10px] uppercase tracking-wider text-ink-3 font-mono font-normal">
                  {key}
                </span>
              </div>
              <p className="text-sm text-ink-2 leading-relaxed">{entry.definition}</p>
            </div>
          ))}
        </div>
        <footer className="border-t border-line-1 px-6 py-3 text-xs text-ink-3 leading-relaxed">
          이 시스템은 한국 정유사 원유 조달 의사결정 AI 비서입니다. 공개 데이터 7개 ·
          Slack ↔ Apps 5초 sync · 7년 backtest 75% 적중. <kbd className="px-1.5 py-0.5 ml-1 bg-line-1 rounded text-[10px] font-mono">ESC</kbd> 또는 배경 클릭으로 닫기.
        </footer>
      </div>
    </div>
  );
}
