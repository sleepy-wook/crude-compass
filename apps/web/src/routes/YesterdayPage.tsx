// Yesterday Review — Genie "다시 묻기" + Self-critique + AI/BI Dashboard iframe
// Phase 3에서 본 구현 (AI/BI iframe은 Phase 4 deploy 시 token endpoint 연결).

export default function YesterdayPage() {
  return (
    <div style={{ padding: '0 40px 60px', maxWidth: 1280, margin: '0 auto' }}>
      <header style={{ padding: '28px 0 18px' }}>
        <div className="label-mini" style={{ color: 'var(--ink-3)' }}>어제 복기 · Yesterday Review</div>
        <h1 className="display" style={{ fontSize: 26, fontWeight: 600, margin: '4px 0 0', letterSpacing: '-.02em' }}>
          어제 결정을 복기합니다
        </h1>
      </header>

      <div className="hl" style={{ background: '#fff', borderRadius: 8, padding: 24 }}>
        <div className="label-mini">Phase 0 골격 — Genie bar + Self-critique + AI/BI Dashboard iframe Phase 3·4</div>
      </div>
    </div>
  )
}
