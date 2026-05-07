function PageDiscovery() {
  const [riskValue, setRiskValue] = React.useState(64);
  const [confirmedCard, setConfirmedCard] = React.useState(null);
  const [dismissed, setDismissed] = React.useState({});

  React.useEffect(() => {
    const t = setTimeout(() => setRiskValue(72), 250);
    return () => clearTimeout(t);
  }, []);

  const contributors = [
    { name: "거시경제",  kr: "Macro",        value: 58, delta: +3, spark: [40,42,44,46,48,52,54,56,58], color: "#1B3139" },
    { name: "가격",      kr: "Price",        value: 71, delta: +6, spark: [50,55,52,60,58,65,68,69,71], color: "#1B3139" },
    { name: "지정학",    kr: "Geopolitical", value: 88, delta: +11, spark: [50,52,55,60,65,72,80,84,88], color: "#FF3621" },
    { name: "사내·운영", kr: "Company",      value: 64, delta: -2, spark: [70,68,66,67,65,66,65,64,64], color: "#1B3139" },
  ];

  const cards = [
    {
      id: "c1", cat: "리스크", icon: I.Brain, urgent: true,
      title: "Hormuz 리스크 스코어 70 초과 · Term 비중 +15pt 권고",
      titleKr: "지난 7일간 Geopolitical 입력 +33pt · 행동 시점 도래",
      meta: "트리거 09:42 KST · Lakebase + Geopolitical Gold table",
      body: (
        <CardC1 />
      ),
      cta: "시나리오 시뮬레이션 실행",
      sec: "What-If에서 열기",
    },
    {
      id: "c2", cat: "선박", icon: I.Ship, urgent: true,
      title: "VLCC GS-CALTEX-003 Hormuz 진입 임박 · ETA 위험 D-1",
      titleKr: "우회 결정 창 6시간 · 체선료 노출 임박",
      meta: "AIS · 11:08 KST · MMSI 538009312",
      body: (
        <CardC2 />
      ),
      cta: "희망봉 우회 승인",
      sec: "현 위치 유지 · 모니터",
    },
    {
      id: "c3", cat: "ARAMCO", icon: I.Doc, urgent: false,
      title: "Aramco 5월 OSP(공식판매가) 발표 · D-2 카운트다운",
      titleKr: "과거 6회 사이클 기준 +$2.40/bbl 예측 (신뢰도 95%)",
      meta: "Saudi Aramco · 발표 예정 5월 6일 18:00 AST",
      body: (
        <CardC3 />
      ),
      cta: "OSP +$2.40 선제 포지셔닝",
      sec: "발표까지 대기",
    },
    {
      id: "c4", cat: "입찰", icon: I.Layers, urgent: false,
      title: "Frame Contract 입찰 · 4개사 대응 완료",
      titleKr: "AI 자동 협상 12/14 사이클 종료 · 매니저 승인 대기",
      meta: "AI 자동협상 12/14 cycle · 04:21 KST",
      body: (
        <CardC4 />
      ),
      cta: "ADNOC + Aramco 분할 수락",
      sec: "4개사 일괄 카운터제안",
    },
    {
      id: "c5", cat: "미션", icon: I.Target, urgent: false,
      title: "미션 D+18 체크포인트 · 매니저 승인 대기",
      titleKr: "Term 50→70 (Hormuz hedge) · 18일간 AI 자율 행동 47건",
      meta: "Term 50→70 · Hormuz hedge · 18/28 cycle",
      body: (
        <CardC5 />
      ),
      cta: "D+19 AI 플랜 승인",
      sec: "목표 비율 조정",
    },
  ];

  const visibleCards = cards.filter(c => !dismissed[c.id]);

  return (
    <div style={{ padding: "0 40px 60px", maxWidth: 1100, margin: "0 auto" }}>
      {/* Page header */}
      <header style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", padding: "28px 0 18px" }}>
        <div>
          <div className="label-mini" style={{ color: "var(--ink-3)" }}>오늘의 발견 · Discovery</div>
          <h1 className="display" style={{ fontSize: 26, fontWeight: 600, margin: "4px 0 4px", letterSpacing: "-.02em" }}>
            오늘의 의사결정 카드 <span style={{ color: "var(--ink-3)", fontWeight: 400 }}>· 5월 7일 목요일</span>
          </h1>
          <div style={{ fontSize: 13, color: "var(--ink-2)" }}>
            5건 · 예상 소요 <span className="mono">16분</span> · 마지막 갱신 <span className="mono">12초 전</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-ghost"><I.Filter size={13}/> 필터</button>
          <button className="btn btn-ghost"><I.Replay size={13}/> 어제 다시보기</button>
          <button className="btn btn-dark"><I.Spark size={13}/> AI에게 묻기</button>
        </div>
      </header>

      {/* Top: Risk score summary */}
      <section className="hl" style={{ background: "#fff", borderRadius: 8, padding: 24, marginBottom: 18 }}>
        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 32, alignItems: "center" }}>
          {/* Gauge */}
          <div style={{ position: "relative", width: 132, height: 132 }}>
            <GaugeRing value={riskValue} />
            <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", textAlign: "center" }}>
              <div>
                <div className="display mono" style={{ fontSize: 38, fontWeight: 600, lineHeight: 1, color: "var(--ink)" }}>{riskValue}</div>
                <div className="mono" style={{ fontSize: 9.5, letterSpacing: ".12em", color: "var(--ink-3)", marginTop: 4 }}>리스크 · 0–100</div>
              </div>
            </div>
          </div>

          {/* Contributors */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <span className="pill pill-danger"><span className="dot blink" style={{ background: "#FF3621" }}/> 높음</span>
              <span className="mono" style={{ fontSize: 12, color: "var(--ink-2)" }}>어제 대비</span>
              <span className="mono" style={{ fontSize: 12, color: "#FF3621", fontWeight: 600 }}>+8 ▲</span>
              <span style={{ fontSize: 12, color: "var(--ink-3)" }}>·</span>
              <span style={{ fontSize: 12, color: "var(--ink-2)" }}>7일 평균 <span className="mono">61</span></span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
              {contributors.map(c => (
                <div key={c.name} className="hl" style={{ padding: "10px 12px", borderRadius: 6, background: "#FCFCFB" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <div style={{ fontSize: 11.5, fontWeight: 500, color: "var(--ink-2)" }}>{c.name}</div>
                    <div className="mono" style={{ fontSize: 9.5, color: "var(--ink-4)" }}>{c.kr}</div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: 4 }}>
                    <div className="mono display" style={{ fontSize: 22, fontWeight: 600, color: c.color, lineHeight: 1 }}>{c.value}</div>
                    <Sparkline data={c.spark} w={60} h={20} color={c.color} fill stroke={1.4}/>
                  </div>
                  <div className="mono" style={{ fontSize: 10, color: c.delta > 0 ? "#FF3621" : "var(--ink-3)", marginTop: 4 }}>
                    {c.delta > 0 ? "▲" : "▼"} {Math.abs(c.delta)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* AI Recommendation */}
          <div style={{ width: 250, padding: 16, background: "var(--green)", color: "#fff", borderRadius: 6 }}>
            <div className="label-mini" style={{ color: "#7a8a91", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
              <I.Bolt size={11} stroke="#FF3621"/> AI 권고
            </div>
            <div className="mono" style={{ fontSize: 11, color: "#A9B4B9", marginBottom: 4 }}>현재 포트폴리오</div>
            <div className="display mono" style={{ fontSize: 18, fontWeight: 500, marginBottom: 12 }}>
              Term <span style={{ color: "#fff" }}>55%</span> <span style={{ color: "#5a6c73" }}>:</span> Spot <span style={{ color: "#fff" }}>45%</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <I.ArrowRight size={14} stroke="#FF3621"/>
              <div className="display mono" style={{ fontSize: 18, fontWeight: 600, color: "#FF3621" }}>
                Term <span style={{ color: "#fff" }}>70%</span> : Spot <span style={{ color: "#fff" }}>30%</span>
              </div>
            </div>
            <div style={{ fontSize: 11.5, color: "#A9B4B9", lineHeight: 1.5 }}>
              Hormuz 통과량 7일간 94% 감소. Dubai 스프레드 $12/bbl 하방 헤지 위해 4주 Term Lock 권고.
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
              borderLeft: c.urgent ? "3px solid #FF3621" : "1px solid var(--line)"
            }}>
              <header style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                <div style={{
                  width: 28, height: 28, borderRadius: 6,
                  background: c.urgent ? "var(--red-soft)" : "#F0F0EB",
                  display: "grid", placeItems: "center"
                }}>
                  <Ic size={14} stroke={c.urgent ? "#FF3621" : "#1B3139"} sw={1.8}/>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span className="pill pill-neutral mono">{String(i + 1).padStart(2, '0')} · {c.cat}</span>
                    {c.urgent && <span className="pill pill-danger">긴급</span>}
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
                  style={isConfirmed ? { background: "#10B981", opacity: .9 } : {}}>
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

window.PageDiscovery = PageDiscovery;
