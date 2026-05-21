/**
 * LibraryPage — 자료실 (/library) (2026-05-21 reports model 부수).
 *
 * 2 tabs:
 *   [OPEC 월간 보고서]  bronze.opec_momr_parsed (gold.opec_demand_gap view)
 *   [주요 보도]          GDELT importance >= 70 article
 *
 * Layout (Archive와 동일 패턴):
 *   - 좌 5/12: list (날짜 정렬)
 *   - 우 7/12: detail
 *   둘 다 h-[680px], 좌측 scroll
 */
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ExternalLink, Search } from "lucide-react";
import { useNewsTop, useOpecHistory } from "../lib/queries";
import { cn } from "../lib/utils";

type TabKey = "opec" | "news";

export function LibraryPage() {
  const [searchParams] = useSearchParams();
  const focus = searchParams.get("focus") ?? undefined;
  const [tab, setTab] = useState<TabKey>(
    searchParams.get("tab") === "news" ? "news" : "opec",
  );

  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      <header className="mb-5">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-1">
          Library
        </div>
        <h1 className="font-display text-xl font-semibold text-ink-1 tracking-tight">
          자료실
        </h1>
        <p className="text-[12px] text-ink-3 mt-1">
          OPEC 월간 보고서와 GDELT 주요 보도 — AI 보고서가 인용하는 원본 자료.
        </p>
      </header>

      {/* Tabs */}
      <div className="flex items-center gap-0.5 mb-5 border-b border-line-1">
        <TabButton
          active={tab === "opec"}
          onClick={() => setTab("opec")}
          label="OPEC 월간 보고서"
        />
        <TabButton
          active={tab === "news"}
          onClick={() => setTab("news")}
          label="주요 보도"
        />
      </div>

      {tab === "opec" ? <OpecTab /> : <NewsTab initialFocus={focus} />}

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
// Tab 1: OPEC 월간 보고서
// ─────────────────────────────────────────────────────────────────────
type OpecItem = NonNullable<ReturnType<typeof useOpecHistory>["data"]>["items"][number];

function OpecTab() {
  const { data, isLoading } = useOpecHistory(36);
  const items = data?.items ?? [];

  // 년도별 분리 — report_month "YYYY-MM" 앞 4자리.
  const years = useMemo(() => {
    const set = new Set(items.map((m) => m.report_month.slice(0, 4)));
    return Array.from(set).sort((a, b) => b.localeCompare(a));
  }, [items]);

  const [selectedYear, setSelectedYear] = useState<string | undefined>(undefined);
  const activeYear = selectedYear && years.includes(selectedYear) ? selectedYear : years[0];

  const yearItems = useMemo(
    () => items.filter((m) => m.report_month.slice(0, 4) === activeYear),
    [items, activeYear],
  );

  const [selectedMonth, setSelectedMonth] = useState<string | undefined>(undefined);
  const selected = useMemo(() => {
    if (selectedMonth && yearItems.some((m) => m.report_month === selectedMonth)) {
      return yearItems.find((m) => m.report_month === selectedMonth);
    }
    return yearItems[0];
  }, [yearItems, selectedMonth]);

  return (
    <>
      {/* Year filter */}
      {years.length > 0 && (
        <div className="flex items-center gap-1 mb-4 flex-wrap">
          {years.map((y) => (
            <button
              key={y}
              type="button"
              onClick={() => setSelectedYear(y)}
              className={cn(
                "px-3 py-1.5 text-[12px] rounded-md border transition-colors tabular-nums",
                y === activeYear
                  ? "border-ink-1 bg-ink-1 text-paper font-medium"
                  : "border-line-2 text-ink-2 hover:bg-line-1",
              )}
            >
              {y}년
            </button>
          ))}
          <span className="ml-2 text-[11px] text-ink-3 tabular-nums">{yearItems.length}건</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-5">
          <OpecList
            items={yearItems}
            selectedMonth={selected?.report_month}
            onSelect={setSelectedMonth}
            isLoading={isLoading}
          />
        </div>
        <div className="lg:col-span-7">
          <OpecDetail item={selected} isLoading={isLoading} />
        </div>
      </div>
    </>
  );
}

function OpecList({
  items,
  selectedMonth,
  onSelect,
  isLoading,
}: {
  items: OpecItem[];
  selectedMonth: string | undefined;
  onSelect: (m: string) => void;
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
          OPEC MOMR{" "}
          <span className="text-ink-3 tabular-nums font-normal">({items.length})</span>
        </h2>
        <p className="text-[10.5px] text-ink-3 mt-1 leading-snug">
          월별 사우디·이란 생산 + 수요 전망 + 수급 갭
        </p>
      </header>
      <div className="flex-1 overflow-y-auto py-1">
        {items.length === 0 ? (
          <div className="px-4 py-10 text-center text-[12px] text-ink-3">데이터 없음</div>
        ) : (
          items.map((m) => (
            <OpecRow
              key={m.report_month}
              item={m}
              selected={m.report_month === selectedMonth}
              onSelect={() => onSelect(m.report_month)}
            />
          ))
        )}
      </div>
    </section>
  );
}

function OpecRow({
  item,
  selected,
  onSelect,
}: {
  item: OpecItem;
  selected: boolean;
  onSelect: () => void;
}) {
  const delta = item.saudi_delta_vs_prev;
  const balance = item.market_balance;
  const balanceLabel =
    balance === "decrease"
      ? "감산"
      : balance === "increase"
        ? "증산"
        : balance === "steady"
          ? "유지"
          : "—";
  const balanceTone =
    balance === "decrease"
      ? "bg-crisis-50 text-crisis-700"
      : balance === "increase"
        ? "bg-opportunity-50 text-opportunity-700"
        : "bg-line-1 text-ink-3";

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
            {item.report_month}
          </span>
          <span
            className={cn(
              "inline-flex items-center px-1.5 py-0.5 rounded text-[9.5px] font-semibold uppercase tracking-wider",
              balanceTone,
            )}
          >
            {balanceLabel}
          </span>
        </span>
        <span className="mt-1 flex items-center gap-2 text-[10.5px] text-ink-3 tabular-nums">
          <span>사우디 {item.saudi_kbbl_d?.toFixed(0) ?? "—"} kbd</span>
          {delta != null && delta !== 0 && (
            <span className={cn(
              "font-medium",
              delta > 0 ? "text-crisis-700" : "text-opportunity-700",
            )}>
              {delta > 0 ? "+" : ""}{delta.toFixed(0)}
            </span>
          )}
          <span aria-hidden>·</span>
          <span>수요 {item.forecast_demand_kbbl_d?.toFixed(0) ?? "—"}</span>
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

function OpecDetail({ item, isLoading }: { item: OpecItem | undefined; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="bg-white border border-line-2 rounded-2xl p-8 flex items-center text-sm text-ink-3 h-[680px] shadow-sm">
        불러오는 중...
      </div>
    );
  }
  if (!item) {
    return (
      <div className="bg-white border border-line-2 rounded-2xl p-6 h-[680px] flex flex-col justify-center shadow-sm">
        <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">보고서</div>
        <div className="text-base text-ink-1">선택된 월 없음</div>
      </div>
    );
  }

  const balance = item.market_balance;
  const balanceLabel =
    balance === "decrease"
      ? "감산"
      : balance === "increase"
        ? "증산"
        : balance === "steady"
          ? "유지"
          : "—";
  const balanceTone =
    balance === "decrease"
      ? "bg-crisis-50 text-crisis-700 border-crisis-200"
      : balance === "increase"
        ? "bg-opportunity-50 text-opportunity-700 border-opportunity-200"
        : "bg-line-1 text-ink-3 border-line-2";

  return (
    <div className="bg-white border border-line-2 rounded-2xl p-6 flex flex-col h-[680px] overflow-y-auto shadow-sm">
      <div className="flex items-baseline justify-between mb-4 flex-wrap gap-2">
        <div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-ink-3 mb-0.5">
            OPEC MOMR · ai_parse_document
          </div>
          <h3 className="font-display text-[20px] font-semibold text-ink-1 tracking-tight tabular-nums">
            {item.report_month}
          </h3>
        </div>
        <span className={cn("inline-flex items-center px-2.5 py-1 rounded-md text-[11px] border font-medium", balanceTone)}>
          OPEC {balanceLabel}
        </span>
      </div>

      {/* 핵심 지표 grid */}
      <div className="grid grid-cols-2 gap-4 mb-5">
        <Stat
          label="사우디 생산"
          value={item.saudi_kbbl_d?.toFixed(0)}
          unit="kbd"
          delta={item.saudi_delta_vs_prev}
        />
        <Stat
          label="이란 생산"
          value={item.iran_kbbl_d?.toFixed(0)}
          unit="kbd"
        />
        <Stat
          label="OPEC 전체"
          value={item.opec_total_kbbl_d?.toFixed(0)}
          unit="kbd"
        />
        <Stat
          label="글로벌 수요 전망"
          value={item.forecast_demand_kbbl_d?.toFixed(0)}
          unit="kbd"
        />
      </div>

      {/* OPEC 생산 전월 대비 (MoM) */}
      {item.supply_demand_gap_kbbl_d != null && (
        <div className="rounded-md border border-line-1 bg-paper px-4 py-3 mb-4">
          <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">
            OPEC 생산 전월 대비 (MoM)
          </div>
          <div className="flex items-baseline gap-2 tabular-nums">
            <span className={cn(
              "font-display text-2xl font-semibold",
              item.supply_demand_gap_kbbl_d > 0
                ? "text-opportunity-700"
                : item.supply_demand_gap_kbbl_d < 0
                  ? "text-crisis-700"
                  : "text-ink-1",
            )}>
              {item.supply_demand_gap_kbbl_d > 0 ? "+" : ""}{item.supply_demand_gap_kbbl_d.toFixed(0)}
            </span>
            <span className="text-[11px] text-ink-3">kbd</span>
          </div>
        </div>
      )}

      {/* 해석 */}
      <div className="text-[12.5px] text-ink-2 leading-relaxed mt-3 pt-3 border-t border-line-1">
        {balance === "decrease" && (
          <p>
            OPEC 전월 대비 감산. 공급 축소 → 단기 가격 상승 압력. 정유사 매입 비용 ↑ 가능성 (위험 신호).
          </p>
        )}
        {balance === "increase" && (
          <p>
            OPEC 전월 대비 증산. 공급 확대 → 가격 약세 압력. Spot 발주 타이밍 유리할 수 있음 (안정 신호).
          </p>
        )}
        {balance === "steady" && (
          <p>
            OPEC 생산 전월 수준 유지. 외부 충격(지정학·계절성) 없으면 공급 측 가격 영향 중립.
          </p>
        )}
      </div>

      <div className="mt-auto pt-4 text-[10.5px] text-ink-3 italic">
        Databricks Document Intelligence — OPEC MOMR PDF → ai_parse_document() → bronze.opec_momr_parsed
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  unit,
  delta,
}: {
  label: string;
  value: string | undefined | null;
  unit: string;
  delta?: number | null;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">{label}</div>
      <div className="flex items-baseline gap-2 tabular-nums">
        <span className="font-display text-xl font-semibold text-ink-1">{value ?? "—"}</span>
        <span className="text-[11px] text-ink-3">{unit}</span>
        {delta != null && delta !== 0 && (
          <span className={cn(
            "text-[11px] font-medium ml-1",
            delta > 0 ? "text-crisis-700" : "text-opportunity-700",
          )}>
            {delta > 0 ? "+" : ""}{delta.toFixed(0)}
          </span>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Tab 2: 주요 보도 (GDELT)
// ─────────────────────────────────────────────────────────────────────
type NewsItem = NonNullable<ReturnType<typeof useNewsTop>["data"]>["items"][number];

function NewsTab({ initialFocus }: { initialFocus?: string }) {
  const { data, isLoading } = useNewsTop(80);
  const items = data?.items ?? [];
  const [titleQuery, setTitleQuery] = useState("");
  const [dirFilter, setDirFilter] = useState<"all" | "bullish" | "bearish">("all");

  const filtered = useMemo(() => {
    const q = titleQuery.trim().toLowerCase();
    return items.filter((n) => {
      if (q && !n.title.toLowerCase().includes(q)) return false;
      if (dirFilter !== "all" && n.direction !== dirFilter) return false;
      return true;
    });
  }, [items, titleQuery, dirFilter]);

  const [selectedTitle, setSelectedTitle] = useState<string | undefined>(initialFocus);
  const selected = useMemo(() => {
    if (selectedTitle) {
      const found = filtered.find((n) => n.title === selectedTitle);
      if (found) return found;
    }
    return filtered[0];
  }, [filtered, selectedTitle]);

  // Pagination — 10개 단위. 필터 변경 시 1페이지로 reset.
  const PAGE_SIZE = 10;
  const [page, setPage] = useState(0);
  useEffect(() => setPage(0), [titleQuery, dirFilter]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const paged = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  return (
    <>
      {/* Filters */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
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
          {(["all", "bullish", "bearish"] as const).map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDirFilter(d)}
              className={cn(
                "px-2.5 py-1 text-[11px] rounded transition-colors",
                dirFilter === d
                  ? "bg-line-1 text-ink-1 font-medium"
                  : "text-ink-3 hover:text-ink-1",
              )}
            >
              {d === "all" ? "전체" : d === "bullish" ? "위험" : "안정"}
            </button>
          ))}
        </div>
        <span className="ml-2 text-[11px] text-ink-3 tabular-nums">
          {filtered.length} / {items.length}건
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-5">
          <NewsList
            items={paged}
            total={filtered.length}
            selected={selected?.title}
            onSelect={setSelectedTitle}
            isLoading={isLoading}
            page={safePage}
            pageCount={pageCount}
            onPage={setPage}
          />
        </div>
        <div className="lg:col-span-7">
          <NewsDetail item={selected} isLoading={isLoading} />
        </div>
      </div>
    </>
  );
}

function NewsList({
  items,
  total,
  selected,
  onSelect,
  isLoading,
  page,
  pageCount,
  onPage,
}: {
  items: NewsItem[];
  total: number;
  selected: string | undefined;
  onSelect: (title: string) => void;
  isLoading: boolean;
  page: number;
  pageCount: number;
  onPage: (p: number) => void;
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
          GDELT 주요 보도{" "}
          <span className="text-ink-3 tabular-nums font-normal">({total})</span>
        </h2>
        <p className="text-[10.5px] text-ink-3 mt-1 leading-snug">
          importance ≥ 60 · 최근 7일 · A·B tier 신뢰 source
        </p>
      </header>
      <div className="flex-1 overflow-y-auto py-1">
        {total === 0 ? (
          <div className="px-4 py-10 text-center text-[12px] text-ink-3">조건 일치 보도 없음</div>
        ) : (
          items.map((n, i) => (
            <NewsRow
              key={`${n.title}-${i}`}
              item={n}
              selected={n.title === selected}
              onSelect={() => onSelect(n.title)}
            />
          ))
        )}
      </div>
      <Pagination page={page} pageCount={pageCount} onPage={onPage} />
    </section>
  );
}

// 숫자형 pagination — « ‹ 1 2 3 … › »
function Pagination({
  page,
  pageCount,
  onPage,
}: {
  page: number;
  pageCount: number;
  onPage: (p: number) => void;
}) {
  if (pageCount <= 1) return null;
  const WINDOW = 7;
  let start = Math.max(0, page - Math.floor(WINDOW / 2));
  const end = Math.min(pageCount, start + WINDOW);
  start = Math.max(0, end - WINDOW);
  const nums: number[] = [];
  for (let i = start; i < end; i++) nums.push(i);

  const base =
    "min-w-[26px] h-[26px] px-1.5 text-[11px] rounded-md border transition-colors disabled:opacity-30 disabled:cursor-not-allowed tabular-nums";
  const ctrl = cn(base, "border-line-2 text-ink-3 hover:bg-line-1");

  return (
    <div className="border-t border-line-1 px-3 py-2 flex items-center justify-center gap-1">
      <button type="button" onClick={() => onPage(0)} disabled={page <= 0} className={ctrl} aria-label="처음">
        «
      </button>
      <button type="button" onClick={() => onPage(page - 1)} disabled={page <= 0} className={ctrl} aria-label="이전">
        ‹
      </button>
      {nums.map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onPage(n)}
          className={cn(
            base,
            n === page
              ? "border-ink-1 bg-ink-1 text-paper font-semibold"
              : "border-line-2 text-ink-2 hover:bg-line-1",
          )}
        >
          {n + 1}
        </button>
      ))}
      <button type="button" onClick={() => onPage(page + 1)} disabled={page >= pageCount - 1} className={ctrl} aria-label="다음">
        ›
      </button>
      <button type="button" onClick={() => onPage(pageCount - 1)} disabled={page >= pageCount - 1} className={ctrl} aria-label="끝">
        »
      </button>
    </div>
  );
}

function NewsRow({
  item,
  selected,
  onSelect,
}: {
  item: NewsItem;
  selected: boolean;
  onSelect: () => void;
}) {
  const dirLabel =
    item.direction === "bullish" ? "위험" : item.direction === "bearish" ? "안정" : "중립";
  const dirTone =
    item.direction === "bullish"
      ? "bg-crisis-50 text-crisis-700"
      : item.direction === "bearish"
        ? "bg-opportunity-50 text-opportunity-700"
        : "bg-line-1 text-ink-3";

  return (
    <button
      type="button"
      onClick={onSelect}
      title={item.title}
      className={cn(
        "w-full px-2.5 py-2 flex items-start gap-2.5 text-left transition-colors border-l-2",
        selected
          ? "bg-line-1 border-ink-1"
          : "border-transparent hover:bg-line-1/60",
      )}
    >
      <span className="flex-1 min-w-0">
        <span className="block text-[12.5px] text-ink-1 leading-snug line-clamp-2">
          {item.title}
        </span>
        <span className="mt-1 flex items-center gap-2 text-[10.5px] text-ink-3 tabular-nums">
          <span>{item.source ?? "—"}</span>
          {item.tier && (
            <>
              <span aria-hidden>·</span>
              <span>{item.tier} tier</span>
            </>
          )}
          <span aria-hidden>·</span>
          <span>{item.event_date}</span>
          <span
            className={cn(
              "ml-auto inline-flex items-center px-1.5 py-0.5 rounded text-[9.5px] font-semibold",
              dirTone,
            )}
          >
            {dirLabel} {item.importance ?? "—"}
          </span>
        </span>
      </span>
    </button>
  );
}

// GDELT는 기사 본문을 제공하지 않음 → 집계 메타로 해석 문단 합성 (정직: 통계 기반).
function newsSummary(item: NewsItem): string {
  const theme = item.title.startsWith("GDELT signal")
    ? item.title.replace(/^GDELT signal\s*·\s*/, "").split("·")[0].trim()
    : null;
  const tone = item.raw_tone;
  const toneText =
    tone == null
      ? "논조 데이터 없음"
      : tone <= -2
        ? `강한 부정 논조 (tone ${tone.toFixed(2)})`
        : tone < 0
          ? `부정 논조 (tone ${tone.toFixed(2)})`
          : tone > 0
            ? `긍정 논조 (tone ${tone.toFixed(2)})`
            : `중립 논조 (tone ${tone.toFixed(2)})`;
  const dirText =
    item.direction === "bullish"
      ? "원유 상방(위험) 압력 시그널"
      : item.direction === "bearish"
        ? "원유 하방(안정) 압력 시그널"
        : "중립 분류";
  const parts: string[] = [];
  parts.push(theme ? `${theme} 테마 GDELT 집계 신호.` : "GDELT 보도 신호.");
  if (item.mention_count != null) parts.push(`최근 7일 ${item.mention_count.toLocaleString()}건 언급,`);
  parts.push(`${toneText}.`);
  parts.push(`${dirText} (중요도 ${item.importance ?? "—"}/100).`);
  parts.push("개별 기사 본문은 GDELT API가 제공하지 않아 '원문 보기'로 확인.");
  return parts.join(" ");
}

function NewsDetail({ item, isLoading }: { item: NewsItem | undefined; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="bg-white border border-line-2 rounded-2xl p-8 flex items-center text-sm text-ink-3 h-[680px] shadow-sm">
        불러오는 중...
      </div>
    );
  }
  if (!item) {
    return (
      <div className="bg-white border border-line-2 rounded-2xl p-6 h-[680px] flex flex-col justify-center shadow-sm">
        <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">보도</div>
        <div className="text-base text-ink-1">선택된 보도 없음</div>
      </div>
    );
  }

  const dirLabel =
    item.direction === "bullish" ? "위험 신호" : item.direction === "bearish" ? "안정 신호" : "중립";
  const dirTone =
    item.direction === "bullish"
      ? "bg-crisis-50 text-crisis-700 border-crisis-200"
      : item.direction === "bearish"
        ? "bg-opportunity-50 text-opportunity-700 border-opportunity-200"
        : "bg-line-1 text-ink-3 border-line-2";

  return (
    <div className="bg-white border border-line-2 rounded-2xl p-6 flex flex-col h-[680px] overflow-y-auto shadow-sm">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-[10px] tracking-wider border font-medium", dirTone)}>
          {dirLabel}
        </span>
        {item.category && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] tracking-wider border font-medium bg-transparent text-ink-3 border-line-2">
            {item.category}
          </span>
        )}
        <span className="ml-auto text-[10px] text-ink-3 tabular-nums">
          {item.event_date}
        </span>
      </div>

      <h3 className="font-display text-[17px] font-semibold text-ink-1 leading-snug mb-3">
        {item.title}
      </h3>

      {/* 해석 — GDELT는 본문 미제공. 집계 메타(테마·tone·언급수·방향)로 합성 */}
      <p className="text-[12.5px] text-ink-2 leading-relaxed mb-4 pb-4 border-b border-line-1">
        {newsSummary(item)}
      </p>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <Stat label="중요도" value={item.importance?.toString()} unit="/100" />
        <Stat label="GDELT tone" value={item.raw_tone?.toFixed(2)} unit="" />
        <Stat label="언급 횟수" value={item.mention_count?.toString()} unit="" />
      </div>

      <div className="rounded-md border border-line-1 bg-paper px-4 py-3 mb-4 text-[12.5px] text-ink-2 leading-relaxed">
        <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">source</div>
        <div className="text-ink-1 font-medium">
          {item.source ?? "—"}
          {item.tier && (
            <span className="ml-2 text-[10px] uppercase tracking-wider text-ink-3 font-normal">
              · {item.tier} tier (신뢰도 등급)
            </span>
          )}
        </div>
      </div>

      {item.url && (
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-[12px] font-medium border border-line-2 bg-white text-ink-1 hover:bg-line-1 transition-colors self-start"
        >
          원문 보기 <ExternalLink className="w-3 h-3" />
        </a>
      )}

      <div className="mt-auto pt-4 text-[10.5px] text-ink-3 italic">
        GDELT DOC API · 15분 cron 적재 · bronze.news_articles
      </div>
    </div>
  );
}
