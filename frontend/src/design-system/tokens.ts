/**
 * Crude Compass design tokens — single source of truth.
 *
 * 색상은 design/index.html (시각 mockup)에서 1:1 추출.
 * 컴포넌트는 토큰만 참조 (하드코딩 hex X).
 *
 * architecture.md §5.2 와 1:1 매핑.
 */

export const tokens = {
  colors: {
    /** HEDGE — 위기 빨강 */
    crisis: {
      50: '#ffece9',
      100: '#ffd0c8',
      500: '#FF3621',
      700: '#ed2e1a',
      900: '#b81d0a',
    },
    /** OPPORTUNITY — 약세 초록 */
    opportunity: {
      50: '#E1F4EB',
      100: '#C8E8DA',
      500: '#0E8F5E',
      700: '#0a7a4e',
      900: '#06724a',
    },
    base: {
      ink: '#1B3139',
      ink2: '#4A5C63',
      ink3: '#7A8A91',
      ink4: '#A9B4B9',
      paper: '#FCFCFB',
      panel: '#FFFFFF',
    },
    line: {
      1: '#ECECE8',
      2: '#E2E2DD',
    },
    accent: {
      warn: '#F59E0B',
      ok: '#10B981',
      info: '#0EA5E9',
    },
    /** 사이드바 잉크 계열 (design/sidebar.jsx) */
    sidebar: {
      bg: '#1B3139',
      bg2: '#243f48',
      bg3: '#2f535e',
      muted: '#7a8a91',
      muted2: '#5a6c73',
    },
  },
  font: {
    display: "'Space Grotesk', 'IBM Plex Sans KR', sans-serif",
    body: "'IBM Plex Sans', 'IBM Plex Sans KR', system-ui, sans-serif",
    mono: "'JetBrains Mono', ui-monospace, monospace",
  },
  radius: {
    sm: '6px',
    md: '8px',
    lg: '10px',
    xl: '12px',
    '2xl': '14px',
    full: '9999px',
  },
  /** Mission status → pill color mapping */
  statusColor: {
    proposed: 'crisis',
    active: 'crisis',
    on_track: 'ok',
    at_risk: 'warn',
    paused: 'ink3',
    pivoted: 'opportunity',
    aborted: 'ink3',
    completed: 'ok',
  },
} as const;

export type Tokens = typeof tokens;
