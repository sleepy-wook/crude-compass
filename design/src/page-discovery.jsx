function PageDiscovery() {
  const [patternValue, setPatternValue] = React.useState(64);
  const [confirmedCard, setConfirmedCard] = React.useState(null);
  const [dismissed, setDismissed] = React.useState({});

  React.useEffect(() => {
    const t = setTimeout(() => setPatternValue(82), 250);
    return () => clearTimeout(t);
  }, []);

  // 4 categories aligned w/ Bidirectional Pattern Detection — bullish (hedge) vs bearish (opp) signal split
  const categories = [
    { name: "지정학",   kr: "Geopolitical",  bull: 6, bear: 1, weight: 32, dir: "bull" },
    { name: "정책",     kr: "Policy",        bull: 3, bear: 2, weight: 18, dir: "bull" },
    { name: "자연재해", kr: "Disaster",      bull: 1, bear: 0, weight: 5,  dir: "bull" },
    { name: "시장",     kr: "Market shock",  bull: 4, bear: 1, weight: 22, dir: "bull" },
  ];

  const cards = [
    {
      id: "c1", cat: "HEDGE \uc81c\uc548", icon: I.Brain, tone: "hedge", urgent: true,
      title: "Pre-emptive HEDGE Mission \u00b7 Pattern Score 82",
      titleKr: "3\uc8fc\uac04 escalation \uc2e0\ud638 6\uac74 \ub204\uc801 \u00b7 Cross-validation 4 source",
      meta: "Mission Plan Agent \u00b7 07:30 KST \u00b7 Lakebase missions:proposed",
      body: (<CardC1 />),
      cta: "Confirm \u00b7 Term 50% \u2192 70%",
      sec: "Open in Slack",
    },
    {
      id: "c2", cat: "OPPORTUNITY \uc81c\uc548", icon: I.TrendDown, tone: "opp", urgent: true,
      title: "Pre-emptive OPPORTUNITY Mission \u00b7 Pattern Score 22",
      titleKr: "\uc57d\uc138 \uc2e0\ud638 5\uac74 \ub204\uc801 (\ud734\uc804 \u00b7 SPR \u00b7 PMI 49.2 \u00b7 \uc6b4\uc784 \u2193 \u00b7 \uc7ac\uace0 \u2191)",
      meta: "Mission Plan Agent \u00b7 14:32 KST \u00b7 \uc218\ub839: \uacbd\uacc4 \uad8c\uace0",
      body: (<CardOpp />),
      cta: "Confirm \u00b7 Spot 50% \u2192 70%",
      sec: "Open in Slack",
    },
    {
      id: "c3", cat: "REACTIVE", icon: I.Ship, tone: "hedge", urgent: true,
      title: "VLCC #003 Hormuz \uc9c4\uc785 D\u22121 \u00b7 \uc6b0\ud68c \uacb0\uc815 \ucc3d 6\uc2dc\uac04",
      titleKr: "AIS \uc775\uba85\ud654 cargo \u00b7 5\ubd84 cron \ub300\uae30 \uc548 \ud558\uace0 \uc989\uc2dc trigger",
      meta: "Layer 2 Reactive \u00b7 11:08 KST \u00b7 aisstream WebSocket",
      body: (<CardC2 />),
      cta: "\ud76c\ub9dd\ubd09 \uc6b0\ud68c \uc2b9\uc778",
      sec: "\ud604 \uc704\uce58 \uc720\uc9c0 \u00b7 \ubaa8\ub2c8\ud130",
    },
    {
      id: "c4", cat: "OSP", icon: I.Doc, tone: "neutral", urgent: false,
      title: "Aramco 5\uc6d4 OSP \ubc1c\ud45c \u00b7 D\u22122 \uce74\uc6b4\ud2b8\ub2e4\uc6b4",
      titleKr: "\uacfc\uac70 6\ud68c \uc0ac\uc774\ud074 \uae30\uc900 +$2.40/bbl \uc608\uce21 (\uc2e0\ub8b0\ub3c4 95%)",
      meta: "Saudi Aramco \u00b7 \ubc1c\ud45c 5/6 18:00 AST",
      body: (<CardC3 />),
      cta: "OSP +$2.40 \uc120\uc81c \ud3ec\uc9c0\uc154\ub2dd",
      sec: "\ubc1c\ud45c\uae4c\uc9c0 \ub300\uae30",
    },
    {
      id: "c5", cat: "\ubbf8\uc158", icon: I.Target, tone: "hedge", urgent: false,
      title: "HEDGE Mission D+18 \uccb4\ud06c\ud3ec\uc778\ud2b8 \u00b7 \ub9e4\ub2c8\uc800 \uc2b9\uc778 \ub300\uae30",
      titleKr: "Term 50\u219270 \u00b7 18\uc77c\uac04 AI \uc790\uc728 \ud589\ub3d9 47\uac74 \u00b7 status: at_risk",
      meta: "Term 50\u219270 \u00b7 18/28 cycle \u00b7 mission_id HM-2026-1247",
      body: (<CardC5 />),
      cta: "D+19 AI \ud50c\ub79c \uc2b9\uc778",
      sec: "\ubaa9\ud45c \ube44\uc728 \uc870\uc815",
    },
  ];

  const visibleCards = cards.filter(c => !dismissed[c.id]);

  return (
    <div style={{ padding: "0 40px 60px", maxWidth: 1100, margin: "0 auto" }}>
      {/* Page header */}
      <header style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", padding: "28px 0 18px" }}>
        <div>
          <div className="label-mini" style={{ color: "var(--ink-3)" }}>오늘의 발견 · Bidirectional Signals</div>
          <h1 className="display" style={{ fontSize: 26, fontWeight: 600, margin: "4px 0 4px", letterSpacing: "-.02em" }}>
            HEDGE 2건 <span style={{ color: "var(--ink-3)", fontWeight: 400 }}>·</span> OPPORTUNITY 1건 <span style={{ color: "var(--ink-3)", fontWeight: 400 }}>· 5월 7일 목요일</span>
          </h1>
          <div style={{ fontSize: 13, color: "var(--ink-2)" }}>
            5건 · 예상 소요 <span className="mono">16분</span> · 100% open data · 마지막 갱신 <span className="mono">12초 전</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-ghost"><I.Filter size={13}/> 필터</button>
          <button className="btn btn-ghost"><I.Replay size={13}/> 어제 다시보기</button>
          <button className="btn btn-dark"><I.Spark size={13}/> AI에게 묻기</button>
        </div>
      </header>

      {/* Top: Bidirectional Pattern Score */}
      <section className="hl" style={{ background: "#fff", borderRadius: 8, padding: 22, marginBottom: 18 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 26 }}>
          {/* LEFT: bidirectional bar + categories */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <span className="label-mini" style={{ color: "var(--ink-3)" }}>Bidirectional Pattern Score</span>
              <span className="pill pill-neutral mono">3–6mo window</span>
              <span className="pill pill-neutral mono">cross-val 4×</span>
            </div>
            <BidirectionalScale value={patternValue}/>
            {/* category split */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginTop: 18 }}>
              {categories.map(c => (
                <div key={c.name} className="hl" style={{ padding: "10px 12px", borderRadius: 6, background: "#FCFCFB" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <div style={{ fontSize: 11.5, fontWeight: 500, color: "var(--ink-2)" }}>{c.name}</div>
                    <div className="mono" style={{ fontSize: 9.5, color: "var(--ink-4)" }}>{c.kr}</div>
                  </div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 6 }}>
                    <span className="mono" style={{ fontSize: 14, fontWeight: 600, color: "#FF3621" }}>↑{c.bull}</span>
                    <span className="mono" style={{ fontSize: 11, color: "var(--ink-4)" }}>/</span>
                    <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: "#0E8F5E" }}>↓{c.bear}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                    <div style={{ flex: 1, height: 3, background: "#F0F0EB", borderRadius: 99, overflow: "hidden", position: "relative" }}>
                      <div style={{ width: c.weight + "%", height: "100%", background: "#FF3621" }}/>
                    </div>
                    <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}>{c.weight}pt</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* RIGHT: dual mission pending */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ padding: "12px 14px", background: "var(--red-soft)", border: "1px solid #FF3621", borderRadius: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <span className="pill" style={{ background: "#FF3621", color: "#fff" }}>HEDGE</span>
                <span className="mono" style={{ fontSize: 10.5, color: "#b81d0a" }}>proposed · score 82</span>
              </div>
              <div className="display" style={{ fontSize: 14, fontWeight: 500, color: "#1B3139" }}>Term 50% → 70% (4주)</div>
              <div className="mono" style={{ fontSize: 11, color: "#1B3139", marginTop: 2 }}>시뮬 봉쇄 발발 시 <span style={{ fontWeight: 600 }}>+₩410억</span></div>
            </div>
            <div style={{ padding: "12px 14px", background: "var(--opp-soft)", border: "1px solid var(--opp)", borderRadius: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <span className="pill" style={{ background: "var(--opp)", color: "#fff" }}>OPPORTUNITY</span>
                <span className="mono" style={{ fontSize: 10.5, color: "#0E8F5E" }}>watchlist · score 38</span>
              </div>
              <div className="display" style={{ fontSize: 14, fontWeight: 500, color: "#1B3139" }}>Spot 50% → 70% (대기)</div>
              <div className="mono" style={{ fontSize: 11, color: "#1B3139", marginTop: 2 }}>약세 5건 더 누적 시 trigger</div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 4px", fontSize: 11, color: "var(--ink-3)" }}>
              <span className="dot blink" style={{ background: "#10B981" }}/>
              Slack ↔ Apps Lakebase Single Source of Truth · 5소 동기
            </div>
          </div>
        </div>
      </section>

      {/* Cards stack */}
      <div className="stagger" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {visibleCards.map((c, i) => {
          const Ic = c.icon;
          const isConfirmed = confirmedCard === c.id;
          return (
            <article key={c.id} className="hl lift" style={{
              background: "#fff", borderRadius: 8, padding: "18px 22px",
              borderLeft: "3px solid " + (c.tone === "opp" ? "var(--opp)" : c.tone === "hedge" ? "#FF3621" : "var(--line)")
            }}>
              <header style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                <div style={{
                  width: 28, height: 28, borderRadius: 6,
                  background: c.tone === "opp" ? "var(--opp-soft)" : c.tone === "hedge" ? "var(--red-soft)" : "#F0F0EB",
                  display: "grid", placeItems: "center"
                }}>
                  <Ic size={14} stroke={c.tone === "opp" ? "#0E8F5E" : c.tone === "hedge" ? "#FF3621" : "#1B3139"} sw={1.8}/>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span className="pill pill-neutral mono">{String(i + 1).padStart(2, '0')} · {c.cat}</span>
                    {c.tone === "hedge" && c.urgent && <span className="pill pill-danger">HEDGE</span>}
                    {c.tone === "opp" && <span className="pill" style={{ background: "var(--opp-soft)", color: "#0E8F5E" }}>OPPORTUNITY</span>}
                    <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>{c.meta}</span>
                  </div>
                  <h3 className="display" style={{ fontSize: 16, fontWeight: 500, margin: "6px 0 2px", letterSpacing: "-.01em" }}>{c.title}</h3>
                  <div style={{ fontSize: 12, color: "var(--ink-3)" }}>{c.titleKr}</div>
                </div>
                <button onClick={() => setDismissed({ ...dismissed, [c.id]: true })}
                  style={{ width: 28, height: 28, borderRadius: 6, color: "var(--ink-4)" }}>
                  <I.X size={14}/>
                </button>
              </header>

              <div style={{ marginBottom: 14 }}>{c.body}</div>

              <footer style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <button className="btn btn-primary"
                  onClick={() => setConfirmedCard(c.id)}
                  disabled={isConfirmed}
                  style={isConfirmed ? { background: "#10B981", opacity: .9 } : c.tone === "opp" ? { background: "var(--opp)" } : {}}>
                  {isConfirmed ? <><I.Check size={13}/> 승인됨 · D+19 대기열 등록</> : <>{c.cta} <I.ArrowRight size={13}/></>}
                </button>
                <button className="btn btn-ghost">{c.sec}</button>
                <div style={{ flex: 1 }}/>
                <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>id · {c.id.toUpperCase()}-2026-{1247 + i}</span>
              </footer>
            </article>
          );
        })}
      </div>
    </div>
  );
}

/* ---------- card bodies ---------- */

function StatCol({ k, kr, v, sub, color = "var(--ink)" }) {
  return (
    <div>
      <div className="label-mini" style={{ color: "var(--ink-3)" }}>{k} <span style={{ color: "var(--ink-4)", fontWeight: 400 }}>{kr}</span></div>
      <div className="display mono" style={{ fontSize: 22, fontWeight: 600, color, marginTop: 4 }}>{v}</div>
      {sub && <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function CardC1() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, padding: "8px 0" }}>
      <div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 16 }}>
          <StatCol k="HORMUZ 통과량" kr="vessels/30d" v="191" sub="7일 평균 2,840 대비 −93%" color="#FF3621"/>
          <StatCol k="DUBAI–BRENT" kr="스프레드" v="$11.40" sub="7일 전 $4.20에서 확대"/>
          <StatCol k="VLCC 용선료" kr="$/day" v="$98k" sub="WS 142 · +44%"/>
        </div>
        <div className="hl" style={{ padding: 12, borderRadius: 6, background: "#FCFCFB" }}>
          <div className="label-mini" style={{ color: "var(--ink-3)", marginBottom: 6 }}>AI 판단 근거</div>
          <div style={{ fontSize: 13, color: "var(--ink)", lineHeight: 1.55 }}>
            지난 7일간 Geopolitical 입력값이 +33pt 상승했고 Hormuz 통과량이 급감했습니다.
            Term 비중을 +15pt 늘리면 향후 4주간 평균 인도가 변동성을 σ <span className="mono">$8.4 → $3.1</span>로 낮춥니다.
          </div>
        </div>
      </div>
      <div className="hl" style={{ padding: 12, borderRadius: 6 }}>
        <div className="label-mini" style={{ color: "var(--ink-3)", marginBottom: 8 }}>시나리오 · 4주 인도원가 (₩억)</div>
        <BarChart
          data={[245, 268, 290, 312, 270, 240, 215]}
          accentIdx={3}
          xLabels={["Now","T+5","T+10","T+15","T+20","T+25","T+28"]}
          width={420} height={140}
        />
        <div style={{ display: "flex", gap: 16, marginTop: 6, fontSize: 11, color: "var(--ink-2)" }}>
          <span><span className="dot" style={{ background: "#1B3139" }}/> 현재 55:45</span>
          <span><span className="dot" style={{ background: "#FF3621" }}/> 권고 70:30 · 정점 T+15</span>
        </div>
      </div>
    </div>
  );
}

function CardC2() {
  const vessels = [
    { id: "001", x: 320, y: 235, status: "transit" },
    { id: "002", x: 420, y: 215, status: "transit" },
    { id: "003", x: 540, y: 175, status: "stranded" },
    { id: "004", x: 600, y: 195, status: "stranded" },
    { id: "005", x: 660, y: 155, status: "transit" },
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 18 }}>
      <div className="hl" style={{ borderRadius: 6, overflow: "hidden" }}>
        <HormuzMap vessels={vessels} height={210}/>
      </div>
      <div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
          <StatCol k="선박" kr="Vessel" v="VLCC #003" sub="2.1M bbl · Dubai 원유"/>
          <StatCol k="여수 도착" kr="ETA" v="5월 22일" sub="위험 · 4일 지연 가능" color="#FF3621"/>
          <StatCol k="체선료" kr="Demurrage" v="$28k/d" sub="48시간 초과 억류 시"/>
          <StatCol k="우회 비용" kr="Reroute" v="+$1.2M" sub="희망봉 경유 · +9일"/>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {[
            ["09:42", "AIS 핑 · 50해리 통제구역 진입"],
            ["10:15", "이란 순찰선 호위함 검문 · 통과"],
            ["11:08", "AI 경보: 우회 결정 창 6시간 남음"],
          ].map(([t, m]) => (
            <div key={t} style={{ display: "flex", gap: 10, fontSize: 12, color: "var(--ink-2)" }}>
              <span className="mono" style={{ color: "var(--ink-3)", width: 38 }}>{t}</span>
              <span>{m}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CardC3() {
  const days = ["May 6","May 7","May 8 ★"];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 24 }}>
      <div>
        <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
          {days.map((d, i) => (
            <div key={d} className="hl" style={{
              flex: 1, padding: "10px 12px", borderRadius: 6,
              background: i === 2 ? "var(--red-soft)" : "#FCFCFB",
              borderColor: i === 2 ? "#FF3621" : undefined
            }}>
              <div className="mono" style={{ fontSize: 10, color: i === 2 ? "#FF3621" : "var(--ink-3)" }}>{d}</div>
              <div className="display mono" style={{ fontSize: 18, fontWeight: 600, marginTop: 4 }}>
                {i === 2 ? "발표일" : "D−" + (2 - i)}
              </div>
            </div>
          ))}
        </div>
        <div style={{ fontSize: 13, color: "var(--ink-2)", lineHeight: 1.55 }}>
          AI 예측: Aramco OSP가 Dubai 대비 <span className="mono" style={{ color: "var(--ink)" }}>+$2.40/bbl</span> (신뢰도 95%, 과거 24회 사이클).
          오늘 800k bbl Term Lock 선제 포지셔닝 시 <span className="mono" style={{ color: "#FF3621" }}>약 ₩48억</span> 절감 추정.
        </div>
      </div>
      <div className="hl" style={{ padding: 12, borderRadius: 6 }}>
        <div className="label-mini" style={{ color: "var(--ink-3)", marginBottom: 8 }}>최근 6개 OSP 사이클 · Dubai 대비 조정폭 ($/bbl)</div>
        <BarChart
          data={[1.20, 0.80, 1.60, 2.10, 1.90, 2.40]}
          accentIdx={5}
          xLabels={["Nov","Dec","Jan","Feb","Mar","Apr"]}
          width={300} height={130}
        />
      </div>
    </div>
  );
}

function CardC4() {
  const bids = [
    { co: "Saudi Aramco",     vol: "1.2M bbl", price: "Dubai +$2.10", terms: "12mo · TPP", ai: 92, recommend: true },
    { co: "ADNOC",            vol: "0.8M bbl", price: "Dubai +$1.90", terms: "6mo · FOB",  ai: 88, recommend: true },
    { co: "BP Trading",       vol: "0.5M bbl", price: "Brent −$0.40", terms: "3mo · CFR",  ai: 71, recommend: false },
    { co: "TotalEnergies",    vol: "0.6M bbl", price: "Dubai +$2.60", terms: "12mo · CFR", ai: 64, recommend: false },
  ];
  return (
    <div className="hl" style={{ borderRadius: 6, overflow: "hidden" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
        <thead>
          <tr style={{ background: "#FCFCFB" }}>
            {["거래상대방", "수량", "가격", "조건", "AI 적합도", "액션"].map(h => (
              <th key={h} className="label-mini" style={{ textAlign: "left", padding: "10px 14px", color: "var(--ink-3)", borderBottom: "1px solid var(--line)" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bids.map((b, i) => (
            <tr key={b.co} style={{ borderBottom: i < bids.length - 1 ? "1px solid var(--line)" : "none", background: b.recommend ? "rgba(255,54,33,.025)" : "#fff" }}>
              <td style={{ padding: "12px 14px", fontWeight: 500 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="dot" style={{ background: b.recommend ? "#FF3621" : "#A9B4B9" }}/>
                  {b.co}
                </div>
              </td>
              <td className="mono" style={{ padding: "12px 14px" }}>{b.vol}</td>
              <td className="mono" style={{ padding: "12px 14px", color: "var(--ink)" }}>{b.price}</td>
              <td className="mono" style={{ padding: "12px 14px", color: "var(--ink-2)" }}>{b.terms}</td>
              <td style={{ padding: "12px 14px", width: 120 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ flex: 1, height: 4, background: "#F0F0EB", borderRadius: 99, overflow: "hidden" }}>
                    <div style={{ width: `${b.ai}%`, height: "100%", background: b.ai >= 80 ? "#FF3621" : "#1B3139" }}/>
                  </div>
                  <span className="mono" style={{ fontSize: 11, fontWeight: 600 }}>{b.ai}</span>
                </div>
              </td>
              <td style={{ padding: "12px 14px" }}>
                {b.recommend ? <span className="pill pill-danger">수락</span> : <span className="pill pill-neutral">카운터</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CardC5() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "center" }}>
      <div>
        <div className="label-mini" style={{ color: "var(--ink-3)", marginBottom: 6 }}>미션 · Term 50% → 70% (Hormuz 헤지)</div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 8 }}>
          <span className="display mono" style={{ fontSize: 28, fontWeight: 600 }}>65%</span>
          <span className="mono" style={{ fontSize: 12, color: "var(--ink-3)" }}>현재 Term · 목표 70%</span>
        </div>
        <ProgressBar value={65} target={70} max={100}/>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
          <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>50% 시작</span>
          <span className="mono" style={{ fontSize: 10.5, color: "var(--ink)" }}>70% 목표</span>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <StatCol k="AI 자율 행동" kr="actions" v="47" sub="지난 18일"/>
        <StatCol k="매니저 승인" kr="confirms" v="3" sub="총 5건 필요"/>
      </div>
    </div>
  );
}

function CardOpp() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, padding: "8px 0" }}>
      <div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
          <StatCol k="PATTERN SCORE" kr="bidirectional" v="22" sub="낮을수록 약세 강함" color="#0E8F5E"/>
          <StatCol k="권고" kr="action" v="Spot 50→70%" sub="4주 Pre-emptive opportunity"/>
        </div>
        <div className="hl" style={{ padding: 12, borderRadius: 6, background: "#FCFCFB" }}>
          <div className="label-mini" style={{ color: "var(--ink-3)", marginBottom: 8 }}>약세 신호 5건 · cross-validation</div>
          {[
            ["외교", "휴전 임박 · Reuters · AP confirm"],
            ["정책", "미국 SPR 1억 배럴 방출 발표"],
            ["수요", "중국 PMI 49.2 · 수축 영역"],
            ["시장", "VLCC 운임 −15% · 재고 ↑"],
            ["시장", "글로벌 정유 재고 증가"],
          ].map(([cat, msg]) => (
            <div key={msg} style={{ display: "flex", gap: 10, padding: "3px 0", fontSize: 12, color: "var(--ink-2)" }}>
              <span className="mono" style={{ color: "#0E8F5E", width: 42, fontSize: 10.5 }}>↓ {cat}</span>
              <span>{msg}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="hl" style={{ padding: 12, borderRadius: 6 }}>
        <div className="label-mini" style={{ color: "var(--ink-3)", marginBottom: 8 }}>시뮬 · 4주 인도가 (₩억)</div>
        <BarChart
          data={[260, 245, 230, 215, 195, 180, 165]}
          accentIdx={6}
          xLabels={["Now","T+5","T+10","T+15","T+20","T+25","T+28"]}
          width={420} height={140}
          color="#0E8F5E"
        />
        <div style={{ display: "flex", gap: 16, marginTop: 6, fontSize: 11, color: "var(--ink-2)" }}>
          <span><span className="dot" style={{ background: "#0E8F5E" }}/> Spot 70:30 · Brent $72 시으로 ↓</span>
        </div>
        <div className="mono" style={{ marginTop: 10, fontSize: 11, color: "#0E8F5E", fontWeight: 600 }}>
          약세 실현 시 +₩130억 · 다시 상승 시 −₩30억
        </div>
      </div>
    </div>
  );
}

function BidirectionalScale({ value }) {
  // Bar 0–100 with green opp zone (0–30), neutral (30–70), red hedge zone (70–100)
  return (
    <div style={{ position: "relative", marginTop: 12 }}>
      <div style={{ position: "relative", height: 28, borderRadius: 6, overflow: "hidden", background: "#F0F0EB" }}>
        <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "30%", background: "linear-gradient(to right, #0E8F5E, #C8E8DA)" }}/>
        <div style={{ position: "absolute", left: "30%", top: 0, bottom: 0, width: "40%", background: "#F0F0EB" }}/>
        <div style={{ position: "absolute", left: "70%", top: 0, bottom: 0, right: 0, background: "linear-gradient(to right, #FFD0C8, #FF3621)" }}/>
        <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 1, background: "#1B3139", opacity: .25 }}/>
        {/* needle */}
        <div style={{ position: "absolute", left: `calc(${value}% - 7px)`, top: -4, width: 14, height: 36, transition: "left .8s cubic-bezier(.2,.7,.2,1)" }}>
          <div style={{ width: 14, height: 14, background: "#fff", border: "2px solid #1B3139", borderRadius: 99, marginTop: 2 }}/>
          <div style={{ position: "absolute", left: 6, top: 16, width: 2, height: 24, background: "#1B3139" }}/>
        </div>
      </div>
      {/* labels */}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 10.5 }}>
        <span className="mono" style={{ color: "#0E8F5E", fontWeight: 600 }}>0 · OPPORTUNITY</span>
        <span className="mono" style={{ color: "var(--ink-3)" }}>30 · 약세</span>
        <span className="mono" style={{ color: "var(--ink-3)" }}>50 · 균형</span>
        <span className="mono" style={{ color: "var(--ink-3)" }}>70 · 주의</span>
        <span className="mono" style={{ color: "#FF3621", fontWeight: 600 }}>100 · HEDGE</span>
      </div>
      {/* current */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginTop: 14 }}>
        <span className="display mono" style={{ fontSize: 36, fontWeight: 600, color: "#FF3621", lineHeight: 1 }}>{value}</span>
        <span className="mono" style={{ fontSize: 11, color: "#FF3621" }}>+11 ▲ (3주 누적)</span>
        <span style={{ flex: 1 }}/>
        <span className="pill pill-danger">HEDGE · score ≥ 70</span>
      </div>
    </div>
  );
}

window.PageDiscovery = PageDiscovery;
