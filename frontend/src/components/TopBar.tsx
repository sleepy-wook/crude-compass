/**
 * TopBar — Sticky KPI strip (Stripe Dashboard 풍).
 *
 * 전 page 공통. 위기 점수 · mode chip · 진행 임무 · 마지막 갱신 · 실시간 연결 (WS + Slack).
 */
import { useMissionsActive, usePatternCurrent } from "../lib/queries";
import { useMissionsWebSocket } from "../lib/ws";
import { formatRoundedScore } from "../lib/utils";

type Mode = "HEDGE" | "OPPORTUNITY" | "STABLE";

function decideMode(missionType: string | null | undefined): Mode {
  if (missionType === "HEDGE") return "HEDGE";
  if (missionType === "OPPORTUNITY") return "OPPORTUNITY";
  return "STABLE";
}

function modeColor(mode: Mode): string {
  if (mode === "HEDGE") return "bg-crisis-50 text-crisis-700";
  if (mode === "OPPORTUNITY") return "bg-opportunity-50 text-opportunity-700";
  return "bg-line-1 text-ink-3";
}

function modeLabel(mode: Mode): string {
  if (mode === "HEDGE") return "위험방어";
  if (mode === "OPPORTUNITY") return "기회포착";
  return "관망";
}

function formatRelativeDate(dateStr: string | undefined): string {
  if (!dateStr) return "—";
  try {
    const then = new Date(`${dateStr}T06:30:00+09:00`).getTime();
    const now = Date.now();
    const diffMs = now - then;
    if (diffMs < 0) return "갱신 예정";
    const diffMin = Math.floor(diffMs / 60_000);
    const diffHours = Math.floor(diffMs / 3_600_000);
    const diffDays = Math.floor(diffMs / 86_400_000);
    if (diffMin < 60) return "방금 갱신";
    if (diffHours < 24) return `${diffHours}시간 전 갱신`;
    if (diffDays === 1) return "어제 갱신";
    if (diffDays < 7) return `${diffDays}일 전 갱신`;
    return `${dateStr.slice(5).replace("-", "/")} 갱신`;
  } catch {
    return "—";
  }
}

export function TopBar() {
  const pattern = usePatternCurrent();
  const missions = useMissionsActive();
  const { status } = useMissionsWebSocket();

  const cur = pattern.data?.current ?? null;
  const activeCount = missions.data?.missions?.length ?? 0;
  const mode = decideMode(cur?.mission_type);
  const score = cur?.pattern_score ?? null;
  const wsConnected = status === "connected";

  return (
    <header className="sticky top-0 z-30 bg-paper/95 backdrop-blur-md border-b border-line-1">
      <div className="max-w-7xl mx-auto px-8 py-3.5 flex items-center gap-x-6 flex-wrap">
        {/* Score + mode */}
        <KpiChip
          label="위기 점수"
          value={formatRoundedScore(score)}
          chip={
            <span
              className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${modeColor(mode)}`}
            >
              {modeLabel(mode)}
            </span>
          }
        />

        <Divider />

        {/* Signal accumulated count — 신뢰도 대신 진짜 핵심 */}
        <KpiChip
          label="90일 시그널"
          value={
            cur?.signal_count_90d != null
              ? `${cur.signal_count_90d.toLocaleString()}건`
              : "—"
          }
        />

        <Divider />

        {/* Active missions */}
        <KpiChip label="진행 임무" value={`${activeCount}건`} />

        <Divider />

        {/* Last update */}
        <KpiChip label="데이터" value={formatRelativeDate(cur?.date)} />

        <Divider />

        {/* Open Data Track 1 tagline */}
        <KpiChip label="Track 1" value="6 source · 무료" />


        <div className="flex-1" />

        {/* Connection indicators */}
        <div className="flex items-center gap-4 text-[11px] text-ink-3">
          <div className="flex items-center gap-1.5" title={wsConnected ? "실시간 연결됨" : "재연결 중"}>
            <span
              className={`w-1.5 h-1.5 rounded-full ${wsConnected ? "bg-opportunity-500" : "bg-ink-3/40"}`}
            />
            <span>실시간</span>
          </div>
          <div className="flex items-center gap-1.5" title="Slack에서도 임무 처리 가능">
            <span className="w-1.5 h-1.5 rounded-full bg-opportunity-500" />
            <span>Slack</span>
          </div>
        </div>
      </div>
    </header>
  );
}

function KpiChip({
  label,
  value,
  chip,
}: {
  label: string;
  value: string;
  chip?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] uppercase tracking-wider text-ink-3">{label}</span>
      <span className="font-display text-sm font-semibold text-ink-1 tabular-nums">{value}</span>
      {chip}
    </div>
  );
}

function Divider() {
  return <span className="w-px h-4 bg-line-1" />;
}
