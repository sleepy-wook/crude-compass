/**
 * TimeHorizonBreakdown — 시나리오 §6.5 시그널 시간 지평 분류.
 *
 *   Leading (D-7)      : GDELT 키워드 mention burst (휘발성)
 *   Macro (D-30~D-7)   : OPEC MOMR, USD/KRW (구조적)
 *   Fundamentals (D-1) : EIA 재고, 가격 spike (확인)
 *
 * → 단일 적중률로 평가하면 안 됨. 시간 지평별 lead time 차별화가 진짜 가치.
 */
import { useSignalContribution } from "../lib/queries";

type Horizon = "leading" | "macro" | "fundamentals";

const SIGNAL_HORIZON: Record<string, Horizon> = {
  news_tone: "leading",
  opec_momr: "macro",
  fx_krw_usd: "macro",
  eia_inventory: "fundamentals",
  price_spike: "fundamentals",
};

const SIGNAL_LABEL: Record<string, string> = {
  news_tone: "GDELT 뉴스 키워드 burst",
  opec_momr: "OPEC 사우디·이란 생산",
  fx_krw_usd: "USD/KRW 환율 추세",
  eia_inventory: "EIA 미국 재고",
  price_spike: "유가 급변동",
};

const HORIZON_META: Record<
  Horizon,
  { label: string; sub: string; lead: string; desc: string; color: string }
> = {
  leading: {
    label: "선행 (Leading)",
    sub: "가격 반영 전 감지",
    lead: "7일 ~ 1일 전",
    desc: "GDELT 글로벌 뉴스 키워드 burst — 시장이 반응하기 전 신호",
    color: "text-crisis-700",
  },
  macro: {
    label: "구조 (Macro)",
    sub: "산유국·환율 추세",
    lead: "30일 ~ 7일 전",
    desc: "OPEC 월간 보고서 + USD/KRW 환율 trend — 중기 펀더멘털",
    color: "text-ink-1",
  },
  fundamentals: {
    label: "확인 (Fundamentals)",
    sub: "재고·가격 직접",
    lead: "7일 전 ~ 1일 후",
    desc: "EIA 미국 재고 + 일별 유가 — 시장이 실제로 움직였는지 검증",
    color: "text-opportunity-700",
  },
};

export function TimeHorizonBreakdown() {
  const { data, isLoading } = useSignalContribution();
  const items = data?.items ?? [];

  // signal_type별 grouping (horizon)
  const grouped: Record<Horizon, { signal_type: string; direction: string; share_pct: number; n: number }[]> = {
    leading: [],
    macro: [],
    fundamentals: [],
  };
  for (const it of items) {
    const h = SIGNAL_HORIZON[it.signal_type];
    if (!h) continue;
    grouped[h].push({
      signal_type: it.signal_type,
      direction: it.direction,
      share_pct: it.share_pct,
      n: it.n_signals,
    });
  }

  return (
    <section className="bg-panel border border-line-1 rounded-xl p-6">
      <div className="mb-5">
        <h3 className="font-display text-base font-semibold text-ink-1">
          이번 권고의 시간 지평별 근거
        </h3>
        <p className="text-[11px] text-ink-3 mt-0.5">
          데이터 소스마다 시장 반영까지 걸리는 시간이 다릅니다. 단일 적중률이 아닌 시간 지평별 종합 신호.
        </p>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-16 rounded bg-line-1/40 animate-pulse" />
          ))}
        </div>
      )}

      {!isLoading && (
        <div className="space-y-4">
          {(Object.keys(HORIZON_META) as Horizon[]).map((h) => (
            <HorizonRow key={h} horizon={h} signals={grouped[h]} />
          ))}
        </div>
      )}
    </section>
  );
}

function HorizonRow({
  horizon,
  signals,
}: {
  horizon: Horizon;
  signals: { signal_type: string; direction: string; share_pct: number; n: number }[];
}) {
  const meta = HORIZON_META[horizon];
  const totalShare = signals.reduce((s, x) => s + x.share_pct, 0);

  return (
    <div className="pb-4 border-b border-line-1 last:border-0 last:pb-0">
      <div className="flex items-baseline justify-between mb-2">
        <div className="flex items-baseline gap-2">
          <span className={`font-display text-sm font-semibold ${meta.color}`}>{meta.label}</span>
          <span className="text-[11px] text-ink-3 font-mono">{meta.lead}</span>
        </div>
        <span className="text-[11px] text-ink-3 tabular-nums">
          기여도 합 {totalShare.toFixed(1)}%
        </span>
      </div>
      <p className="text-[11px] text-ink-3 mb-2">{meta.desc}</p>

      {signals.length === 0 && (
        <div className="text-[11px] text-ink-3/70 italic">이 시간 지평의 누적 신호 없음</div>
      )}

      {signals.length > 0 && (
        <div className="space-y-1">
          {signals.map((s, i) => (
            <div key={i} className="flex items-center gap-2 text-[12px]">
              <span
                className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${
                  s.direction === "bullish"
                    ? "bg-crisis-500"
                    : s.direction === "bearish"
                      ? "bg-opportunity-500"
                      : "bg-ink-3/40"
                }`}
              />
              <span className="text-ink-1 flex-1 truncate">
                {SIGNAL_LABEL[s.signal_type] ?? s.signal_type}
              </span>
              <span className="text-ink-3 text-[11px] tabular-nums">
                {s.share_pct.toFixed(1)}%
              </span>
              <span className="text-ink-3/70 text-[10px] tabular-nums w-10 text-right">
                {s.n}건
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
