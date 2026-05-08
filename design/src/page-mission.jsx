function PageMission() {
  const today = 18; // D+18 of 28
  const [selectedDay, setSelectedDay] = React.useState(today);

  // 28-day timeline events
  const timeline = React.useMemo(() => {
    const events = {
      1:  [{ kind: "ai", title: "미션 시작 · Term 50% 기준선 락", time: "08:00", detail: "Lakebase 스냅샷 · 4주 목표 Term 70%, Hormuz 헤지 프로필 로드." }],
      2:  [{ kind: "ai", title: "8개 거래상대방 RFQ 발송", time: "11:30", detail: "Aramco, ADNOC, KPC, BP, TotalEnergies, Shell, Vitol, Trafigura." }],
      3:  [{ kind: "ai", title: "협상 1차 사이클 · 8건 중 6건 회신", time: "23:14", detail: "6개사에 Dubai +$1.80 자동 카운터." }],
      4:  [{ kind: "mgr", title: "매니저: Trafigura 조건 거절", time: "09:18", detail: "사유: 거래상대방 리스크 38점, 임계 60 미달." }],
      5:  [{ kind: "ai", title: "0.4M bbl Term Lock · Aramco · Dubai +$1.95", time: "15:42", detail: "Term 비율 50% → 53.2%." }],
      6:  [{ kind: "ai", title: "Hormuz 통과량 정상 · 2,840 vessels/30d", time: "06:00", detail: "별도 행동 없음." }],
      7:  [{ kind: "ai", title: "0.3M bbl Term Lock · ADNOC · Dubai +$1.85", time: "18:21", detail: "Term 비율 53.2% → 55.6%." }],
      8:  [{ kind: "ai", title: "리스크 50 돌파 · GDACS 이란 경보", time: "02:14", detail: "모니터링 주기 1h → 5min 단축." }],
      9:  [{ kind: "mgr", title: "매니저: AI 주간 플랜 승인", time: "10:00", detail: "Term Lock 주당 +0.5M 유지." }],
      10: [{ kind: "ai", title: "Hormuz 통과량 전주 대비 −34%", time: "21:00", detail: "Discovery 피드 자동 등록." }],
      11: [{ kind: "ai", title: "0.6M bbl Term Lock · BP · Brent −$0.40", time: "13:09", detail: "Term 비율 55.6% → 60.4%." }],
      12: [{ kind: "ai", title: "Spot 입찰 2건 가격 확정 전 취소", time: "08:42", detail: "금요일 종가 대비 약 ₩18억 절감 추정." }],
      13: [{ kind: "mgr", title: "매니저: Spot 최저선 0.2M bbl 추가", time: "16:00", detail: "사유: Q2 정유 턴어라운드 버퍼." }],
      14: [{ kind: "ai", title: "리스크 60 돌파 · Hormuz 사건", time: "04:00", detail: "이란 보트가 싱가폴 선적 탱커 승선." }],
      15: [{ kind: "ai", title: "VLCC #007 희망봉 우회", time: "11:21", detail: "+9일 항해, +$1.2M 비용, 체선료 회피." }],
      16: [{ kind: "ai", title: "0.5M bbl Term Lock · TotalEnergies · Dubai +$2.30", time: "19:48", detail: "Term 비율 60.4% → 64.0%." }],
      17: [{ kind: "ai", title: "Aramco OSP +$2.40 시그널", time: "22:30", detail: "신뢰도 72%. 선제 포지셔닝 권고." }],
      18: [{ kind: "mgr", title: "D+18 체크포인트 · 매니저 승인 대기", time: "—", detail: "AI 누적 행동 및 향후 플랜 매니저 검토 대기." }],
      19: [{ kind: "ai", title: "예정 · OSP 발표 후 Term +0.5M bbl Lock", time: "—", detail: "조건: Aramco OSP +$2.40 ± $0.30." }],
      22: [{ kind: "ai", title: "예정 · 중간 점검 · 목표 67%", time: "—", detail: "괴리 3pt 초과 시 자동 리밸런싱." }],
      28: [{ kind: "ai", title: "미션 완료 · 목표 Term 70% 달성", time: "—", detail: "매니저와 최종 리뷰." }],
    };
    return Array.from({ length: 28 }, (_, i) => ({ day: i + 1, events: events[i + 1] || [] }));
  }, []);

  const selectedEvents = timeline[selectedDay - 1].events;

  return (
    <div style={{ padding: "0 40px 60px", maxWidth: 1280, margin: "0 auto" }}>
      {/* header */}
      <header style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", padding: "28px 0 18px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="label-mini" style={{ color: "var(--ink-3)" }}>Living Mission · mission_type</span>
            <span className="pill pill-danger" style={{ fontWeight: 700 }}>HEDGE</span>
            <span className="pill pill-warn">at_risk</span>
          </div>
          <h1 className="display" style={{ fontSize: 26, fontWeight: 600, margin: "6px 0 4px", letterSpacing: "-.02em" }}>
            Term 50% → 70% <span style={{ color: "var(--ink-3)", fontWeight: 400 }}>· Pre-emptive Hedge · Pattern 82</span>
          </h1>
          <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 13, color: "var(--ink-2)" }}>
            <span className="mono">D+{today}/28</span>
            <span className="mono">시작 4/19</span> · <span className="mono">종료 5/17</span>
            <span style={{ color: "var(--ink-3)" }}>· 담당 김지훈 · K-Petroleum</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-ghost"><I.Replay size={13}/> 타임라인 다시보기</button>
          <button className="btn btn-ghost">일시정지</button>
          <button className="btn btn-ghost" style={{ borderColor: "var(--opp)", color: "var(--opp)" }}>↔ Pivot to OPP</button>
          <button className="btn btn-primary"><I.Check size={13}/> D+19 플랜 승인</button>
        </div>
      </header>

      {/* 60/40 split */}
      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: 18 }}>
        {/* LEFT: timeline */}
        <section className="hl" style={{ background: "#fff", borderRadius: 8, padding: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <div>
              <div className="display" style={{ fontSize: 15, fontWeight: 500 }}>타임라인 · 28일</div>
              <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 2 }}>날짜를 클릭해 AI ⚡ / 매니저 👤 행동 보기</div>
            </div>
            <div style={{ display: "flex", gap: 14, fontSize: 11, color: "var(--ink-2)" }}>
              <span style={{ display: "flex", alignItems: "center", gap: 5 }}><I.Bolt size={11} stroke="#FF3621"/> AI <span className="mono" style={{ color: "var(--ink)" }}>47</span></span>
              <span style={{ display: "flex", alignItems: "center", gap: 5 }}><I.User size={11}/> 매니저 <span className="mono" style={{ color: "var(--ink)" }}>3</span></span>
            </div>
          </div>

          {/* Calendar grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 6, marginBottom: 18 }}>
            {timeline.map(({ day, events }) => {
              const isToday = day === today;
              const isPast = day < today;
              const isFuture = day > today;
              const isSelected = day === selectedDay;
              const hasMgr = events.some(e => e.kind === "mgr");
              const hasAi = events.some(e => e.kind === "ai");
              return (
                <button key={day}
                  onClick={() => setSelectedDay(day)}
                  className="lift"
                  style={{
                    aspectRatio: "1.05",
                    padding: "8px 8px",
                    borderRadius: 6,
                    background: isToday ? "#FF3621" : isSelected ? "var(--green)" : "#fff",
                    color: (isToday || isSelected) ? "#fff" : "var(--ink)",
                    border: "1px solid " + (isToday ? "#FF3621" : isSelected ? "var(--green)" : "var(--line)"),
                    opacity: isFuture ? .65 : 1,
                    textAlign: "left",
                    display: "flex", flexDirection: "column", justifyContent: "space-between"
                  }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <span className="mono" style={{ fontSize: 10, opacity: .7 }}>D+{day}</span>
                    {isFuture && <span className="mono" style={{ fontSize: 9, opacity: .5 }}>—</span>}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    {hasAi && <I.Bolt size={10} stroke={isToday || isSelected ? "#fff" : "#FF3621"}/>}
                    {hasMgr && <I.User size={10} stroke={isToday || isSelected ? "#fff" : "#1B3139"} sw={2}/>}
                    {!hasAi && !hasMgr && isPast && <span style={{ fontSize: 10, opacity: .4 }}>·</span>}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Day detail */}
          <div className="hl" style={{ borderRadius: 6, padding: 16, background: "#FCFCFB" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              <span className="display mono" style={{ fontSize: 20, fontWeight: 600 }}>D+{selectedDay}</span>
              <span style={{ fontSize: 12, color: "var(--ink-3)" }}>
                {new Date(2026, 3, 18 + selectedDay).toLocaleDateString("en-US", { month: "short", day: "numeric", weekday: "short" })}
              </span>
              {selectedDay === today && <span className="pill pill-danger">오늘</span>}
              {selectedDay > today && <span className="pill pill-neutral">계획</span>}
            </div>

            {selectedEvents.length === 0 ? (
              <div style={{ fontSize: 12.5, color: "var(--ink-3)", padding: "20px 0" }}>
                이 날 별도 행동 없음. AI는 패시브 모니터링 지속 (~1,200건 데이터 포인트 기록).
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {selectedEvents.map((e, i) => (
                  <div key={i} style={{ display: "flex", gap: 12, padding: 10, background: "#fff", border: "1px solid var(--line)", borderRadius: 6 }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: 6,
                      background: e.kind === "ai" ? "var(--red-soft)" : "var(--green)",
                      color: e.kind === "ai" ? "#FF3621" : "#fff",
                      display: "grid", placeItems: "center", flexShrink: 0
                    }}>
                      {e.kind === "ai" ? <I.Bolt size={13} stroke="#FF3621"/> : <I.User size={13} sw={2}/>}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 13, fontWeight: 500 }}>{e.title}</span>
                        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginLeft: "auto" }}>{e.time}</span>
                      </div>
                      <div style={{ fontSize: 12, color: "var(--ink-2)", marginTop: 4 }}>{e.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* RIGHT: live state */}
        <section style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Progress */}
          <div className="hl" style={{ background: "#fff", borderRadius: 8, padding: 18 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
              <span className="label-mini" style={{ color: "var(--ink-3)" }}>Term : Spot 비율 · 현재</span>
              <span className="pill pill-warn">정상 진행</span>
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 14 }}>
              <span className="display mono" style={{ fontSize: 32, fontWeight: 600 }}>65</span>
              <span style={{ fontSize: 14, color: "var(--ink-3)" }}>: 35</span>
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)", marginLeft: 6 }}>목표 +20pt 중 +15pt 달성</span>
            </div>
            <ProgressBar value={65} target={70} max={100}/>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
              <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>50% 시작</span>
              <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>현재 65%</span>
              <span className="mono" style={{ fontSize: 10.5, color: "var(--ink)" }}>70% 목표 ◆</span>
            </div>
          </div>

          {/* Frame contracts */}
          <div className="hl" style={{ background: "#fff", borderRadius: 8, padding: 18 }}>
            <div className="label-mini" style={{ color: "var(--ink-3)", marginBottom: 10 }}>Frame Contract 협상 현황</div>
            {[
              { co: "Saudi Aramco",  status: "락 완료",  vol: "1.2M", color: "ok",     pct: 100 },
              { co: "ADNOC",         status: "락 완료",  vol: "0.8M", color: "ok",     pct: 100 },
              { co: "BP Trading",    status: "카운터 중", vol: "0.5M", color: "warn",   pct: 65 },
              { co: "TotalEnergies", status: "대기",     vol: "0.6M", color: "neutral",pct: 30 },
            ].map(c => (
              <div key={c.co} style={{ padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <span style={{ fontSize: 12.5, fontWeight: 500 }}>{c.co}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>{c.vol} bbl</span>
                    <span className={"pill pill-" + c.color}>{c.status}</span>
                  </div>
                </div>
                <div style={{ height: 3, background: "#F0F0EB", borderRadius: 99 }}>
                  <div style={{
                    width: c.pct + "%", height: "100%",
                    background: c.color === "ok" ? "#10B981" : c.color === "warn" ? "#F59E0B" : "#A9B4B9",
                    borderRadius: 99
                  }}/>
                </div>
              </div>
            ))}
          </div>

          {/* Cumulative metrics */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div className="hl" style={{ background: "var(--green)", color: "#fff", borderRadius: 8, padding: 16 }}>
              <div className="label-mini" style={{ color: "#7a8a91" }}><I.Bolt size={11} stroke="#FF3621"/> AI 자율 행동</div>
              <div className="display mono" style={{ fontSize: 32, fontWeight: 600, margin: "6px 0 2px" }}>47</div>
              <div className="mono" style={{ fontSize: 10.5, color: "#A9B4B9" }}>건 · 18일간</div>
            </div>
            <div className="hl" style={{ background: "#fff", borderRadius: 8, padding: 16 }}>
              <div className="label-mini" style={{ color: "var(--ink-3)" }}><I.User size={11}/> 매니저 승인</div>
              <div className="display mono" style={{ fontSize: 32, fontWeight: 600, margin: "6px 0 2px" }}>3<span style={{ fontSize: 16, color: "var(--ink-3)" }}>/5</span></div>
              <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>체크포인트</div>
            </div>
          </div>

          {/* Pivot watch — bidirectional */}
          <div className="hl" style={{ background: "#fff", borderRadius: 8, padding: 18, borderLeft: "3px solid var(--ink)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <div className="label-mini" style={{ color: "var(--ink-3)" }}>Pivot Watch · bidirectional</div>
              <span className="pill pill-neutral mono">2 source · 신뢰도 med</span>
            </div>
            <div style={{ position: "relative", height: 8, borderRadius: 99, overflow: "hidden", background: "linear-gradient(to right, #0E8F5E 0%, #C8E8DA 30%, #F0F0EB 30% 70%, #FFD0C8 70%, #FF3621 100%)" }}>
              <div style={{ position: "absolute", left: "82%", top: -3, bottom: -3, width: 2, background: "#1B3139" }}/>
              <div style={{ position: "absolute", left: "calc(82% - 5px)", top: -2, width: 12, height: 12, borderRadius: 99, background: "#fff", border: "2px solid #1B3139" }}/>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 10, color: "var(--ink-3)" }}>
              <span className="mono" style={{ color: "#0E8F5E" }}>OPP ≤30</span>
              <span className="mono">균형 50</span>
              <span className="mono" style={{ color: "#FF3621" }}>HEDGE ≥70 · 현재 82</span>
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 12, padding: "10px 12px", background: "#FCFCFB", borderRadius: 6, border: "1px dashed var(--line-2)", fontSize: 12, color: "var(--ink-2)" }}>
              <I.Bolt size={12} stroke="#FF3621"/>
              <div>
                <span style={{ fontWeight: 500 }}>휴전 임박 시 Pivot 트리거</span>
                <div style={{ color: "var(--ink-3)", fontSize: 11.5, marginTop: 2 }}>Score 30↓ → Spot 70% Mission으로 5초 안에 자동 재생성</div>
              </div>
            </div>
          </div>

          {/* ROI scenarios */}
          <div className="hl" style={{ background: "#fff", borderRadius: 8, padding: 18 }}>
            <div className="label-mini" style={{ color: "var(--ink-3)", marginBottom: 10 }}>시나리오 ROI · 무대응 대비</div>
            {[
              { lbl: "Brent $130 + Dubai $125", val: "+₩320억", pct: 92, pos: true },
              { lbl: "Brent $110 + Dubai $108", val: "+₩140억", pct: 60, pos: true },
              { lbl: "Brent $100 + Dubai $98",  val: "+₩40억",  pct: 25, pos: true },
              { lbl: "Brent $90 + Dubai $85",   val: "−₩50억",  pct: 30, pos: false },
            ].map(s => (
              <div key={s.lbl} style={{ display: "grid", gridTemplateColumns: "1.5fr 2fr 1fr", alignItems: "center", gap: 10, padding: "6px 0" }}>
                <div className="mono" style={{ fontSize: 11.5, color: "var(--ink-2)" }}>{s.lbl}</div>
                <div style={{ position: "relative", height: 8, background: "#F4F4EF", borderRadius: 99, overflow: "hidden" }}>
                  <div style={{
                    position: "absolute", top: 0, bottom: 0,
                    left: s.pos ? "50%" : `${50 - s.pct / 2}%`,
                    width: `${s.pct / 2}%`,
                    background: s.pos ? "#10B981" : "#FF3621"
                  }}/>
                  <div style={{ position: "absolute", left: "50%", top: -2, bottom: -2, width: 1, background: "#1B3139" }}/>
                </div>
                <div className="mono" style={{ fontSize: 12, fontWeight: 600, textAlign: "right", color: s.pos ? "#06724a" : "#FF3621" }}>{s.val}</div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* BOTTOM: cargo map */}
      <section className="hl" style={{ background: "#fff", borderRadius: 8, padding: 20, marginTop: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div>
            <div className="display" style={{ fontSize: 15, fontWeight: 500 }}>선단 위치 · Hormuz 해협</div>
            <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 2 }}>K-Petroleum 익명화 VLCC 5척 · 통제구역 내 2척 억류 · MMSI 가명 처리</div>
          </div>
          <div style={{ display: "flex", gap: 14, fontSize: 11, color: "var(--ink-2)" }}>
            <span style={{ display: "flex", alignItems: "center", gap: 5 }}><span className="dot" style={{ background: "#10B981" }}/> 안전</span>
            <span style={{ display: "flex", alignItems: "center", gap: 5 }}><span className="dot" style={{ background: "#F59E0B" }}/> 항해 중</span>
            <span style={{ display: "flex", alignItems: "center", gap: 5 }}><span className="dot" style={{ background: "#FF3621" }}/> 억류</span>
            <span className="mono" style={{ color: "var(--ink-3)" }}>· AIS 실시간</span>
          </div>
        </div>
        <HormuzMap height={300} vessels={[
          { id: "001", x: 220, y: 245, status: "transit" },
          { id: "002", x: 380, y: 225, status: "transit" },
          { id: "003", x: 530, y: 175, status: "stranded" },
          { id: "004", x: 595, y: 195, status: "stranded" },
          { id: "005", x: 670, y: 145, status: "safe" },
        ]}/>
      </section>
    </div>
  );
}

window.PageMission = PageMission;
