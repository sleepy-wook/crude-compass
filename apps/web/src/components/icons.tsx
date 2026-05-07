// Lucide-style stroke icons — design/src/icons.jsx 1:1 TypeScript port

import type { CSSProperties, ReactNode } from 'react'

interface IconProps {
  size?: number
  stroke?: string
  fill?: string
  sw?: number
  vb?: number
  style?: CSSProperties
  children?: ReactNode
}

const Svg = ({
  size = 16,
  stroke = 'currentColor',
  fill = 'none',
  sw = 1.6,
  vb = 24,
  style,
  children,
}: IconProps) => (
  <svg
    width={size}
    height={size}
    viewBox={`0 0 ${vb} ${vb}`}
    fill={fill}
    stroke={stroke}
    strokeWidth={sw}
    strokeLinecap="round"
    strokeLinejoin="round"
    style={style}
  >
    {children}
  </svg>
)

export const I = {
  Logo: ({ size = 20 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="2" y="2" width="9" height="9" rx="1.5" fill="#FF3621" />
      <rect x="13" y="2" width="9" height="9" rx="1.5" fill="#1B3139" />
      <rect x="2" y="13" width="9" height="9" rx="1.5" fill="#1B3139" />
      <rect x="13" y="13" width="9" height="9" rx="1.5" fill="#FF3621" opacity=".7" />
    </svg>
  ),
  Compass: (p: IconProps) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="M15.5 8.5l-2 5-5 2 2-5z" />
    </Svg>
  ),
  Target: (p: IconProps) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" />
    </Svg>
  ),
  Replay: (p: IconProps) => (
    <Svg {...p}>
      <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
      <path d="M3 3v5h5" />
    </Svg>
  ),
  Flask: (p: IconProps) => (
    <Svg {...p}>
      <path d="M9 3h6M10 3v6L4 19a2 2 0 0 0 1.7 3h12.6A2 2 0 0 0 20 19l-6-10V3" />
      <path d="M7 14h10" />
    </Svg>
  ),
  Search: (p: IconProps) => (
    <Svg {...p}>
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-3.5-3.5" />
    </Svg>
  ),
  Bell: (p: IconProps) => (
    <Svg {...p}>
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9z" />
      <path d="M10 21a2 2 0 0 0 4 0" />
    </Svg>
  ),
  Bolt: (p: IconProps) => (
    <Svg {...p} fill="currentColor" stroke="none">
      <path d="M13 2L4 14h7l-1 8 9-12h-7z" />
    </Svg>
  ),
  User: (p: IconProps) => (
    <Svg {...p}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </Svg>
  ),
  Ship: (p: IconProps) => (
    <Svg {...p}>
      <path d="M3 17a4 4 0 0 0 4-2 4 4 0 0 0 4 2 4 4 0 0 0 4-2 4 4 0 0 0 4 2" />
      <path d="M5 14l1-5h12l1 5" />
      <path d="M12 4v5" />
    </Svg>
  ),
  ArrowUp: (p: IconProps) => (
    <Svg {...p}>
      <path d="M12 19V5M5 12l7-7 7 7" />
    </Svg>
  ),
  ArrowDown: (p: IconProps) => (
    <Svg {...p}>
      <path d="M12 5v14M19 12l-7 7-7-7" />
    </Svg>
  ),
  ArrowRight: (p: IconProps) => (
    <Svg {...p}>
      <path d="M5 12h14M13 5l7 7-7 7" />
    </Svg>
  ),
  Globe: (p: IconProps) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3a13 13 0 0 1 0 18M12 3a13 13 0 0 0 0 18" />
    </Svg>
  ),
  Doc: (p: IconProps) => (
    <Svg {...p}>
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
      <path d="M14 3v6h6M8 13h8M8 17h5" />
    </Svg>
  ),
  Clock: (p: IconProps) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </Svg>
  ),
  Check: (p: IconProps) => (
    <Svg {...p}>
      <path d="M5 13l4 4L19 7" />
    </Svg>
  ),
  X: (p: IconProps) => (
    <Svg {...p}>
      <path d="M6 6l12 12M6 18L18 6" />
    </Svg>
  ),
  Spark: (p: IconProps) => (
    <Svg {...p}>
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8" />
    </Svg>
  ),
  Filter: (p: IconProps) => (
    <Svg {...p}>
      <path d="M3 5h18M6 12h12M10 19h4" />
    </Svg>
  ),
  Brain: (p: IconProps) => (
    <Svg {...p}>
      <path d="M9 3a3 3 0 0 0-3 3v0a3 3 0 0 0-3 3 3 3 0 0 0 1.5 2.6A3 3 0 0 0 6 18a3 3 0 0 0 6 0V3a3 3 0 0 0-3 0z" />
      <path d="M15 3a3 3 0 0 1 3 3v0a3 3 0 0 1 3 3 3 3 0 0 1-1.5 2.6A3 3 0 0 1 18 18a3 3 0 0 1-6 0" />
    </Svg>
  ),
  TrendUp: (p: IconProps) => (
    <Svg {...p}>
      <path d="M3 17l6-6 4 4 8-8" />
      <path d="M14 7h7v7" />
    </Svg>
  ),
  TrendDown: (p: IconProps) => (
    <Svg {...p}>
      <path d="M3 7l6 6 4-4 8 8" />
      <path d="M14 17h7v-7" />
    </Svg>
  ),
  Send: (p: IconProps) => (
    <Svg {...p}>
      <path d="M3 11l18-8-8 18-2-8z" />
    </Svg>
  ),
  Layers: (p: IconProps) => (
    <Svg {...p}>
      <path d="M12 2l10 5-10 5L2 7z" />
      <path d="M2 12l10 5 10-5M2 17l10 5 10-5" />
    </Svg>
  ),
  Eye: (p: IconProps) => (
    <Svg {...p}>
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
    </Svg>
  ),
}
