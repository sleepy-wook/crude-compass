/**
 * ReportsInbox — Decision Room 좌측 컬럼 (reports model 2026-05-21).
 *
 * pending status 보고서 list. trigger별 아이콘/색상:
 *   gdelt_signal → Newspaper (info-blue)
 *   price_spike  → DollarSign (ok-green)
 *   pattern_drift → Activity (warn-amber)
 *
 * 높이 SelectedReportDetail과 매칭 (h-[560px]).
 */
import { Activity, DollarSign, Newspaper } from "lucide-react";
import type { ComponentType } from "react";
import { cn } from "../lib/utils";
import type { Recommendation, Report, TriggerType } from "../lib/types";

interface Props {
  reports: Report[];
  selectedId: string | undefined;
  onSelect: (id: string) => void;
}

interface TriggerMeta {
  Icon: ComponentType<{ className?: string }>;
  iconClass: string;
  label: string;
}

const TRIGGER_META: Record<TriggerType, TriggerMeta> = {
  gdelt_signal: { Icon: Newspaper, iconClass: "text-info-700 bg-info-50", label: "뉴스" },
  price_spike: { Icon: DollarSign, iconClass: "text-opportunity-700 bg-opportunity-50", label: "가격" },
  pattern_drift: { Icon: Activity, iconClass: "text-amber-700 bg-amber-50", label: "추세" },
};

const REC_CHIP: Record<Recommendation, string> = {
  HOLD: "bg-line-1 text-ink-2",
  "DEFER SPOT": "bg-amber-50 text-amber-700",
  "ACCELERATE SPOT": "bg-opportunity-50 text-opportunity-700",
  "REVIEW TERM": "bg-info-50 text-info-700",
  HEDGE: "bg-crisis-50 text-crisis-700",
  DIVERSIFY: "bg-info-50 text-info-700",
};

function ageLabel(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "방금";
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return `${Math.floor(diff / 86400)}d`;
}

export function ReportsInbox({ reports, selectedId, onSelect }: Props) {
  return (
    <section className="bg-panel border border-line-1 rounded-2xl flex flex-col h-[680px]">
      <header className="px-4 py-3 border-b border-line-1">
        <div className="flex items-baseline justify-between">
          <h2 className="text-[13px] font-semibold text-ink-1 tracking-tight">
            검토 대기{" "}
            <span className="text-ink-3 tabular-nums font-normal">({reports.length})</span>
          </h2>
          <span className="text-[10px] tracking-wider text-ink-3">시간 역순</span>
        </div>
        <p className="text-[10.5px] text-ink-3 mt-1 leading-snug">
          트리거 신호 발생 시 AI가 자동 생성한 보고서
        </p>
      </header>

      <div className="flex-1 overflow-y-auto py-1">
        {reports.length === 0 ? (
          <div className="px-4 py-10 text-center text-[12px] text-ink-3">
            현재 검토 필요한 보고서 없음
          </div>
        ) : (
          reports.map((r) => (
            <ReportRow
              key={r.report_id}
              report={r}
              selected={r.report_id === selectedId}
              onSelect={onSelect}
            />
          ))
        )}
      </div>
    </section>
  );
}

interface RowProps {
  report: Report;
  selected: boolean;
  onSelect: (id: string) => void;
}

function ReportRow({ report, selected, onSelect }: RowProps) {
  const meta = TRIGGER_META[report.trigger_type];
  const Icon = meta.Icon;
  const rec = report.recommendation;
  const recChipClass = rec ? REC_CHIP[rec] : null;

  return (
    <button
      type="button"
      onClick={() => onSelect(report.report_id)}
      title={report.headline}
      className={cn(
        "w-full px-2.5 py-2 flex items-start gap-2.5 text-left transition-colors border-l-2",
        selected
          ? "bg-line-1 border-ink-1"
          : "border-transparent hover:bg-line-1/60",
      )}
    >
      <span
        className={cn(
          "shrink-0 mt-0.5 inline-flex items-center justify-center w-7 h-7 rounded-md",
          meta.iconClass,
        )}
        aria-hidden
        title={meta.label}
      >
        <Icon className="w-3.5 h-3.5" />
      </span>

      <span className="flex-1 min-w-0">
        <span className="block text-[12.5px] text-ink-1 leading-snug line-clamp-2">
          {report.headline}
        </span>
        <span className="mt-1 flex items-center gap-2 text-[10.5px] text-ink-3 tabular-nums">
          <span>{meta.label}</span>
          <span aria-hidden>·</span>
          <span>{ageLabel(report.created_at)}</span>
          {rec && recChipClass && (
            <span
              className={cn(
                "ml-auto inline-flex items-center px-1.5 py-0.5 rounded text-[9.5px] font-semibold uppercase tracking-wider",
                recChipClass,
              )}
            >
              {rec}
            </span>
          )}
        </span>
      </span>

      {selected && (
        <span className="shrink-0 text-ink-3 text-[12px] mt-0.5" aria-hidden>
          ›
        </span>
      )}
    </button>
  );
}
