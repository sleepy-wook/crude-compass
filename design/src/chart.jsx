// Hand-rolled SVG charts: tight, tabular, no library bloat

function Sparkline({ data, w = 80, h = 22, color = "#1B3139", fill = false, stroke = 1.4 }) {
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const step = w / (data.length - 1);
  const pts = data.map((v, i) => [i * step, h - ((v - min) / range) * (h - 2) - 1]);
  const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const dFill = d + ` L ${w} ${h} L 0 ${h} Z`;
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      {fill && <path d={dFill} fill={color} fillOpacity=".08" />}
      <path d={d} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function GaugeRing({ value, size = 132, stroke = 9, color = "#FF3621", track = "#F0F0EB" }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - Math.min(value, 100) / 100);
  return (
    <svg width={size} height={size}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={stroke} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
        strokeDasharray={c} strokeDashoffset={off} strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`} style={{ transition: "stroke-dashoffset .8s cubic-bezier(.2,.7,.2,1)" }} />
    </svg>
  );
}

function ProgressBar({ value, target, max = 100, height = 8, color = "#FF3621", track = "#F0F0EB" }) {
  return (
    <div style={{ position: "relative", height, background: track, borderRadius: 999, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${(value / max) * 100}%`, background: color, borderRadius: 999, transition: "width .8s" }} />
      {target != null && (
        <div style={{ position: "absolute", left: `calc(${(target / max) * 100}% - 1px)`, top: -3, bottom: -3, width: 2, background: "#1B3139" }} />
      )}
    </div>
  );
}

// Multi-line chart with axes, gridlines, optional annotations
function LineChart({ series, width = 600, height = 240, padding = { l: 44, r: 16, t: 16, b: 28 }, yLabel, xLabels, annotations = [], yDomain }) {
  const pw = width - padding.l - padding.r;
  const ph = height - padding.t - padding.b;
  const all = series.flatMap(s => s.data);
  const yMin = yDomain ? yDomain[0] : Math.min(...all);
  const yMax = yDomain ? yDomain[1] : Math.max(...all);
  const yRange = yMax - yMin || 1;
  const n = series[0].data.length;
  const xStep = pw / (n - 1);

  const ticks = 4;
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => yMin + (yRange * i) / ticks);

  const path = (data) => data.map((v, i) => {
    const x = padding.l + i * xStep;
    const y = padding.t + ph - ((v - yMin) / yRange) * ph;
    return (i ? "L" : "M") + x.toFixed(1) + " " + y.toFixed(1);
  }).join(" ");

  return (
    <svg width={width} height={height} style={{ display: "block", overflow: "visible" }}>
      {yTicks.map((t, i) => {
        const y = padding.t + ph - ((t - yMin) / yRange) * ph;
        return (
          <g key={i}>
            <line x1={padding.l} x2={width - padding.r} y1={y} y2={y} stroke="#ECECE8" strokeWidth="1" />
            <text x={padding.l - 8} y={y + 3} fill="#7A8A91" fontSize="10" textAnchor="end" fontFamily="JetBrains Mono">{Math.round(t)}</text>
          </g>
        );
      })}
      {annotations.map((a, i) => {
        const x = padding.l + a.i * xStep;
        return (
          <g key={i}>
            <line x1={x} x2={x} y1={padding.t} y2={padding.t + ph} stroke="#FF3621" strokeWidth="1" strokeDasharray="3 3" opacity=".5" />
            <text x={x + 4} y={padding.t + 10} fill="#FF3621" fontSize="9.5" fontFamily="JetBrains Mono" fontWeight="600">{a.label}</text>
          </g>
        );
      })}
      {series.map((s, i) => (
        <path key={i} d={path(s.data)} fill="none" stroke={s.color} strokeWidth={s.width || 1.6} strokeLinecap="round" strokeLinejoin="round"
          strokeDasharray={s.dash || undefined} />
      ))}
      {xLabels && xLabels.map((lab, i) => {
        const x = padding.l + i * xStep * (n / xLabels.length) * (xLabels.length / n);
        const realX = padding.l + (i * (n - 1) / (xLabels.length - 1)) * xStep;
        return <text key={i} x={realX} y={height - padding.b + 16} fill="#7A8A91" fontSize="10" textAnchor="middle" fontFamily="JetBrains Mono">{lab}</text>;
      })}
    </svg>
  );
}

function BarChart({ data, width = 600, height = 200, padding = { l: 44, r: 16, t: 16, b: 28 }, color = "#1B3139", xLabels, accentIdx }) {
  const pw = width - padding.l - padding.r;
  const ph = height - padding.t - padding.b;
  const max = Math.max(...data) * 1.1;
  const bw = pw / data.length * 0.7;
  const gap = (pw / data.length) * 0.3;
  const ticks = 4;
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      {Array.from({ length: ticks + 1 }, (_, i) => {
        const v = (max * i) / ticks;
        const y = padding.t + ph - (v / max) * ph;
        return (
          <g key={i}>
            <line x1={padding.l} x2={width - padding.r} y1={y} y2={y} stroke="#ECECE8" />
            <text x={padding.l - 8} y={y + 3} fill="#7A8A91" fontSize="10" textAnchor="end" fontFamily="JetBrains Mono">{Math.round(v)}</text>
          </g>
        );
      })}
      {data.map((v, i) => {
        const h = (v / max) * ph;
        const x = padding.l + i * (bw + gap) + gap / 2;
        const y = padding.t + ph - h;
        return <rect key={i} x={x} y={y} width={bw} height={h} fill={accentIdx === i ? "#FF3621" : color} rx="1" />;
      })}
      {xLabels && data.map((_, i) => {
        const x = padding.l + i * (bw + gap) + gap / 2 + bw / 2;
        return <text key={i} x={x} y={height - padding.b + 16} fill="#7A8A91" fontSize="10" textAnchor="middle" fontFamily="JetBrains Mono">{xLabels[i]}</text>;
      })}
    </svg>
  );
}

// Stylized world map fragment focused on Hormuz
function HormuzMap({ width = 720, height = 280, vessels = [] }) {
  // Approximate land outlines for Persian Gulf / Strait of Hormuz region
  // Coordinates are in arbitrary 720x280 space
  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: "block", background: "#FAFAF7" }}>
      {/* grid */}
      <defs>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#EFEFEA" strokeWidth="1"/>
        </pattern>
        <radialGradient id="riskGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#FF3621" stopOpacity=".22"/>
          <stop offset="100%" stopColor="#FF3621" stopOpacity="0"/>
        </radialGradient>
      </defs>
      <rect width={width} height={height} fill="url(#grid)"/>

      {/* Arabian Peninsula (left/bottom landmass) */}
      <path d="M 60 90 L 240 70 L 360 100 L 430 150 L 470 200 L 520 240 L 540 280 L 60 280 Z"
        fill="#EDEDE7" stroke="#D6D6CF" strokeWidth="1"/>
      {/* Iran (top landmass) */}
      <path d="M 280 0 L 720 0 L 720 110 L 640 130 L 540 120 L 460 130 L 400 110 L 340 90 L 300 70 Z"
        fill="#EDEDE7" stroke="#D6D6CF" strokeWidth="1"/>
      {/* Oman peninsula (right) */}
      <path d="M 540 240 L 580 200 L 600 160 L 640 140 L 680 180 L 700 230 L 720 280 L 540 280 Z"
        fill="#EDEDE7" stroke="#D6D6CF" strokeWidth="1"/>

      {/* Strait of Hormuz risk zone */}
      <ellipse cx="555" cy="170" rx="80" ry="38" fill="url(#riskGlow)"/>
      <ellipse cx="555" cy="170" rx="80" ry="38" fill="none" stroke="#FF3621" strokeWidth="1" strokeDasharray="4 4" opacity=".7"/>

      {/* Labels */}
      <text x="180" y="200" fill="#7A8A91" fontSize="10" fontFamily="JetBrains Mono" letterSpacing="2">SAUDI ARABIA</text>
      <text x="450" y="60"  fill="#7A8A91" fontSize="10" fontFamily="JetBrains Mono" letterSpacing="2">IRAN</text>
      <text x="640" y="260" fill="#7A8A91" fontSize="10" fontFamily="JetBrains Mono" letterSpacing="2">OMAN</text>
      <text x="500" y="140" fill="#FF3621" fontSize="11" fontFamily="JetBrains Mono" fontWeight="600">STRAIT OF HORMUZ</text>
      <text x="500" y="155" fill="#FF3621" fontSize="9" fontFamily="JetBrains Mono">BLOCKADE ZONE · D+18</text>

      {/* Korea destination indicator (off-map) */}
      <g transform="translate(680,30)">
        <rect width="38" height="22" rx="3" fill="#1B3139"/>
        <text x="19" y="14" fill="#fff" fontSize="9" textAnchor="middle" fontFamily="JetBrains Mono" fontWeight="600">→ KR</text>
      </g>

      {/* Vessel positions */}
      {vessels.map((v, i) => (
        <g key={i} transform={`translate(${v.x},${v.y})`}>
          <circle r="9" fill={v.status === "stranded" ? "#FF3621" : v.status === "transit" ? "#F59E0B" : "#10B981"} fillOpacity=".18"/>
          <circle r="4" fill={v.status === "stranded" ? "#FF3621" : v.status === "transit" ? "#F59E0B" : "#10B981"}/>
          <text x="9" y="4" fill="#1B3139" fontSize="10" fontFamily="JetBrains Mono" fontWeight="600">{v.id}</text>
        </g>
      ))}

      {/* compass */}
      <g transform="translate(36,240)" stroke="#7A8A91" fill="none">
        <circle r="12"/>
        <path d="M 0 -10 L 0 10 M -10 0 L 10 0"/>
        <text y="-14" fill="#7A8A91" fontSize="9" fontFamily="JetBrains Mono" textAnchor="middle">N</text>
      </g>
    </svg>
  );
}

window.Sparkline = Sparkline;
window.GaugeRing = GaugeRing;
window.ProgressBar = ProgressBar;
window.LineChart = LineChart;
window.BarChart = BarChart;
window.HormuzMap = HormuzMap;
