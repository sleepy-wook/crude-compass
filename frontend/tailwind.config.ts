import type { Config } from 'tailwindcss';
import { tokens } from './src/design-system/tokens';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        crisis: tokens.colors.crisis,
        opportunity: tokens.colors.opportunity,
        ink: {
          DEFAULT: tokens.colors.base.ink,
          1: tokens.colors.base.ink,  // alias for `ink-1` (darkest) — line, etc 패턴 일치
          2: tokens.colors.base.ink2,
          3: tokens.colors.base.ink3,
          4: tokens.colors.base.ink4,
        },
        paper: tokens.colors.base.paper,
        panel: tokens.colors.base.panel,
        line: tokens.colors.line,
        warn: tokens.colors.accent.warn,
        ok: tokens.colors.accent.ok,
        info: tokens.colors.accent.info,
        sidebar: tokens.colors.sidebar,
      },
      fontFamily: {
        display: ['Space Grotesk', 'IBM Plex Sans KR', 'sans-serif'],
        body: ['IBM Plex Sans', 'IBM Plex Sans KR', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        sm: tokens.radius.sm,
        md: tokens.radius.md,
        lg: tokens.radius.lg,
        xl: tokens.radius.xl,
        '2xl': tokens.radius['2xl'],
      },
    },
  },
  plugins: [],
} satisfies Config;
