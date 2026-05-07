// Living Mission — 28일 timeline + 인라인 Genie 시뮬 (Wow 3)
// Phase 3에서 본 구현.

export default function MissionPage() {
  return (
    <div style={{ padding: '0 40px 60px', maxWidth: 1280, margin: '0 auto' }}>
      <header style={{ padding: '28px 0 18px' }}>
        <div className="label-mini" style={{ color: 'var(--ink-3)' }}>진행 중 미션 · Living Mission</div>
        <h1 className="display" style={{ fontSize: 26, fontWeight: 600, margin: '4px 0 4px', letterSpacing: '-.02em' }}>
          Term 50% → 70% <span style={{ color: 'var(--ink-3)', fontWeight: 400 }}>· Hormuz 봉쇄 헤지</span>
        </h1>
      </header>

      <div className="hl" style={{ background: '#fff', borderRadius: 8, padding: 24 }}>
        <div className="label-mini">Phase 0 골격 — Mission timeline + 인라인 Genie 본구현 Phase 3</div>
      </div>
    </div>
  )
}
