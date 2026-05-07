// Sidebar — design/src/sidebar.jsx 포팅 + memory 결정 cut 반영:
//  - K-Petroleum 브랜딩 (GS칼텍스 X)
//  - 검색 ⌘K 제거
//  - 데이터 소스 5 → 3개 + ECOS "30m" → "종가"
//  - D+18 mini card 제거 (Mission 헤더 중복)
//  - kbd 1/2/3 유지 + react-router 바인딩

import { useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { I } from '@/components/icons'

const NAV = [
  { id: 'discovery', to: '/discovery', label: '오늘의 발견', icon: I.Compass, badge: 3, kbd: '1' },
  { id: 'mission',   to: '/mission',   label: '진행 중 미션', icon: I.Target,  badge: null, kbd: '2' },
  { id: 'yesterday', to: '/yesterday', label: '어제 복기',    icon: I.Replay,  badge: null, kbd: '3' },
] as const

const DATA_SOURCES = [
  ['AIS WebSocket', '실시간'],
  ['OilPriceAPI',   '5분'],
  ['Lakebase',      '실시간'],
] as const

export default function Sidebar() {
  const navigate = useNavigate()

  // keyboard shortcut 1/2/3 (design 패턴 보존)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) return
      const item = NAV.find((n) => n.kbd === e.key)
      if (item) navigate(item.to)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [navigate])

  return (
    <aside
      style={{
        width: 232,
        background: 'var(--green)',
        color: '#fff',
        display: 'flex',
        flexDirection: 'column',
        padding: '20px 16px',
        flexShrink: 0,
        position: 'sticky',
        top: 0,
        height: '100vh',
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 8px 18px' }}>
        <I.Logo size={20} />
        <div>
          <div className="display" style={{ fontWeight: 600, fontSize: 14.5, letterSpacing: '-.01em' }}>
            K-Petroleum
          </div>
          <div className="mono" style={{ fontSize: 9.5, color: '#5a6c73', letterSpacing: '.1em', marginTop: 1 }}>
            의사결정 지원 · v0.4
          </div>
        </div>
      </div>

      {/* Org indicator (switcher 동작 X — narrative 일관성용 표기) */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 10px',
          marginBottom: 18,
          background: 'rgba(255,255,255,.04)',
          border: '1px solid rgba(255,255,255,.08)',
          borderRadius: 6,
          fontSize: 12,
          fontWeight: 500,
        }}
      >
        <div
          style={{
            width: 18,
            height: 18,
            background: '#FF3621',
            borderRadius: 3,
            display: 'grid',
            placeItems: 'center',
            fontSize: 10,
            fontWeight: 700,
          }}
        >
          KP
        </div>
        <div style={{ flex: 1 }}>
          <div>K-Petroleum</div>
          <div className="mono" style={{ fontSize: 9.5, color: '#7a8a91' }}>여수 정유 #2</div>
        </div>
      </div>

      {/* Nav */}
      <div className="label-mini" style={{ color: '#5a6c73', padding: '0 8px 8px' }}>워크스페이스</div>
      <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {NAV.map(({ id, to, label, icon: Ic, badge, kbd }) => (
          <NavLink
            key={id}
            to={to}
            className={({ isActive }) => 'nav-item ' + (isActive ? 'active' : '')}
          >
            {({ isActive }) => (
              <>
                <Ic size={15} stroke={isActive ? '#FF3621' : 'currentColor'} sw={1.7} />
                <span>{label}</span>
                {badge != null ? (
                  <span
                    className="mono"
                    style={{
                      marginLeft: 'auto',
                      background: isActive ? '#FF3621' : 'rgba(255,255,255,.06)',
                      color: isActive ? '#fff' : '#A9B4B9',
                      padding: '1px 6px',
                      borderRadius: 999,
                      fontSize: 10,
                    }}
                  >
                    {badge}
                  </span>
                ) : (
                  <kbd>{kbd}</kbd>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Data sources (3종, ECOS 종가 포함) */}
      <div className="label-mini" style={{ color: '#5a6c73', padding: '20px 8px 8px' }}>데이터 소스</div>
      <div style={{ padding: '0 8px', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {DATA_SOURCES.map(([n, s]) => (
          <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11.5, color: '#A9B4B9' }}>
            <span
              className={'dot ' + (s === '실시간' ? 'blink' : '')}
              style={{ background: s === '실시간' ? '#10B981' : '#7A8A91' }}
            />
            <span style={{ flex: 1 }}>{n}</span>
            <span className="mono" style={{ fontSize: 9.5, color: '#5a6c73' }}>{s}</span>
          </div>
        ))}
      </div>

      <div style={{ flex: 1 }} />

      {/* User */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '8px 4px',
          borderTop: '1px solid #2f535e',
        }}
      >
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 999,
            background: 'linear-gradient(135deg,#FF3621,#1B3139)',
            display: 'grid',
            placeItems: 'center',
            fontWeight: 600,
            fontSize: 11,
          }}
        >
          김
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 500 }}>김지훈</div>
          <div style={{ fontSize: 10.5, color: '#7a8a91' }}>구매 시니어 매니저</div>
        </div>
        <I.Bell size={14} stroke="#7a8a91" />
      </div>
    </aside>
  )
}
