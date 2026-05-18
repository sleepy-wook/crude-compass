/**
 * NewsTopList — 최근 7일 importance ≥ 60 + bullish/bearish 뉴스.
 *
 * 시나리오 §6.3 #3 anchor — Discovery "오늘의 발견" 뉴스 리스트.
 * 데이터 source: `gold.news_top_signals` view (bronze.news_articles).
 */
import { useNewsTop } from "../lib/queries";
import { relativeTime } from "../lib/utils";

const DIRECTION_LABEL: Record<string, { label: string; cls: string }> = {
  bullish: {
    label: "위기↑",
    cls: "bg-crisis-50 text-crisis-700 border-crisis-100",
  },
  bearish: {
    label: "약세↓",
    cls: "bg-opportunity-50 text-opportunity-700 border-opportunity-100",
  },
  neutral: { label: "—", cls: "bg-line-1 text-ink-3 border-line-2" },
};

const CATEGORY_LABEL: Record<string, string> = {
  geopolitics: "지정학",
  geopolitical: "지정학",
  supply: "공급",
  demand: "수요",
  macro: "거시",
  policy: "정책",
  sanctions: "제재",
  conflict: "분쟁",
  inventory: "재고",
  production_cut: "감산",
  shipping: "해운",
  recession: "경기 침체",
  energy: "에너지",
  trade: "교역",
  // GDELT aggregate / region-specific tags
  russia_ukraine: "러시아·우크라이나",
  iran_sanctions: "이란 제재",
  venezuela_sanctions: "베네수엘라 제재",
  china_demand: "중국 수요",
  middle_east: "중동",
  hormuz: "호르무즈",
  saudi: "사우디",
  opec: "OPEC",
  spr_release: "전략비축유 방출",
  GDELT_aggregate: "GDELT 종합",
  gdelt_aggregate: "GDELT 종합",
};

// Unknown category → underscore를 공백으로 + 첫 글자 대문자 (raw key 노출 방어)
function prettifyCategory(raw: string): string {
  if (raw in CATEGORY_LABEL) return CATEGORY_LABEL[raw];
  return raw.replace(/_/g, " ");
}

// GDELT raw title을 매니저-friendly로 변환.
// 입력 예: "GDELT signal · venezuela_sanctions · tone=-0.02"
// 출력 예: "베네수엘라 제재 — 약한 부정 톤"
function prettifyNewsTitle(raw: string): string {
  const m = raw.match(/GDELT\s+signal\s*[·•|-]\s*([a-zA-Z_]+)\s*[·•|-]\s*tone\s*=\s*(-?\d+\.?\d*)/i);
  if (!m) return raw;
  const [, rawCat, toneStr] = m;
  const cat = prettifyCategory(rawCat);
  const tone = parseFloat(toneStr);
  const toneLabel =
    tone <= -3
      ? "강한 부정 톤"
      : tone <= -1
        ? "부정 톤"
        : tone <= -0.3
          ? "약한 부정 톤"
          : tone < 0.3
            ? "중립 톤"
            : tone < 1
              ? "약한 긍정 톤"
              : "긍정 톤";
  return `${cat} — ${toneLabel}`;
}

export function NewsTopList({ limit = 12 }: { limit?: number }) {
  const { data, isLoading, isError } = useNewsTop(limit);
  const items = data?.items ?? [];

  return (
    <section className="mb-10">
      <div className="flex items-baseline justify-between mb-5">
        <h3 className="font-display text-lg font-semibold tracking-tight text-ink-1">
          주요 보도
        </h3>
        <span className="text-[11px] text-ink-3">최근 7일</span>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-14 rounded-lg border border-line-1 bg-line-1/40 animate-pulse"
            />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-line-1 bg-panel p-4 text-xs text-ink-3">
          뉴스 데이터 일시 불가.
        </div>
      )}

      {!isLoading && !isError && items.length === 0 && (
        <div className="rounded-lg border border-line-1 bg-panel p-4 text-xs text-ink-3">
          최근 7일 importance ≥ 60 뉴스 없음. GDELT 15분 cron 누적 대기.
        </div>
      )}

      {!isLoading && !isError && items.length > 0 && (
        <ul className="space-y-2">
          {items.map((n, idx) => {
            const dir = DIRECTION_LABEL[n.direction] ?? DIRECTION_LABEL.neutral;
            const cat = n.category ? prettifyCategory(n.category) : null;
            return (
              <li
                key={`${n.event_date}-${idx}`}
                className="rounded-lg border border-line-1 bg-panel hover:bg-line-1/30 transition-colors"
              >
                {n.url ? (
                  <a
                    href={n.url}
                    target="_blank"
                    rel="noreferrer"
                    className="block p-3"
                  >
                    <NewsItemContent
                      title={n.title}
                      source={n.source}
                      tier={n.tier}
                      eventDate={n.event_date}
                      category={cat}
                      direction={dir}
                      importance={n.importance}
                      mentionCount={n.mention_count}
                    />
                  </a>
                ) : (
                  <div className="block p-3">
                    <NewsItemContent
                      title={n.title}
                      source={n.source}
                      tier={n.tier}
                      eventDate={n.event_date}
                      category={cat}
                      direction={dir}
                      importance={n.importance}
                      mentionCount={n.mention_count}
                    />
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

interface NewsItemContentProps {
  title: string;
  source: string | null;
  tier: string | null;
  eventDate: string;
  category: string | null;
  direction: { label: string; cls: string };
  importance: number | null;
  mentionCount: number | null;
}

function NewsItemContent({
  title,
  source,
  tier,
  eventDate,
  category,
  direction,
  importance,
  mentionCount,
}: NewsItemContentProps) {
  return (
    <>
      <div className="flex items-start gap-2 mb-1.5">
        <span
          className={`shrink-0 inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] border font-medium ${direction.cls}`}
        >
          {direction.label}
        </span>
        {category && (
          <span className="shrink-0 inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] border bg-line-1 text-ink-2 border-line-2 font-medium">
            {category}
          </span>
        )}
        <span className="shrink-0 text-[10px] text-ink-3 font-mono">
          중요도 {importance ?? "—"} · 보도 {mentionCount ?? "—"}회
        </span>
      </div>
      <div className="text-sm text-ink leading-snug line-clamp-2 mb-1">
        {prettifyNewsTitle(title)}
      </div>
      <div className="flex items-center gap-2 text-[11px] text-ink-3 font-mono">
        <span>{source ? prettifyCategory(source) : "GDELT"}</span>
        {tier && <span>· {tier}급 매체</span>}
        <span className="ml-auto">{relativeTime(eventDate + "T00:00:00Z")}</span>
      </div>
    </>
  );
}
