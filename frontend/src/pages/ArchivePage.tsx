/**
 * ArchivePage — 보고서 보관함 (reports model 2026-05-21).
 *
 * 2 tabs:
 *   [트리거 보고서]  status별 (활성화/Drop/AI Drop/보관) + 제목/날짜 필터
 *   [일일 보고서]    06:35 KST cron 생성 daily report history
 *
 * URL focus param: /archive?focus=<report_id> → 트리거 탭으로 진입 + 보고서 선택
 */
import { useEffect, useMemo, useState } from "react";
import { Activity, DollarSign, Newspaper, Search } from "lucide-react";
import type { ComponentType } from "react";
import { useSearchParams } from "react-router-dom";
import {
  useDailyReportsRecent,
  useReportDetail,
  useReportsArchive,
} from "../lib/queries";
import { DailyReportDetail } from "../components/DailyReportDetail";
import { SelectedReportDetail } from "../components/SelectedReportDetail";
import { cn } from "../lib/utils";
import type {
  DailyReport,
  Recommendation,
  Report,
  ReportStatus,
  TriggerType,
} from "../lib/types";

type TabKey = "reports" | "daily";

const TRIGGER_META: Record<
  TriggerType,
  { Icon: ComponentType<{ className?: string }>; iconClass: string; label: string }
> = {
  gdelt_signal: { Icon: Newspaper, iconClass: "text-info-700 bg-info-50", label: "뉴스" },
  price_spike: { Icon: DollarSign, iconClass: "text-opportunity-700 bg-opportunity-50", label: "가격" },
  pattern_drift: { Icon: Activity, iconClass: "text-amber-700 bg-amber-50", label: "추세" },
};

const STATUS_LABEL: Record<ReportStatus, string> = {
  pending: "검토 대기",
  kept: "활성화",
  archived: "보관",
  dropped: "Drop",
  ai_dropped: "AI Drop",
};

const REC_CHIP: Record<Recommendation, string> = {
  HOLD: "bg-line-1 text-ink-2",
  "DEFER SPOT": "bg-amber-50 text-amber-700",
  "ACCELERATE SPOT": "bg-opportunity-50 text-opportunity-700",
  "REVIEW TERM": "bg-info-50 text-info-700",
  HEDGE: "bg-crisis-50 text-crisis-700",
  DIVERSIFY: "bg-info-50 text-info-700",
};

const FILTERS: { value: ReportStatus; label: string }[] = [
  { value: "kept", label: "활성화 (대기 중)" },
  { value: "dropped", label: "Drop" },
  { value: "ai_dropped", label: "AI Drop" },
  { value: "archived", label: "보관" },
];

const DATE_PRESETS: { value: string; label: string; days: number | null }[] = [
  { value: "all", label: "전체", days: null },
  { value: "7d", label: "최근 7일", days: 7 },
  { value: "30d", label: "최근 30일", days: 30 },
  { value: "90d", label: "최근 90일", days: 90 },
];

const DIRECTION_CHIP: Record<string, { label: string; tone: string }> = {
  lean_hedge: { label: "위험방어", tone: "bg-crisis-50 text-crisis-700" },
  neutral: { label: "중립", tone: "bg-line-1 text-ink-3" },
  lean_opportunity: { label: "기회포착", tone: "bg-opportunity-50 text-opportunity-700" },
};

function ageLabel(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  return `${Math.floor(diff / 86400)}일 전`;
}

export function ArchivePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const focusId = searchParams.get("focus") || undefined;
  const initialTab = (searchParams.get("tab") as TabKey) || "reports";

  const [tab, setTab] = useState<TabKey>(initialTab);

  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      <header className="mb-5">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-1">
          Archive
        </div>
        <h1 className="font-display text-xl font-semibold text-ink-1 tracking-tight">
          보고서 보관함
        </h1>
        <p className="text-[12px] text-ink-3 mt-1">
          AI가 생성한 트리거 보고서 history와 매일 06:35 KST 일일 종합 보고서.
        </p>
      </header>

      {/* Tab strip */}
      <div className="flex items-center gap-0.5 mb-5 border-b border-line-1">
        <TabButton
          active={tab === "reports"}
          onClick={() => setTab("reports")}
          label="트리거 보고서"
        />
        <TabButton
          active={tab === "daily"}
          onClick={() => setTab("daily")}
          label="일일 보고서"
        />
      </div>

      {tab === "reports" ? (
        <TriggerReportsTab
          focusId={focusId}
          searchParams={searchParams}
          setSearchParams={setSearchParams}
          onSwitchToReports={() => setTab("reports")}
        />
      ) : (
        <DailyReportsTab
          onSelectKeptReport={(id) => {
            setTab("reports");
            setSearchParams({ focus: id }, { replace: true });
          }}
        />
      )}

      <div className="h-12" />
    </div>
  );
}

function TabButton({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "px-4 py-2.5 text-[13px] font-medium transition-colors border-b-2 -mb-px",
        active
          ? "border-ink-1 text-ink-1"
          : "border-transparent text-ink-3 hover:text-ink-1",
      )}
    >
      {label}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Tab 1: 트리거 보고서
// ─────────────────────────────────────────────────────────────────────
interface TriggerTabProps {
  focusId: string | undefined;
  searchParams: URLSearchParams;
  setSearchParams: (p: URLSearchParams | Record<string, string>, opts?: { replace?: boolean }) => void;
  onSwitchToReports: () => void;
}

function TriggerReportsTab({ focusId, searchParams, setSearchParams }: TriggerTabProps) {
  const [filter, setFilter] = useState<ReportStatus>("kept");
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const [titleQuery, setTitleQuery] = useState("");
  const [datePreset, setDatePreset] = useState<string>("all");

  // focus query param → 해당 보고서의 status로 auto-filter + 선택
  const focusDetail = useReportDetail(focusId);
  useEffect(() => {
    if (!focusId || !focusDetail.data) return;
    const target =
      focusDetail.data.thread.find((r) => r.report_id === focusId) ??
      focusDetail.data.root;
    setFilter(target.status as ReportStatus);
    setSelectedId(focusId);
    searchParams.delete("focus");
    setSearchParams(searchParams, { replace: true });
  }, [focusId, focusDetail.data, searchParams, setSearchParams]);

  const { data, isLoading } = useReportsArchive(filter, 200);
  const rawItems = data?.items ?? [];

  const items = useMemo(() => {
    const q = titleQuery.trim().toLowerCase();
    const preset = DATE_PRESETS.find((p) => p.value === datePreset);
    const cutoff = preset?.days != null ? Date.now() - preset.days * 86_400_000 : null;
    return rawItems.filter((r) => {
      if (q && !r.headline.toLowerCase().includes(q)) return false;
      if (cutoff != null && new Date(r.created_at).getTime() < cutoff) return false;
      return true;
    });
  }, [rawItems, titleQuery, datePreset]);

  const selected = useMemo(() => {
    if (selectedId && items.some((r) => r.report_id === selectedId)) return selectedId;
    return items[0]?.report_id;
  }, [items, selectedId]);

  const handleSelectThread = (id: string) => {
    if (items.some((r) => r.report_id === id)) {
      setSelectedId(id);
    } else {
      setSearchParams({ focus: id }, { replace: true });
    }
  };

  return (
    <>
      {/* Filter pills */}
      <div className="flex items-center gap-1.5 mb-3 flex-wrap">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => {
              setFilter(f.value);
              setSelectedId(undefined);
            }}
            className={cn(
              "px-3 py-1.5 rounded-md text-[12px] font-medium border transition-colors",
              filter === f.value
                ? "bg-ink-1 text-paper border-ink-1"
                : "bg-white text-ink-2 border-line-2 hover:bg-line-1",
            )}
          >
            {f.label}
          </button>
        ))}
        <span className="ml-2 text-[11px] text-ink-3 tabular-nums">
          {items.length} / {rawItems.length}건
        </span>
      </div>

      {/* 보조 필터 */}
      <div className="flex items-center gap-2 mb-5 flex-wrap">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ink-3" />
          <input
            type="text"
            value={titleQuery}
            onChange={(e) => setTitleQuery(e.target.value)}
            placeholder="제목 검색..."
            className="pl-8 pr-3 py-1.5 text-[12px] border border-line-2 rounded-md w-64 bg-white text-ink-1 placeholder:text-ink-3 focus:outline-none focus:border-ink-3"
          />
        </div>
        <div className="flex items-center gap-0.5 rounded-md border border-line-2 bg-white p-0.5">
          {DATE_PRESETS.map((p) => (
            <button
              key={p.value}
              type="button"
              onClick={() => setDatePreset(p.value)}
              className={cn(
                "px-2.5 py-1 text-[11px] rounded transition-colors",
                datePreset === p.value
                  ? "bg-line-1 text-ink-1 font-medium"
                  : "text-ink-3 hover:text-ink-1",
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
        {(titleQuery || datePreset !== "all") && (
          <button
            type="button"
            onClick={() => {
              setTitleQuery("");
              setDatePreset("all");
            }}
            className="text-[11px] text-ink-3 hover:text-ink-1 transition-colors"
          >
            초기화 ×
          </button>
        )}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-5">
          <ReportsList
            reports={items}
            selectedId={selected}
            onSelect={setSelectedId}
            isLoading={isLoading}
          />
        </div>
        <div className="lg:col-span-7">
          <SelectedReportDetail
            reportId={selected}
            isLoading={false}
            onSelectThread={handleSelectThread}
          />
        </div>
      </div>
    </>
  );
}

interface ListProps {
  reports: Report[];
  selectedId: string | undefined;
  onSelect: (id: string) => void;
  isLoading: boolean;
}

function ReportsList({ reports, selectedId, onSelect, isLoading }: ListProps) {
  if (isLoading) {
    return (
      <section className="bg-panel border border-line-1 rounded-2xl h-[680px] flex items-center justify-center text-[12px] text-ink-3">
        불러오는 중...
      </section>
    );
  }
  return (
    <section className="bg-panel border border-line-1 rounded-2xl flex flex-col h-[680px]">
      <div className="flex-1 overflow-y-auto py-1">
        {reports.length === 0 ? (
          <div className="px-4 py-10 text-center text-[12px] text-ink-3">
            조건에 맞는 보고서 없음
          </div>
        ) : (
          reports.map((r) => (
            <ArchiveRow
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

function ArchiveRow({ report, selected, onSelect }: RowProps) {
  const meta = TRIGGER_META[report.trigger_type];
  const Icon = meta.Icon;
  const rec = report.recommendation;
  const recChipClass = rec ? REC_CHIP[rec] : null;
  const isMuted = report.status === "dropped" || report.status === "ai_dropped";

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
        isMuted && "opacity-70",
      )}
    >
      <span
        className={cn(
          "shrink-0 mt-0.5 inline-flex items-center justify-center w-7 h-7 rounded-md",
          meta.iconClass,
        )}
        aria-hidden
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
          <span aria-hidden>·</span>
          <span className="text-ink-3">{STATUS_LABEL[report.status]}</span>
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

// ─────────────────────────────────────────────────────────────────────
// Tab 2: 일일 보고서
// ─────────────────────────────────────────────────────────────────────
function DailyReportsTab({ onSelectKeptReport }: { onSelectKeptReport: (id: string) => void }) {
  const { data, isLoading } = useDailyReportsRecent(30);
  const items = data?.items ?? [];
  const [selectedDate, setSelectedDate] = useState<string | undefined>(undefined);

  const selected = useMemo(() => {
    if (selectedDate && items.some((d) => d.report_date === selectedDate)) {
      return items.find((d) => d.report_date === selectedDate);
    }
    return items[0];
  }, [items, selectedDate]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <div className="lg:col-span-5">
        <DailyReportsList
          dailies={items}
          selectedDate={selected?.report_date}
          onSelect={setSelectedDate}
          isLoading={isLoading}
        />
      </div>
      <div className="lg:col-span-7">
        <DailyReportDetail
          daily={selected}
          isLoading={isLoading}
          onSelectKeptReport={onSelectKeptReport}
        />
      </div>
    </div>
  );
}

function DailyReportsList({
  dailies,
  selectedDate,
  onSelect,
  isLoading,
}: {
  dailies: DailyReport[];
  selectedDate: string | undefined;
  onSelect: (date: string) => void;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <section className="bg-panel border border-line-1 rounded-2xl h-[680px] flex items-center justify-center text-[12px] text-ink-3">
        불러오는 중...
      </section>
    );
  }

  return (
    <section className="bg-panel border border-line-1 rounded-2xl flex flex-col h-[680px]">
      <header className="px-4 py-3 border-b border-line-1">
        <h2 className="text-[13px] font-semibold text-ink-1 tracking-tight">
          일일 종합 보고서{" "}
          <span className="text-ink-3 tabular-nums font-normal">({dailies.length})</span>
        </h2>
        <p className="text-[10.5px] text-ink-3 mt-1 leading-snug">
          매일 06:35 KST · 어제 활성화 보고서 + 직전 daily 종합
        </p>
      </header>
      <div className="flex-1 overflow-y-auto py-1">
        {dailies.length === 0 ? (
          <div className="px-4 py-10 text-center text-[12px] text-ink-3">
            일일 보고서 없음
          </div>
        ) : (
          dailies.map((d) => (
            <DailyRow
              key={d.daily_id}
              daily={d}
              selected={d.report_date === selectedDate}
              onSelect={() => onSelect(d.report_date)}
            />
          ))
        )}
      </div>
    </section>
  );
}

function DailyRow({
  daily,
  selected,
  onSelect,
}: {
  daily: DailyReport;
  selected: boolean;
  onSelect: () => void;
}) {
  const dir = daily.ratio_suggestion?.direction || "neutral";
  const meta = DIRECTION_CHIP[dir] ?? DIRECTION_CHIP.neutral;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full px-2.5 py-2.5 flex items-start gap-2.5 text-left transition-colors border-l-2",
        selected
          ? "bg-line-1 border-ink-1"
          : "border-transparent hover:bg-line-1/60",
      )}
    >
      <span className="flex-1 min-w-0">
        <span className="flex items-baseline gap-2">
          <span className="font-display text-[13px] font-semibold text-ink-1 tabular-nums">
            {daily.report_date}
          </span>
          <span
            className={cn(
              "inline-flex items-center px-1.5 py-0.5 rounded text-[9.5px] font-semibold uppercase tracking-wider",
              meta.tone,
            )}
          >
            {meta.label}
          </span>
        </span>
        <span className="mt-1 flex items-center gap-2 text-[10.5px] text-ink-3 tabular-nums">
          <span>보관 {daily.kept_count}건</span>
          {daily.confidence !== null && (
            <>
              <span aria-hidden>·</span>
              <span>신뢰도 {Math.round(daily.confidence)}</span>
            </>
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
