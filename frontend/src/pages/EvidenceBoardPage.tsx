/**
 * EvidenceBoardPage — /evidence
 *
 * D-2 사용자 요청: OPEC 월간 보고서 + 주요 보도를 게시판처럼 보는 sub-page.
 * Market Watch 메인은 latest 단건씩만, 자세한 history는 여기서.
 *
 * 현재 D-2 scope:
 * - OPEC: latest 1건 + 외부 link (과거 PDF는 OPEC 공식 사이트)
 * - 주요 보도: limit 20 (메인 5건 → 여기 20건)
 *
 * P1 (시간 남으면):
 * - backend `/api/market/opec-history?months=6` 추가 → 과거 OPEC dropdown
 * - 뉴스 필터 (direction / category / 기간)
 */
import { Link } from "react-router-dom";
import { OpecCitation } from "../components/OpecCitation";
import { NewsTopList } from "../components/NewsTopList";

export function EvidenceBoardPage() {
  return (
    <div className="max-w-6xl mx-auto px-8 py-10">
      <header className="mb-8">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-1.5">Evidence Board</div>
        <h1 className="font-display text-[28px] md:text-[32px] font-semibold tracking-tight text-ink-1 leading-tight">
          OPEC 보고서 · 주요 보도 게시판
        </h1>
        <p className="text-[13px] text-ink-3 mt-2 leading-relaxed">
          Knowledge Assistant가 참조하는 문서 근거 + GDELT 키워드 burst 누적.
          Market Watch에서 latest snapshot 본 후 여기서 자세한 history.
        </p>
        <div className="mt-3">
          <Link
            to="/market"
            className="text-[12px] text-ink-3 hover:text-ink-1"
          >
            ← Market Watch로 돌아가기
          </Link>
        </div>
      </header>

      {/* OPEC 섹션 — 현재는 latest 1건 + OPEC 공식 link */}
      <section className="mb-12">
        <div className="mb-4 pb-3 border-b border-line-1">
          <h2 className="font-display text-xl font-semibold text-ink-1 tracking-tight">
            OPEC Monthly Oil Market Report
          </h2>
          <p className="text-xs text-ink-3 mt-0.5">
            Knowledge Assistant (crude-compass-ka)가 OPEC MOMR PDF (2019~2026)를 검색한 결과의 latest snapshot.
            과거 보고서는 OPEC 공식 사이트에서 직접 다운로드.
          </p>
        </div>
        <OpecCitation />
      </section>

      {/* 주요 보도 섹션 — limit 20 (메인 Market Watch보다 많이) */}
      <section className="mb-12">
        <div className="mb-4 pb-3 border-b border-line-1">
          <h2 className="font-display text-xl font-semibold text-ink-1 tracking-tight">
            주요 보도 — GDELT 키워드 burst
          </h2>
          <p className="text-xs text-ink-3 mt-0.5">
            최근 7일 importance ≥ 60. GDELT 15분 cron 누적. Supervisor가 leading 시그널로 참조.
          </p>
        </div>
        <NewsTopList limit={20} />
      </section>

      <div className="h-20" />
    </div>
  );
}
