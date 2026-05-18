/**
 * OpenDataBadge — Track 1 Social Impact narrative.
 *
 * 시나리오 §3 Open Data Democratization:
 *   Bloomberg / Platts / Vortexa / Kpler 유료 → Crude Compass 6 source 무료
 *   = 중소 정유사 / 연구자 / 정부 분석관도 같은 인텔리전스
 *
 * 시나리오 §6.5.1 6 source 구성:
 *   Backtest 4 (GDELT/EIA/OPEC/FX) + Ground truth (OPINET) + Reactive (OilPriceAPI)
 */
import { useBacktestResults } from "../lib/queries";

const SOURCES = [
  { name: "GDELT", role: "글로벌 뉴스 mention", freq: "15분", category: "leading" },
  { name: "OPEC MOMR", role: "산유국 공급 보고서", freq: "월간", category: "macro" },
  { name: "EIA", role: "미국 주간 재고", freq: "주간", category: "fundamentals" },
  { name: "한국은행 ECOS", role: "USD/KRW 환율", freq: "일간", category: "macro" },
  { name: "OPINET KNOC", role: "두바이/Brent/WTI 종가", freq: "일간", category: "fundamentals" },
  { name: "OilPriceAPI", role: "실시간 spike 감지", freq: "5분", category: "reactive" },
];

export function OpenDataBadge() {
  const backtest = useBacktestResults();
  const summary = backtest.data?.summary;
  const hitRate = summary?.hit_rate_pct;
  const nActive = summary?.n_active;

  return (
    <section className="bg-gradient-to-br from-paper to-line-1/40 border border-line-1 rounded-xl p-6">
      <div className="flex items-baseline justify-between mb-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-ink-3 mb-1">
            Track 1 · Open Data Democratization
          </div>
          <h3 className="font-display text-base font-semibold text-ink-1">
            유료 인텔리전스를 무료로
          </h3>
        </div>
      </div>

      <p className="text-[12px] text-ink-2 leading-relaxed mb-5">
        Bloomberg · Platts · Vortexa · Kpler 같은 유료 시스템 없이도 동일한
        의사결정 인텔리전스. 정유 빅5만 가지던 기술을 중소 정유사 · 연구자 ·
        정부 분석관에게.
      </p>

      {/* Backtest hit rate */}
      {hitRate !== null && hitRate !== undefined && (
        <div className="grid grid-cols-3 gap-4 mb-5 pb-5 border-b border-line-1">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">
              백테스트 적중률
            </div>
            <div className="font-display text-2xl font-semibold text-opportunity-700 tabular-nums">
              {hitRate.toFixed(1)}%
            </div>
            <div className="text-[10px] text-ink-3 mt-1">
              7년 검증 {nActive ?? "—"}건
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">
              평균 비용 절감
            </div>
            <div className="font-display text-2xl font-semibold text-opportunity-700 tabular-nums">
              {summary?.avg_save_pct?.toFixed(2) ?? "—"}%
            </div>
            <div className="text-[10px] text-ink-3 mt-1">
              30일 vs 평시 비중
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">
              데이터 비용
            </div>
            <div className="font-display text-2xl font-semibold text-ink-1 tabular-nums">
              0원
            </div>
            <div className="text-[10px] text-ink-3 mt-1">
              vs 유료 연 수천만원
            </div>
          </div>
        </div>
      )}

      {/* 6 source list */}
      <div>
        <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-2.5">
          공개 데이터 6 source
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-[12px]">
          {SOURCES.map((s) => (
            <div key={s.name} className="flex items-baseline gap-2">
              <span className="font-medium text-ink-1">{s.name}</span>
              <span className="text-ink-3 truncate flex-1">{s.role}</span>
              <span className="text-[10px] text-ink-3 font-mono tabular-nums shrink-0">
                {s.freq}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
