/**
 * Dashboard — Decision Room (/) (reports model 2026-05-21).
 *
 * Layout:
 *   [Header — Decision Room]
 *   [DailyReportHero — 오늘 조달 권고 (참고용, read-only)]
 *   [Grid 5/12: ReportsInbox | 7/12: SelectedReportDetail]
 *   [Signal Strength — Bidirectional3Zone]
 *   [Market Memory]
 */
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePatternCurrent, useReportsInbox } from "../lib/queries";
import { Bidirectional3Zone } from "../components/Bidirectional3Zone";
import { DailyReportHero } from "../components/DailyReportHero";
import { ReportsInbox } from "../components/ReportsInbox";
import { SelectedReportDetail } from "../components/SelectedReportDetail";
import { SimilarPastWidget } from "../components/SimilarPastWidget";

export function Dashboard() {
  const navigate = useNavigate();
  const inbox = useReportsInbox(10);
  const pattern = usePatternCurrent();
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);

  const cur = pattern.data?.current ?? null;
  const reports = inbox.data?.items ?? [];

  const selectedReportId = useMemo(() => {
    if (selectedId && reports.some((r) => r.report_id === selectedId)) {
      return selectedId;
    }
    return reports[0]?.report_id;
  }, [reports, selectedId]);

  // thread 자식 클릭 시: inbox에 있으면 선택만 변경, 아니면 archive로 navigate
  const handleSelectThread = (id: string) => {
    if (reports.some((r) => r.report_id === id)) {
      setSelectedId(id);
    } else {
      navigate(`/archive?focus=${id}`);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* PAGE HEADER                                                  */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <header className="mb-5 flex items-baseline justify-between flex-wrap gap-3">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3">
          Decision Room
        </div>
      </header>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* DAILY REPORT HERO — 06:30 KST 종합 보고서 (참고용)            */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <div className="mb-6">
        <DailyReportHero />
      </div>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {/* INBOX + DETAIL — 5/12 + 7/12                                 */}
      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-10">
        <div className="lg:col-span-5">
          <ReportsInbox
            reports={reports}
            selectedId={selectedReportId}
            onSelect={setSelectedId}
          />
        </div>
        <div className="lg:col-span-7">
          <SelectedReportDetail
            reportId={selectedReportId}
            isLoading={inbox.isLoading}
            onSelectThread={handleSelectThread}
          />
        </div>
      </div>

      {/* SIGNAL STRENGTH — Bidirectional (자체 header 보유) */}
      <div className="mt-12">
        <Bidirectional3Zone cur={cur} />
      </div>

      {/* MARKET MEMORY */}
      <SectionHeader title="Market Memory" subtitle="7년 backtest analog" />
      <SimilarPastWidget cur={cur} />

      <div className="h-12" />
    </div>
  );
}

function SectionHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mt-12 mb-5 pb-3 border-b border-line-1">
      <h2 className="font-display text-lg font-semibold text-ink-1 tracking-tight mb-0.5">
        {title}
      </h2>
      {subtitle && <p className="text-xs text-ink-3">{subtitle}</p>}
    </div>
  );
}
