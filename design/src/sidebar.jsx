function Sidebar({ page, setPage }) {
  const items = [
    { id: "discovery", label: "오늘의 발견", kr: "Discovery", icon: I.Compass, badge: 5, kbd: "1" },
    { id: "mission",   label: "진행 중 미션", kr: "Living Mission", icon: I.Target, badge: null, kbd: "2" },
    { id: "whatif",    label: "시뮬레이션", kr: "What-If", icon: I.Flask, badge: null, kbd: "3" },
  ];
  return (
    <aside style={{
      width: 232, background: "var(--green)", color: "#fff",
      display: "flex", flexDirection: "column", padding: "20px 16px", flexShrink: 0,
      position: "sticky", top: 0, height: "100vh"
    }}>
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 8px 18px" }}>
        <I.Logo size={20}/>
        <div>
          <div className="display" style={{ fontWeight: 600, fontSize: 14.5, letterSpacing: "-.01em" }}>Crude Compass</div>
          <div className="mono" style={{ fontSize: 9.5, color: "#5a6c73", letterSpacing: ".1em", marginTop: 1 }}>BIDIRECTIONAL · v0.5</div>
        </div>
      </div>

      {/* Org switcher */}
      <button style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", marginBottom: 10,
        background: "rgba(255,255,255,.04)", border: "1px solid rgba(255,255,255,.08)",
        borderRadius: 6, color: "#fff", fontSize: 12, fontWeight: 500, textAlign: "left"
      }}>
        <div style={{ width: 18, height: 18, background: "#FF3621", borderRadius: 3, display: "grid", placeItems: "center", fontSize: 9, fontWeight: 700 }}>K</div>
        <div style={{ flex: 1 }}>
          <div>K-Petroleum <span style={{ color: "#7a8a91", fontSize: 10, fontWeight: 400 }}>가상</span></div>
          <div className="mono" style={{ fontSize: 9.5, color: "#7a8a91" }}>정제 80만 b/d · 100% open data</div>
        </div>
        <div style={{ color: "#5a6c73" }}>⌄</div>
      </button>

      {/* Search */}
      <button style={{
        display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", marginBottom: 18,
        background: "transparent", border: "1px solid rgba(255,255,255,.08)",
        borderRadius: 6, color: "#7a8a91", fontSize: 12, textAlign: "left"
      }}>
        <I.Search size={13}/> <span style={{ flex: 1 }}>검색…</span>
        <kbd className="mono" style={{ fontSize: 10, color: "#5a6c73", padding: "1px 5px", border: "1px solid #2f535e", borderRadius: 3 }}>⌘K</kbd>
      </button>

      {/* Nav */}
      <div className="label-mini" style={{ color: "#5a6c73", padding: "0 8px 8px" }}>워크스페이스</div>
      <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {items.map(it => {
          const Ic = it.icon;
          const active = page === it.id;
          return (
            <button key={it.id} className={"nav-item " + (active ? "active" : "")} onClick={() => setPage(it.id)}>
              <Ic size={15} stroke={active ? "#FF3621" : "currentColor"} sw={1.7}/>
              <span>{it.label}</span>
              {it.badge != null && (
                <span className="mono" style={{
                  marginLeft: "auto", background: active ? "#FF3621" : "rgba(255,255,255,.06)",
                  color: active ? "#fff" : "#A9B4B9", padding: "1px 6px", borderRadius: 999, fontSize: 10
                }}>{it.badge}</span>
              )}
              {it.badge == null && <kbd>{it.kbd}</kbd>}
            </button>
          );
        })}
      </nav>

      <div className="label-mini" style={{ color: "#5a6c73", padding: "20px 8px 8px" }}>데이터 소스</div>
      <div style={{ padding: "0 8px", display: "flex", flexDirection: "column", gap: 6 }}>
        {[
          ["AIS WebSocket", "실시간"],
          ["OilPriceAPI", "실시간"],
          ["GDACS", "실시간"],
          ["ECOS", "30m"],
          ["Lakebase Postgres", "실시간"],
        ].map(([n, s]) => (

          <div key={n} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11.5, color: "#A9B4B9" }}>
            <span className={"dot " + (s === "실시간" ? "blink" : "")} style={{ background: s === "실시간" ? "#10B981" : "#7A8A91" }}/>
            <span style={{ flex: 1 }}>{n}</span>
            <span className="mono" style={{ fontSize: 9.5, color: "#5a6c73" }}>{s}</span>
          </div>
        ))}
      </div>

      <div style={{ flex: 1 }}/>

      {/* Pattern Score — bidirectional */}
      <div style={{ padding: 10, marginBottom: 12, background: "#243f48", borderRadius: 6, border: "1px solid #2f535e" }}>
        <div className="label-mini" style={{ color: "#7a8a91", marginBottom: 6, display: "flex", justifyContent: "space-between" }}>
          <span>Pattern Score</span><span style={{ color: "#FF3621" }}>HEDGE</span>
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 6 }}>
          <span className="display" style={{ fontSize: 22, fontWeight: 600 }}>82</span>
          <span className="mono" style={{ fontSize: 10, color: "#FF3621" }}>+11 ▲</span>
        </div>
        {/* mini bidirectional bar 0-100, 50=balance */}
        <div style={{ position: "relative", height: 4, background: "linear-gradient(to right, #0E8F5E 0%, #0E8F5E 30%, #2f535e 30%, #2f535e 70%, #FF3621 70%, #FF3621 100%)", borderRadius: 99 }}>
          <div style={{ position: "absolute", left: "50%", top: -2, bottom: -2, width: 1, background: "#7a8a91", opacity: .5 }}/>
          <div style={{ position: "absolute", left: "calc(82% - 4px)", top: -3, width: 8, height: 8, background: "#fff", border: "1px solid #1B3139", borderRadius: 99 }}/>
        </div>
        <div className="mono" style={{ fontSize: 9, color: "#5a6c73", display: "flex", justifyContent: "space-between", marginTop: 4 }}>
          <span>OPP 0</span><span>균형 50</span><span>HEDGE 100</span>
        </div>
      </div>

      {/* User */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 4px", borderTop: "1px solid #2f535e" }}>
        <div style={{ width: 28, height: 28, borderRadius: 999, background: "linear-gradient(135deg,#FF3621,#1B3139)", display: "grid", placeItems: "center", fontWeight: 600, fontSize: 11 }}>김</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 500 }}>김지훈</div>
          <div style={{ fontSize: 10.5, color: "#7a8a91" }}>원유조달 시니어 매니저</div>
        </div>
        <I.Bell size={14} stroke="#7a8a91"/>
      </div>
    </aside>
  );
}

window.Sidebar = Sidebar;
