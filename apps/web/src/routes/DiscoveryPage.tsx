// Discovery Feed — 오늘의 의사결정 카드 3장 default + 더 보기 2건 접힘
// Phase 3에서 RiskScoreSummary + DiscoveryCard + CardC1~C5 본격 구현. 현재는 골격만.

export default function DiscoveryPage() {
  return (
    <div style={{ padding: '0 40px 60px', maxWidth: 1100, margin: '0 auto' }}>
      <header style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', padding: '28px 0 18px' }}>
        <div>
          <div className="label-mini" style={{ color: 'var(--ink-3)' }}>오늘의 발견 · Discovery</div>
          <h1 className="display" style={{ fontSize: 26, fontWeight: 600, margin: '4px 0 4px', letterSpacing: '-.02em' }}>
            오늘의 의사결정 카드
            <span style={{ color: 'var(--ink-3)', fontWeight: 400 }}> · 5월 8일 금요일</span>
          </h1>
          <div style={{ fontSize: 13, color: 'var(--ink-2)' }}>
            3건 · 예상 소요 <span className="mono">16분</span>
          </div>
        </div>
      </header>

      <div className="hl" style={{ background: '#fff', borderRadius: 8, padding: 24 }}>
        <div className="label-mini">Phase 0 골격 — Discovery 카드 본구현은 Phase 3 (5/15~)</div>
      </div>
    </div>
  )
}
