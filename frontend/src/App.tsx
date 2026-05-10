/**
 * Sprint 1 placeholder — design token 검증 + Tailwind 작동 확인.
 * 실제 3 페이지 (Discovery / Mission / What-If) 구현은 Sprint 4.
 */
function App() {
  return (
    <div className="min-h-screen bg-paper text-ink p-10 font-body">
      <header className="mb-8">
        <div className="text-xs uppercase tracking-widest text-ink-3">
          Crude Compass · Sprint 1 Skeleton
        </div>
        <h1 className="font-display text-4xl font-semibold tracking-tight mt-2">
          Pre-emptive Bidirectional Decision Support
        </h1>
      </header>

      <section className="grid grid-cols-2 gap-4 max-w-4xl">
        <div className="border border-line-1 rounded-lg p-6 bg-panel">
          <div className="text-xs uppercase tracking-widest text-ink-3 mb-2">HEDGE Mission</div>
          <div className="font-display text-3xl font-semibold text-crisis-500">82</div>
          <div className="text-xs text-ink-3 mt-2 font-mono">Pattern Score · crisis 토큰</div>
        </div>
        <div className="border border-line-1 rounded-lg p-6 bg-panel">
          <div className="text-xs uppercase tracking-widest text-ink-3 mb-2">OPPORTUNITY</div>
          <div className="font-display text-3xl font-semibold text-opportunity-500">22</div>
          <div className="text-xs text-ink-3 mt-2 font-mono">Pattern Score · opportunity 토큰</div>
        </div>
      </section>

      <footer className="mt-12 text-xs text-ink-4 font-mono">
        Tailwind 3 + Vite + React 19 + design-system tokens loaded.
      </footer>
    </div>
  );
}

export default App;
