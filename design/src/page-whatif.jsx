function PageWhatIf() {
  const [tab, setTab] = React.useState("whatif");
  return (
    <div style={{ padding: "0 40px 60px", maxWidth: 1280, margin: "0 auto" }}>
      <header style={{ padding: "28px 0 12px" }}>
        <div className="label-mini" style={{ color: "var(--ink-3)" }}>시뮬레이션 & 회고 · What-If</div>
        <h1 className="display" style={{ fontSize: 26, fontWeight: 600, margin: "4px 0 0", letterSpacing: "-.02em" }}>
          미래를 시뮬레이션하고, 어제를 복기합니다
        </h1>
      </header>

      <div style={{ borderBottom: "1px solid var(--line)", display: "flex", gap: 4, marginBottom: 22 }}>
        <button className={"tab " + (tab === "whatif" ? "active" : "")} onClick={() => setTab("whatif")}>
          <I.Flask size={13} stroke={tab === "whatif" ? "#FF3621" : "currentColor"}/> What-If 시뮬레이션
        </button>
        <button className={"tab " + (tab === "yesterday" ? "active" : "")} onClick={() => setTab("yesterday")}>
          <I.Replay size={13} stroke={tab === "yesterday" ? "#FF3621" : "currentColor"}/> 어제 복기
          <span className="pill pill-neutral mono" style={{ marginLeft: 6 }}>AI/BI</span>
        </button>
      </div>

      {tab === "whatif" ? <WhatIfTab/> : <YesterdayTab/>}
    </div>
  );
}

/* ---------- What-If tab ---------- */

function WhatIfTab() {
  const examples = [
    "Brent $140·Dubai $135 가면 우리 portfolio impact?",
    "If Hormuz reopens in 7 days, how does Term 70 vs 60 compare?",
    "Aramco OSP +$3.0/bbl 시나리오에서 4월 인도가는?",
  ];
  const [query, setQuery] = React.useState("");
  const [running, setRunning] = React.useState(false);
  const [result, setResult] = React.useState(null);

  const run = (q) => {
    const text = q || query || examples[0];
    setQuery(text);
    setRunning(true);
    setResult(null);
    setTimeout(() => { setRunning(false); setResult(text); }, 1500);
  };

  return (
    <div>
      {/* Genie input */}
      <div className="hl" style={{
        background: "#fff", borderRadius: 10, padding: 18,
        boxShadow: running || result ? "0 0 0 1px rgba(255,54,33,.15)" : "none",
        transition: "box-shadow .25s"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <I.Spark size={14} stroke="#FF3621"/>
          <span className="label-mini" style={{ color: "var(--ink-3)" }}>Genie · 자연어 질의</span>
          <span className="pill pill-neutral mono" style={{ marginLeft: 6 }}>LAKEBASE + GOLD</span>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "stretch" }}>
          <textarea
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="예: Brent $140·Dubai $135 가면 우리 portfolio impact?"
            rows={2}
            style={{
              flex: 1, resize: "none", border: "1px solid var(--line-2)", borderRadius: 6,
              padding: "12px 14px", fontFamily: "inherit", fontSize: 14, color: "var(--ink)",
              outline: "none"
            }}
          />
          <button className="btn btn-primary" style={{ height: "auto", padding: "0 18px" }} onClick={() => run()}>
            {running ? <>실행 중…</> : <>시뮬레이션 <I.Send size={13}/></>}
          </button>
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
          <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", padding: "4px 0" }}>추천 질문</span>
          {examples.map(ex => (
            <button key={ex} className="hl" style={{
              background: "#FCFCFB", padding: "4px 10px", borderRadius: 99,
              fontSize: 11.5, color: "var(--ink-2)"
            }} onClick={() => run(ex)}>{ex}</button>
          ))}
        </div>
      </div>

      {/* Result area */}
      <div style={{ marginTop: 18 }}>
        {!running && !result && (
          <div className="hl" style={{
            background: "#FCFCFB", borderRadius: 10, padding: 60, textAlign: "center",
            borderStyle: "dashed", color: "var(--ink-3)"
          }}>
            <I.Flask size={28} stroke="#A9B4B9"/>
            <div style={{ marginTop: 10, fontSize: 13 }}>질문을 입력하면 포트폴리오 시나리오를 실행합니다.</div>
            <div className="mono" style={{ marginTop: 4, fontSize: 11, color: "var(--ink-4)" }}>
              평균 응답 5.2초 · 최근 30일 Lakebase 스냅샷 사용
            </div>
          </div>
        )}

        {running && (
          <div className="hl" style={{ background: "#fff", borderRadius: 10, padding: 28 }}>
            <div className="mono" style={{ fontSize: 11, color: "var(--ink-3)", marginBottom: 16 }}>시뮬레이션 실행 중…</div>
            {[
              "의도 파싱 · 3개 엔티티 해석 (Brent, Dubai, portfolio)",
              "Lakebase 스냅샷 로드 · 30일 가격, 18일 포지션",
              "Gold 테이블 조인 · cargo, frame_contracts, refining_margins",
              "Monte Carlo 1,000회 반복 실행 중…",
              "결과 차트 렌더링…"
            ].map((step, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 10, padding: "6px 0",
                fontSize: 12, color: "var(--ink-2)",
                opacity: 0, animation: `fadeup .4s ${i * 0.12}s forwards`
              }}>
                <span className="dot blink" style={{ background: i < 3 ? "#10B981" : "#F59E0B" }}/>
                <span className="mono">{String(i + 1).padStart(2, "0")}</span>
                <span>{step}</span>
              </div>
            ))}
          </div>
        )}

        {result && <WhatIfResult query={result}/>}
      </div>
    </div>
  );
}

function WhatIfResult({ query }) {
  return (
    <div className="stagger" style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 18 }}>
      {/* ROI scenario chart */}
      <div className="hl" style={{ background: "#fff", borderRadius: 10, padding: 22 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div>
            <div className="label-mini" style={{ color: "var(--ink-3)" }}>결과 · 포트폴리오 P&L · 4주 예측</div>
            <div className="display" style={{ fontSize: 17, fontWeight: 500, marginTop: 2 }}>
              Brent $140 / Dubai $135 시나리오 · 현재 65:35 vs 권고 70:30
            </div>
          </div>
          <div style={{ display: "flex", gap: 14, fontSize: 11.5 }}>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}><span className="dot" style={{ background: "#1B3139" }}/> 현재 65:35</span>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}><span className="dot" style={{ background: "#FF3621" }}/> 권고 70:30</span>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}><span className="dot" style={{ background: "#A9B4B9" }}/> 무대응</span>
          </div>
        </div>
        <LineChart
          width={620} height={260}
          xLabels={["W1","W2","W3","W4"]}
          series={[
            { color: "#A9B4B9", data: [120, 150, 145, 130, 110, 95, 80, 60, 40, 20, 5, -10], dash: "4 3" },
            { color: "#1B3139", data: [120, 165, 195, 230, 245, 260, 270, 280, 285, 290, 290, 285], width: 2 },
            { color: "#FF3621", data: [120, 175, 220, 265, 300, 320, 335, 345, 350, 355, 355, 350], width: 2.2 },
          ]}
        />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14, marginTop: 14 }}>
          <SummaryStat label="무대응" sub="기준선" v="−₩10억" tone="bad"/>
          <SummaryStat label="현재 65:35" sub="무대응 대비" v="+₩285억" tone="ok"/>
          <SummaryStat label="권고 70:30" sub="무대응 대비" v="+₩355억" tone="best"/>
        </div>
      </div>

      {/* Sensitivity table + attribution */}
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div className="hl" style={{ background: "#fff", borderRadius: 10, padding: 18 }}>
          <div className="label-mini" style={{ color: "var(--ink-3)", marginBottom: 10 }}>민감도 분석 · Term 70:30 결과 (₩억)</div>
          <SensitivityTable/>
        </div>
        <div className="hl" style={{ background: "var(--green)", color: "#fff", borderRadius: 10, padding: 16 }}>
          <div className="mono" style={{ fontSize: 10, color: "#7a8a91", letterSpacing: ".1em", marginBottom: 8 }}>AI 출처</div>
          <div style={{ fontSize: 12.5, lineHeight: 1.55, color: "#A9B4B9" }}>
            Lakebase 스냅샷 <span className="mono" style={{ color: "#fff" }}>2026-05-07T09:42</span> 사용,
            <span className="mono" style={{ color: "#fff" }}> portfolio_positions</span>, <span className="mono" style={{ color: "#fff" }}>frame_contracts</span>,
            <span className="mono" style={{ color: "#fff" }}> price_curves_gold</span> 조인. Monte Carlo 1,000회.
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <span className="pill pill-dark" style={{ background: "#2f535e", color: "#fff" }}>소스 3개</span>
            <span className="pill pill-dark" style={{ background: "#2f535e", color: "#fff" }}>5.2s</span>
            <span className="pill pill-dark" style={{ background: "#2f535e", color: "#fff" }}>신뢰도 87%</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryStat({ label, sub, v, tone }) {
  const colors = { ok: "var(--ink)", best: "#FF3621", bad: "var(--ink-3)" };
  return (
    <div className="hl" style={{
      padding: 12, borderRadius: 6,
      background: tone === "best" ? "var(--red-soft)" : "#FCFCFB",
      borderColor: tone === "best" ? "#FF3621" : undefined
    }}>
      <div className="label-mini" style={{ color: tone === "best" ? "#FF3621" : "var(--ink-3)" }}>{label}</div>
      <div className="display mono" style={{ fontSize: 22, fontWeight: 600, color: colors[tone], marginTop: 4 }}>{v}</div>
      <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginTop: 2 }}>{sub}</div>
    </div>
  );
}

function SensitivityTable() {
  const cols = ["$120", "$130", "$140", "$150"];
  const rows = [
    ["$110", [120, 180, 220, 240]],
    ["$120", [180, 240, 290, 320]],
    ["$130", [220, 290, 355, 390]],
    ["$140", [240, 320, 390, 430]],
  ];
  const max = 430;
  return (
    <table className="mono" style={{ width: "100%", borderCollapse: "collapse", fontSize: 11.5 }}>
      <thead>
        <tr>
          <th style={{ textAlign: "left", padding: "6px 8px", color: "var(--ink-3)", fontWeight: 500 }}>Brent ↓ / Dubai →</th>
          {cols.map(c => <th key={c} style={{ padding: "6px 8px", color: "var(--ink-3)", fontWeight: 500 }}>{c}</th>)}
        </tr>
      </thead>
      <tbody>
        {rows.map(([b, vals]) => (
          <tr key={b}>
            <td style={{ padding: "6px 8px", color: "var(--ink-2)" }}>{b}</td>
            {vals.map((v, i) => {
              const intensity = v / max;
              return (
                <td key={i} style={{
                  padding: "6px 8px", textAlign: "center", fontWeight: 600,
                  background: `rgba(255,54,33,${intensity * 0.3})`,
                  color: intensity > 0.7 ? "#b81d0a" : "var(--ink)"
                }}>+{v}</td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/* ---------- Yesterday tab ---------- */

function YesterdayTab() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {/* Bidirectional backtest banner */}
      <div className="hl" style={{ background: "#fff", borderRadius: 10, padding: 22 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <div>
            <div className="label-mini" style={{ color: "var(--ink-3)" }}>Self-Critique · 양방향 backtest · 최근 90일</div>
            <div className="display" style={{ fontSize: 17, fontWeight: 500, marginTop: 2 }}>
              Bidirectional Pattern Detection 정확도
              <span style={{ color: "var(--ink-3)", fontWeight: 400, marginLeft: 8, fontSize: 13 }}>HEDGE + OPPORTUNITY 공통 architecture</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <span className="pill pill-neutral mono">90d window</span>
            <span className="pill pill-neutral mono">MLflow run #142</span>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 14 }}>
          <div className="hl" style={{ padding: 14, borderRadius: 6, background: "var(--red-soft)", borderColor: "#FF3621" }}>
            <div className="label-mini" style={{ color: "#FF3621" }}>HEDGE 정확도</div>
            <div className="display mono" style={{ fontSize: 28, fontWeight: 600, color: "#FF3621", marginTop: 4 }}>78<span style={{ fontSize: 14 }}>%</span></div>
            <div className="mono" style={{ fontSize: 10.5, color: "#b81d0a", marginTop: 2 }}>9/12 신호 적중 · 위기 1–2회/년</div>
          </div>
          <div className="hl" style={{ padding: 14, borderRadius: 6, background: "var(--opp-soft)", borderColor: "var(--opp)" }}>
            <div className="label-mini" style={{ color: "#0E8F5E" }}>OPPORTUNITY 정확도</div>
            <div className="display mono" style={{ fontSize: 28, fontWeight: 600, color: "#0E8F5E", marginTop: 4 }}>71<span style={{ fontSize: 14 }}>%</span></div>
            <div className="mono" style={{ fontSize: 10.5, color: "#06724a", marginTop: 2 }}>10/14 신호 적중 · 기회 분기 1–2회</div>
          </div>
          <div className="hl" style={{ padding: 14, borderRadius: 6, background: "#FCFCFB" }}>
            <div className="label-mini" style={{ color: "var(--ink-3)" }}>평균 lead time</div>
            <div className="display mono" style={{ fontSize: 28, fontWeight: 600, marginTop: 4 }}>12.4<span style={{ fontSize: 14, color: "var(--ink-3)" }}>일</span></div>
            <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginTop: 2 }}>발발 전 Score 70/30 돌파</div>
          </div>
          <div className="hl" style={{ padding: 14, borderRadius: 6, background: "#FCFCFB" }}>
            <div className="label-mini" style={{ color: "var(--ink-3)" }}>Pivot 성공률</div>
            <div className="display mono" style={{ fontSize: 28, fontWeight: 600, marginTop: 4 }}>4<span style={{ fontSize: 14, color: "var(--ink-3)" }}>/5</span></div>
            <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginTop: 2 }}>양방향 반전 제안 수락률</div>
          </div>
        </div>
        <div style={{ marginTop: 14, padding: "12px 14px", background: "#FCFCFB", borderRadius: 6, border: "1px dashed var(--line-2)", display: "flex", gap: 10, alignItems: "center", fontSize: 12, color: "var(--ink-2)" }}>
          <I.Brain size={13} stroke="#FF3621"/>
          <span>
            <span style={{ fontWeight: 500 }}>Calibration:</span> importance score 가중치 재조정 · OPP threshold 30 → 32 완화 권고 (더 시그널 catch).
            <span className="mono" style={{ color: "var(--ink-3)", marginLeft: 8 }}>MLflow run #142 · next: 2026-05-12</span>
          </span>
        </div>
      </div>

      {/* Self-critique */}
      <div className="hl" style={{ background: "#fff", borderRadius: 10, padding: 22 }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 8, background: "var(--green)",
            color: "#FF3621", display: "grid", placeItems: "center", flexShrink: 0
          }}>
            <I.Brain size={18} stroke="#FF3621"/>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <span className="label-mini" style={{ color: "var(--ink-3)" }}>AI 자기 평가 · D+17 회고</span>
              <span className="pill pill-warn">결과 측정 대기 · 7일</span>
            </div>
            <div className="display" style={{ fontSize: 17, fontWeight: 500, lineHeight: 1.5, color: "var(--ink)", letterSpacing: "-.005em" }}>
              어제 매니저 결정: <span className="mono" style={{ color: "#FF3621" }}>Term +10pt</span> 추가 lock.
              AI 권고는 <span className="mono">+15pt</span>였음. 매니저가 더 보수적.
              <span style={{ color: "var(--ink-2)" }}> 7일 후 outcome 측정 예정 (May 14).</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginTop: 16 }}>
              <Critique k="매니저 결정"  v="Term +10pt"  sub="64.0% → 65.0%" tone="ink"/>
              <Critique k="AI 권고"      v="Term +15pt" sub="64.0% → 65.5%" tone="red"/>
              <Critique k="차이"         v="−5pt"        sub="더 보수적 결정" tone="ink"/>
              <Critique k="추정 기회비용" v="−₩12억"     sub="Brent ≥ $130 시" tone="red"/>
            </div>
          </div>
        </div>
      </div>

      {/* 2x2 grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
        {/* Pattern Score · bidirectional */}
        <ChartCard title="Pattern Score · 30일 (bidirectional)" sub="50 = 균형 · ≥70 HEDGE · ≤30 OPPORTUNITY">
          <div style={{ position: "relative" }}>
            {/* zone backgrounds */}
            <div style={{ position: "absolute", inset: "0 0 24px 0", display: "flex", flexDirection: "column", pointerEvents: "none", opacity: .5 }}>
              <div style={{ flex: "30 1 0", background: "linear-gradient(to bottom, #ffece9, transparent)" }}/>
              <div style={{ flex: "40 1 0" }}/>
              <div style={{ flex: "30 1 0", background: "linear-gradient(to top, #E1F4EB, transparent)" }}/>
            </div>
            <LineChart
              width={560} height={210}
              yDomain={[0, 100]}
              xLabels={["Apr 8","Apr 15","Apr 22","Apr 29","May 6"]}
              annotations={[
                { i: 7,  label: "GDACS alert" },
                { i: 14, label: "Tanker boarded" },
                { i: 22, label: "Blockade decl." },
              ]}
              series={[{
                color: "#FF3621", width: 2,
                data: [48,46,44,42,40,38,36,34,30,28,32,38,46,52,58,64,70,72,76,78,76,80,82,84,82,80,78,82,84,82]
              }]}
            />
          </div>
          <div style={{ display: "flex", gap: 14, marginTop: 6, fontSize: 11, color: "var(--ink-2)" }}>
            <span><span className="dot" style={{ background: "#0E8F5E" }}/> 4/15 OPP 신호 · score 28</span>
            <span><span className="dot" style={{ background: "#FF3621" }}/> 4/22+ HEDGE 신호 · score 70+</span>
            <span style={{ marginLeft: "auto" }} className="mono">현재 82</span>
          </div>
        </ChartCard>

        {/* Hormuz transit */}
        <ChartCard title="Hormuz 해협 통과량" sub="vessels/day · 최근 30일">
          <BarChart
            width={560} height={210}
            data={[98,102,99,101,100,97,95,96,94,90,82,70,60,52,44,38,30,24,20,18,15,12,10,9,8,7,7,6,6,7].map(v => v * 10)}
            accentIdx={29}
            xLabels={["Apr 8","Apr 15","Apr 22","Apr 29","May 6"]}
            color="#1B3139"
          />
          <div style={{ display: "flex", gap: 16, marginTop: 4, fontSize: 11, color: "var(--ink-2)" }}>
            <span>30일 합계 <span className="mono" style={{ color: "var(--ink)" }}>14,820</span></span>
            <span>오늘 <span className="mono" style={{ color: "#FF3621" }}>191</span> · 30일 평균 대비 <span className="mono">−93%</span></span>
          </div>
        </ChartCard>

        {/* WTI / Brent / Dubai */}
        <ChartCard title="WTI · Brent · Dubai · 30일" sub="Brent–Dubai 스프레드 강조">
          <LineChart
            width={560} height={210}
            yDomain={[80, 140]}
            xLabels={["Apr 8","Apr 15","Apr 22","Apr 29","May 6"]}
            series={[
              { color: "#A9B4B9", width: 1.5, data: [82,83,84,85,86,87,88,90,92,93,94,96,98,100,102,104,106,108,110,112,114,116,118,118,117,118,119,120,120,121] }, // WTI
              { color: "#1B3139", width: 2,   data: [85,86,87,88,90,91,92,94,96,98,100,102,104,107,110,114,118,122,126,128,130,132,134,134,132,130,131,132,133,134] }, // Brent
              { color: "#FF3621", width: 2,   data: [83,84,85,86,87,89,90,92,94,96,98,101,104,108,112,116,120,124,128,131,134,136,139,140,138,137,138,139,140,142] }, // Dubai
            ]}
          />
          <div style={{ display: "flex", gap: 16, marginTop: 4, fontSize: 11, color: "var(--ink-2)" }}>
            <span><span className="dot" style={{ background: "#A9B4B9" }}/> WTI <span className="mono">$121</span></span>
            <span><span className="dot" style={{ background: "#1B3139" }}/> Brent <span className="mono">$134</span></span>
            <span><span className="dot" style={{ background: "#FF3621" }}/> Dubai <span className="mono">$142</span></span>
            <span style={{ marginLeft: "auto", color: "#FF3621", fontWeight: 600 }} className="mono">B–D 스프레드 −$8.0 ▼</span>
          </div>
        </ChartCard>

        {/* Decisions outcome */}
        <ChartCard title="매니저 결정 · 결과 회고" sub="최근 7건 승인 결정">
          <div style={{ overflow: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11.5 }}>
              <thead>
                <tr>
                  {["일자","결정","7일","30일","AI 동의"].map(h => (
                    <th key={h} className="label-mini" style={{ textAlign: "left", padding: "6px 8px", color: "var(--ink-3)", borderBottom: "1px solid var(--line)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  ["4/22","Term +5pt","+₩8억","+₩22억","동의","HEDGE"],
                  ["4/25","BP 거절","+₩2억","—","동의","HEDGE"],
                  ["4/28","Spot 최저선 +0.2M","−₩4억","−₩9억","불일치","OPP"],
                  ["5/1","Term +8pt","+₩15억","—","동의","HEDGE"],
                  ["5/3","주간 플랜 승인","—","—","동의","—"],
                  ["5/5","#003 우회","+₩6억","—","동의","HEDGE"],
                  ["5/6","Term +10pt","측정중","측정중","부분","HEDGE"],
                ].map((r, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--line)" }}>
                    <td className="mono" style={{ padding: "8px 8px", color: "var(--ink-2)" }}>{r[0]}</td>
                    <td style={{ padding: "8px 8px", fontWeight: 500 }}>
                      {r[1]}
                      {r[5] !== "—" && (
                        <span className="mono" style={{ marginLeft: 6, fontSize: 9.5, padding: "1px 5px", borderRadius: 3, background: r[5] === "OPP" ? "var(--opp-soft)" : "var(--red-soft)", color: r[5] === "OPP" ? "#0E8F5E" : "#b81d0a" }}>{r[5]}</span>
                      )}
                    </td>
                    <td className="mono" style={{ padding: "8px 8px", color: r[2].startsWith("−") ? "#FF3621" : r[2].startsWith("+") ? "#06724a" : "var(--ink-3)" }}>{r[2]}</td>
                    <td className="mono" style={{ padding: "8px 8px", color: r[3].startsWith("−") ? "#FF3621" : r[3].startsWith("+") ? "#06724a" : "var(--ink-3)" }}>{r[3]}</td>
                    <td style={{ padding: "8px 8px" }}>
                      <span className={"pill " + (r[4] === "동의" ? "pill-ok" : r[4] === "불일치" ? "pill-danger" : "pill-warn")}>{r[4]}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ChartCard>
      </div>
    </div>
  );
}

function ChartCard({ title, sub, children }) {
  return (
    <div className="hl" style={{ background: "#fff", borderRadius: 10, padding: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
        <div>
          <div className="display" style={{ fontSize: 14.5, fontWeight: 500 }}>{title}</div>
          <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 2 }}>{sub}</div>
        </div>
        <button style={{ color: "var(--ink-3)" }}><I.Eye size={14}/></button>
      </div>
      {children}
    </div>
  );
}

function Critique({ k, v, sub, tone }) {
  return (
    <div className="hl" style={{ padding: 12, borderRadius: 6, background: "#FCFCFB" }}>
      <div className="label-mini" style={{ color: "var(--ink-3)" }}>{k}</div>
      <div className="display mono" style={{ fontSize: 19, fontWeight: 600, color: tone === "red" ? "#FF3621" : "var(--ink)", marginTop: 4 }}>{v}</div>
      <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginTop: 2 }}>{sub}</div>
    </div>
  );
}

window.PageWhatIf = PageWhatIf;
