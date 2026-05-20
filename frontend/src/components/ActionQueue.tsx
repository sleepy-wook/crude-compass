/**
 * ActionQueue — multi-case priority list (left 5/12 column).
 *
 * Header: "당신을 기다리는 것 (N)"
 * List of CaseRow.
 * N=0 → empty "현재 검토 필요한 case 없음"
 * Footer: "모두 보기" → /missions
 */
import { Link } from "react-router-dom";
import { CaseRow } from "./CaseRow";
import type { Mission } from "../lib/types";

interface Props {
  cases: Mission[];
  selectedId: string | undefined;
  onSelect: (id: string) => void;
}

export function ActionQueue({ cases, selectedId, onSelect }: Props) {
  return (
    <section className="bg-panel border border-line-1 rounded-2xl flex flex-col h-full min-h-[420px]">
      <header className="px-4 py-3 border-b border-line-1 flex items-baseline justify-between">
        <h2 className="text-[13px] font-semibold text-ink-1 tracking-tight">
          당신을 기다리는 것{" "}
          <span className="text-ink-3 tabular-nums font-normal">({cases.length})</span>
        </h2>
        <span className="text-[10px] uppercase tracking-wider text-ink-3">priority</span>
      </header>

      <div className="flex-1 overflow-y-auto py-1">
        {cases.length === 0 ? (
          <div className="px-4 py-10 text-center text-[12px] text-ink-3">
            현재 검토 필요한 case 없음
          </div>
        ) : (
          cases.map((m) => (
            <CaseRow
              key={m.mission_id}
              mission={m}
              selected={m.mission_id === selectedId}
              onSelect={onSelect}
            />
          ))
        )}
      </div>

      <footer className="px-4 py-2 border-t border-line-1">
        <Link
          to="/missions"
          className="text-[11px] text-ink-3 hover:text-ink-1 transition-colors"
        >
          모두 보기 →
        </Link>
      </footer>
    </section>
  );
}
