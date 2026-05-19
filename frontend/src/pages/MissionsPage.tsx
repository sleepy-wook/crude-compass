/**
 * MissionsPage — /missions
 *
 * Linear/Gmail 풍 split layout:
 *   좌측: mission list (active / proposed / completed 필터)
 *   우측: 선택된 mission detail panel + actions
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  useMission,
  useMissionsActive,
  useMissionConfirm,
  useMissionModify,
  useMissionPivot,
  useMissionReject,
} from "../lib/queries";
import { MissionSplitBar } from "../components/MissionSplitBar";
import { MissionTypePill, StatusPill } from "../components/StatusPill";
import { AgentActivityTimeline } from "../components/AgentActivityTimeline";
import { SuggestedNextActions } from "../components/SuggestedNextActions";
import type { Mission } from "../lib/types";
import {
  formatDate,
  missionTypeLabel,
  normalizeScenarioLabel,
  relativeTime,
  statusLabel,
  termSpotLabel,
} from "../lib/utils";
type Filter = "all" | "active" | "proposed";
type DateRange = "all" | "7d" | "30d" | "90d";

const DAYS: Record<DateRange, number> = { all: Infinity, "7d": 7, "30d": 30, "90d": 90 };
const RANGE_LABEL: Record<DateRange, string> = {
  all: "전체",
  "7d": "7일",
  "30d": "30일",
  "90d": "90일",
};

// confirmed_by raw 값 → 매니저용 표시 라벨.
// service principal UUID (예: "72770060767895@74746565268093800") 또는 빈 값이면 hide,
// email/사람 이름이면 @ 앞부분만, 그 외 raw 그대로.
function prettyActor(raw: string | null | undefined): string {
  if (!raw) return "매니저";
  // SP UUID 패턴: 숫자만 또는 long@long
  if (/^\d+@\d+$/.test(raw) || /^[0-9a-f-]{30,}/.test(raw)) return "매니저";
  // email 패턴
  if (raw.includes("@")) return raw.split("@")[0];
  return raw;
}

export function MissionsPage() {
  const { id: routeId } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const { data, isLoading } = useMissionsActive();
  const missions = data?.missions || [];
  const [filter, setFilter] = useState<Filter>("all");
  const [dateRange, setDateRange] = useState<DateRange>("all");
  const [selectedId, setSelectedId] = useState<string | null>(routeId ?? null);

  // Auto-select first mission on load
  useEffect(() => {
    if (!selectedId && missions.length > 0) {
      setSelectedId(missions[0].mission_id);
    }
  }, [missions, selectedId]);

  // Sync URL with selected
  useEffect(() => {
    if (selectedId && selectedId !== routeId) {
      navigate(`/missions/${selectedId}`, { replace: true });
    }
  }, [selectedId, routeId, navigate]);

  const filtered = missions.filter((m) => {
    if (filter === "active" && !["active", "on_track", "at_risk"].includes(m.status)) return false;
    if (filter === "proposed" && m.status !== "proposed") return false;
    if (dateRange !== "all") {
      const ageDays = (Date.now() - new Date(m.created_at).getTime()) / 86_400_000;
      if (ageDays > DAYS[dateRange]) return false;
    }
    return true;
  });

  return (
    <div className="flex h-[calc(100vh-56px)]">
      {/* Left — list */}
      <div className="w-[380px] border-r border-line-1 flex flex-col">
        {/* Page header */}
        <div className="px-6 py-5 border-b border-line-1">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-1.5">Case File</div>
          <h1 className="font-display text-xl font-semibold text-ink-1 mb-3">결정 케이스 기록</h1>
          {/* Status filter tabs */}
          <div className="flex gap-1 text-[12px] mb-2">
            {(["all", "proposed", "active"] as Filter[]).map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={
                  filter === f
                    ? "px-2.5 py-1 rounded bg-ink-1 text-paper"
                    : "px-2.5 py-1 rounded text-ink-3 hover:text-ink-1 hover:bg-line-1"
                }
              >
                {f === "all" ? "전체" : f === "proposed" ? "검토 대기" : "진행 중"}
                <span className="ml-1.5 text-[11px] opacity-70">
                  {f === "all"
                    ? missions.length
                    : f === "proposed"
                      ? missions.filter((m) => m.status === "proposed").length
                      : missions.filter((m) =>
                          ["active", "on_track", "at_risk"].includes(m.status),
                        ).length}
                </span>
              </button>
            ))}
          </div>
          {/* Date range filter — 최근 N일 (case 누적 시 narrow 가능) */}
          <div className="flex gap-1 text-[11px]">
            <span className="px-1 py-1 text-ink-3 uppercase tracking-wider">기간</span>
            {(["all", "90d", "30d", "7d"] as DateRange[]).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setDateRange(r)}
                className={
                  dateRange === r
                    ? "px-2 py-1 rounded bg-line-2 text-ink-1 font-medium"
                    : "px-2 py-1 rounded text-ink-3 hover:text-ink-2 hover:bg-line-1"
                }
              >
                {RANGE_LABEL[r]}
              </button>
            ))}
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading && <div className="p-6 text-sm text-ink-3">불러오는 중...</div>}
          {!isLoading && filtered.length === 0 && (
            <div className="p-6 text-sm text-ink-3">해당 상태의 case가 없습니다.</div>
          )}
          {filtered.map((m) => (
            <button
              key={m.mission_id}
              type="button"
              onClick={() => setSelectedId(m.mission_id)}
              className={
                selectedId === m.mission_id
                  ? "w-full text-left px-6 py-4 border-b border-line-1 bg-line-1/60"
                  : "w-full text-left px-6 py-4 border-b border-line-1 hover:bg-line-1/40 transition-colors"
              }
            >
              <div className="flex items-center gap-2 mb-1.5">
                <MissionTypePill type={m.mission_type} />
                <StatusPill status={m.status} />
                <span className="ml-auto text-[10px] text-ink-3">{relativeTime(m.created_at)}</span>
              </div>
              <div className="font-medium text-sm text-ink-1 line-clamp-1 mb-1">
                {m.mission_type === "HEDGE" ? "Term 비중" : "Spot 비중"} 60%{" "}
                <span className="text-ink-3 mx-0.5">→</span>{" "}
                {m.target_pct ?? (m.mission_type === "HEDGE" ? 75 : 70)}%
              </div>
              <div className="flex gap-3 text-[11px] text-ink-3">
                <span>
                  위기 {m.pattern_score != null ? Math.round(m.pattern_score / 10) : "—"}/10
                </span>
                {m.target_pct !== null && (
                  <span>
                    {termSpotLabel(m.mission_type)} {m.target_pct}%
                  </span>
                )}
                <span>{m.duration_days}일</span>
              </div>
            </button>
          ))}
        </div>

        {/* Slack note */}
        <div className="px-6 py-3 border-t border-line-1 text-[11px] text-ink-3 leading-relaxed bg-line-1/30">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-opportunity-500 mr-1.5 align-middle" />
          모든 case는 Slack에서도 채택/거절/방향 전환할 수 있습니다.
        </div>
      </div>

      {/* Right — detail */}
      <div className="flex-1 overflow-y-auto">
        {selectedId ? (
          <MissionDetail missionId={selectedId} />
        ) : (
          <div className="h-full flex items-center justify-center text-sm text-ink-3">
            왼쪽에서 case를 선택하세요.
          </div>
        )}
      </div>
    </div>
  );
}

function MissionDetail({ missionId }: { missionId: string }) {
  const { data: m, isLoading } = useMission(missionId);
  const { data: missionsData } = useMissionsActive();
  const confirmMut = useMissionConfirm();
  const rejectMut = useMissionReject();
  const pivotMut = useMissionPivot();
  const modifyMut = useMissionModify();
  const [showPivot, setShowPivot] = useState(false);
  const [pivotReason, setPivotReason] = useState("");
  const [showModify, setShowModify] = useState(false);
  const [modifyTarget, setModifyTarget] = useState<number | null>(null);
  const [modifyReason, setModifyReason] = useState("");

  if (isLoading) return <div className="p-10 text-sm text-ink-3">불러오는 중...</div>;
  if (!m) return <div className="p-10 text-sm text-ink-3">case를 찾을 수 없습니다.</div>;

  const canAct = ["proposed", "active", "on_track", "at_risk"].includes(m.status);
  // baseline은 시나리오 §4 K-Petroleum default (Term 60 / Spot 40)으로 강제.
  const target = m.target_pct ?? (m.mission_type === "HEDGE" ? 75 : 70);
  const action = m.mission_type === "HEDGE" ? "Term 비중 (장기 계약)" : "Spot 비중 (즉시 매입)";
  // 위기 강도 10점 만점 (TopBar와 통일)
  const intensityScore = m.pattern_score != null ? Math.round(m.pattern_score / 10) : null;
  const roiEntries = Object.entries(m.simulation_roi || {}).map(
    ([rawKey, value], idx) => [normalizeScenarioLabel(rawKey, idx), value] as [string, number]
  );

  // 현재 운영 mission — 본 mission 외의 가장 최근 active/on_track/at_risk (자기 자신 제외)
  const operatingMission =
    (missionsData?.missions ?? [])
      .filter(
        (x) =>
          x.mission_id !== m.mission_id &&
          ["active", "on_track", "at_risk"].includes(x.status),
      )
      .sort((a, b) =>
        (b.confirmed_at ?? b.created_at).localeCompare(a.confirmed_at ?? a.created_at),
      )[0] ?? null;
  const currentTermPct =
    operatingMission && operatingMission.target_pct != null
      ? operatingMission.mission_type === "HEDGE"
        ? operatingMission.target_pct
        : 100 - operatingMission.target_pct
      : 60;
  const currentSourceLabel = operatingMission
    ? `직전 운영 mission ${operatingMission.created_at.slice(0, 10)} 기록 기준`
    : "회사 평시 기준 (운영 history 없음)";

  return (
    <div className="max-w-3xl px-10 py-10">
      {/* Page overline — cross-page IA 일관성 (DECISION ROOM / MARKET WATCH / INVESTIGATION / CASE FILE) */}
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-2">Case File</div>

      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <MissionTypePill type={m.mission_type} />
        <StatusPill status={m.status} label={statusLabel(m.status)} />
        {m.urgency === "urgent" && (
          <span className="text-[10px] uppercase tracking-wider bg-crisis-500 text-white px-2 py-0.5 rounded">
            긴급
          </span>
        )}
        {m.confirmed_via && (
          <span
            className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded ${
              m.confirmed_via === "slack"
                ? "bg-opportunity-50 text-opportunity-700"
                : "bg-line-1 text-ink-2"
            }`}
            title={`${m.confirmed_via === "slack" ? "Slack" : "Apps"}에서 매니저가 채택`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-opportunity-500" />
            {m.confirmed_via === "slack" ? "Slack 채택" : "Apps 채택"}
          </span>
        )}
        <span className="ml-auto text-[11px] text-ink-3">생성 {formatDate(m.created_at)}</span>
      </div>

      {/* Decision trace — 채택 후 표시 */}
      {m.confirmed_at && (
        <div className="text-[11px] text-ink-3 mb-4 -mt-2">
          <span className="text-ink-2 font-medium">{prettyActor(m.confirmed_by)}</span>이 결정 기록 ·{" "}
          {formatDate(m.confirmed_at)} · {m.confirmed_via === "slack" ? "Slack" : "Apps"} 채널
        </div>
      )}

      <h1 className="font-display text-2xl md:text-3xl font-semibold tracking-tight text-ink-1 mb-2 leading-tight">
        {action} 권고
      </h1>
      <p className="text-sm text-ink-2 leading-relaxed mb-8">{m.reasoning}</p>

      {/* Term/Spot 분할 시각화 — 현재 운영 비중 vs AI 권고 한눈에 */}
      <div className="mb-8 pb-8 border-b border-line-1">
        <MissionSplitBar
          missionType={m.mission_type}
          targetPct={target}
          currentTermPct={currentTermPct}
          currentSourceLabel={currentSourceLabel}
          size="full"
        />
      </div>

      {/* 어제 vs 오늘 권고 변동 narrative — AI Agent self-awareness */}
      {m.delta_vs_previous && (
        <div className="mb-8 pb-8 border-b border-line-1">
          <div className="flex items-baseline justify-between mb-3">
            <div className="text-[11px] uppercase tracking-wider text-ink-3">
              어제 vs 오늘 권고 변동
            </div>
            {m.delta_vs_previous.direction_changed && (
              <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider bg-crisis-500 text-white px-2 py-0.5 rounded">
                방향 전환
              </span>
            )}
          </div>
          <div className="bg-panel border border-line-1 rounded-lg p-5">
            {/* 이전 vs 현재 권고 */}
            <div className="flex items-center gap-3 mb-4 text-[13px]">
              <div className="flex-1">
                <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">
                  어제 ({m.delta_vs_previous.previous_date})
                </div>
                <div className="font-medium text-ink-2">
                  {m.delta_vs_previous.previous_mission_type === "HEDGE"
                    ? "위험방어"
                    : "기회포착"}{" "}
                  · {m.delta_vs_previous.previous_target_pct ?? "—"}%
                </div>
              </div>
              <div className="text-ink-3 text-lg">→</div>
              <div className="flex-1 text-right">
                <div className="text-[10px] uppercase tracking-wider text-ink-3 mb-1">
                  오늘 ({m.created_at.slice(0, 10)})
                </div>
                <div className="font-medium text-ink-1">
                  {m.mission_type === "HEDGE" ? "위험방어" : "기회포착"} · {target}%
                </div>
              </div>
            </div>

            <p className="text-[13px] text-ink-2 leading-relaxed mb-3">
              {m.delta_vs_previous.reason}
            </p>

            {(m.delta_vs_previous.new_signals?.length ?? 0) > 0 && (
              <div className="mb-2">
                <div className="text-[10px] uppercase tracking-wider text-crisis-700 mb-1">
                  + 신규 시그널 (어제는 없었음)
                </div>
                <ul className="space-y-0.5">
                  {m.delta_vs_previous.new_signals.map((s, i) => (
                    <li key={i} className="text-[12px] text-ink-2 pl-3">
                      · {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {(m.delta_vs_previous.weakened_signals?.length ?? 0) > 0 && (
              <div>
                <div className="text-[10px] uppercase tracking-wider text-opportunity-700 mb-1">
                  − 약해진 시그널 (어제는 강했음)
                </div>
                <ul className="space-y-0.5">
                  {m.delta_vs_previous.weakened_signals.map((s, i) => (
                    <li key={i} className="text-[12px] text-ink-2 pl-3">
                      · {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-6 pb-8 mb-8 border-b border-line-1">
        <DetailStat
          label="위기 강도"
          value={intensityScore != null ? `${intensityScore}/10` : "—"}
        />
        <DetailStat label={termSpotLabel(m.mission_type)} value={`${target}%`} />
        <DetailStat label="기간" value={`${m.duration_days}일`} />
      </div>

      {/* ROI scenarios */}
      {roiEntries.length > 0 && (
        <div className="mb-8 pb-8 border-b border-line-1">
          <div className="flex items-baseline justify-between mb-3">
            <div className="text-[11px] uppercase tracking-wider text-ink-3">예상 시나리오</div>
            <span className="text-[10px] text-ink-3 italic">시뮬레이션 · 시연용 예시</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {roiEntries.map(([scenario, roi]) => (
              <div key={scenario} className="bg-panel border border-line-1 rounded-lg p-4">
                <div className="text-xs text-ink-3 mb-1.5">{scenario}</div>
                <div
                  className={`font-display text-xl font-semibold tabular-nums ${
                    roi > 0
                      ? "text-opportunity-700"
                      : roi < 0
                        ? "text-crisis-700"
                        : "text-ink-1"
                  }`}
                >
                  {roi > 0 ? "+" : ""}
                  {roi}억원
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pivot history */}
      {m.pivot_history.length > 0 && (
        <div className="mb-8 pb-8 border-b border-line-1">
          <div className="flex items-baseline justify-between mb-3">
            <div className="text-[11px] uppercase tracking-wider text-ink-3">방향 전환 이력</div>
            <span className="text-[10px] text-ink-3 italic">
              위기 ↔ 기회 양방향 전환 추적
            </span>
          </div>
          <div className="space-y-3">
            {m.pivot_history.map((p, i) => {
              const fromHedge = p.from_type === "HEDGE";
              const toHedge = p.to_type === "HEDGE";
              const intensity =
                p.pattern_score_at != null ? Math.round(p.pattern_score_at / 10) : null;
              return (
                <div
                  key={i}
                  className="bg-panel border border-line-1 rounded-lg p-4"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium ${
                        fromHedge
                          ? "bg-crisis-50 text-crisis-700"
                          : "bg-opportunity-50 text-opportunity-700"
                      }`}
                    >
                      {fromHedge ? "위험방어" : "기회포착"}
                    </span>
                    <span className="text-ink-3" aria-hidden>
                      →
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium ${
                        toHedge
                          ? "bg-crisis-50 text-crisis-700"
                          : "bg-opportunity-50 text-opportunity-700"
                      }`}
                    >
                      {toHedge ? "위험방어" : "기회포착"}
                    </span>
                    <span className="ml-auto text-[10px] text-ink-3">
                      {formatDate(p.occurred_at)}
                      {intensity != null && (
                        <>
                          {" · 위기 강도 "}
                          <span className="font-medium tabular-nums">{intensity}/10</span>
                        </>
                      )}
                    </span>
                  </div>
                  <div className="text-[13px] text-ink-2 leading-relaxed">{p.reason}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 의사결정 chain — AI 권고가 단순 1-click이 아닌 회사 결정 흐름의 input임을 명시 */}
      <DecisionChainPanel mission={m} />

      {/* 매니저의 다음 행동 — codex P0 SuggestedNextActions (6 agentic options) */}
      <SuggestedNextActions mission={m} />

      {/* Agent Bricks 활동 timeline (Lakebase agent_activity_events 실 기록) — codex P0 */}
      <AgentActivityTimeline missionId={m.mission_id} mode="full" />


      {/* Actions */}
      {canAct && !showPivot && !showModify && (
        <div className="flex flex-wrap gap-3">
          {m.status === "proposed" && (
            <>
              <button
                type="button"
                onClick={() =>
                  confirmMut.mutate({ id: m.mission_id, version: m.version })
                }
                disabled={confirmMut.isPending}
                className="px-4 py-2 rounded-md bg-ink-1 text-paper text-[13px] font-medium hover:bg-ink-2 disabled:opacity-50"
              >
                매니저 회부 (검토 시작)
              </button>
              <button
                type="button"
                onClick={() => {
                  setModifyTarget(target);
                  setShowModify(true);
                }}
                className="px-4 py-2 rounded-md border border-line-2 text-ink-1 text-[13px] font-medium hover:bg-line-1"
              >
                조정 후 회부
              </button>
              <button
                type="button"
                onClick={() =>
                  rejectMut.mutate({
                    id: m.mission_id,
                    version: m.version,
                    reason: "매니저 거절",
                  })
                }
                disabled={rejectMut.isPending}
                className="px-4 py-2 rounded-md border border-line-2 text-ink-2 text-[13px] font-medium hover:bg-line-1"
              >
                거절
              </button>
            </>
          )}
          {m.status !== "proposed" && (
            <button
              type="button"
              onClick={() => setShowPivot(true)}
              className="px-4 py-2 rounded-md border border-line-2 text-ink-2 text-[13px] font-medium hover:bg-line-1"
            >
              방향 전환
            </button>
          )}
        </div>
      )}

      {/* Modify form — 매니저가 AI 권고 target_pct를 자기 판단으로 조정 */}
      {showModify && (
        <div className="bg-panel border border-line-1 rounded-lg p-5">
          <div className="text-sm text-ink-1 font-medium mb-1">
            매니저 조정 — {m.mission_type === "HEDGE" ? "Term" : "Spot"} 비중
          </div>
          <div className="text-[12px] text-ink-3 mb-4">
            Supervisor 권고는 {target}%. 매니저 판단으로 조정해서 기록할 수 있습니다.
          </div>

          <div className="flex items-baseline gap-3 mb-3">
            <span className="text-[11px] uppercase tracking-wider text-ink-3 w-16">조정 비중</span>
            <input
              type="range"
              min={m.mission_type === "HEDGE" ? 55 : 45}
              max={m.mission_type === "HEDGE" ? 90 : 90}
              value={modifyTarget ?? target}
              onChange={(e) => setModifyTarget(Number(e.target.value))}
              className="flex-1 accent-ink-1"
            />
            <span className="font-display text-xl font-semibold text-ink-1 tabular-nums w-12 text-right">
              {modifyTarget ?? target}%
            </span>
          </div>

          {modifyTarget != null && modifyTarget !== target && (
            <div className="text-[12px] text-ink-2 mb-3">
              Supervisor 권고 {target}% → 매니저 조정 {modifyTarget}%{" "}
              <span className={modifyTarget < target ? "text-opportunity-700" : "text-crisis-700"}>
                ({modifyTarget > target ? "+" : ""}
                {modifyTarget - target}%p)
              </span>
            </div>
          )}

          <textarea
            value={modifyReason}
            onChange={(e) => setModifyReason(e.target.value)}
            placeholder="조정 사유 (선택) — 예: Supervisor 권고보다 보수적으로, OSP 발표 직후 확정 예정"
            rows={2}
            className="w-full text-sm p-3 border border-line-2 rounded-md focus:outline-none focus:border-ink-3 mb-3 resize-none"
          />

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                const nextTarget = modifyTarget ?? target;
                modifyMut.mutate(
                  {
                    id: m.mission_id,
                    version: m.version,
                    target_pct: nextTarget,
                  },
                  {
                    onSuccess: (updated) => {
                      // modify 성공 시 confirm chain — "조정 후 기록" intent
                      confirmMut.mutate({ id: updated.mission_id, version: updated.version });
                      setShowModify(false);
                      setModifyTarget(null);
                      setModifyReason("");
                    },
                  }
                );
              }}
              disabled={modifyMut.isPending || confirmMut.isPending}
              className="px-4 py-2 rounded-md bg-ink-1 text-paper text-[13px] font-medium hover:bg-ink-2 disabled:opacity-50"
            >
              {modifyMut.isPending || confirmMut.isPending ? "기록 중..." : "조정 후 기록"}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowModify(false);
                setModifyTarget(null);
                setModifyReason("");
              }}
              className="px-4 py-2 rounded-md border border-line-2 text-ink-3 text-[13px]"
            >
              취소
            </button>
          </div>
        </div>
      )}

      {/* Pivot form */}
      {showPivot && (
        <div className="bg-panel border border-line-1 rounded-lg p-5">
          <div className="text-sm text-ink-2 mb-3">
            현재 {missionTypeLabel(m.mission_type)} →{" "}
            {missionTypeLabel(m.mission_type === "HEDGE" ? "OPPORTUNITY" : "HEDGE")}으로 전환
          </div>
          <textarea
            value={pivotReason}
            onChange={(e) => setPivotReason(e.target.value)}
            placeholder="전환 사유 (예: 휴전 임박 + 미국 비축유 방출)"
            rows={2}
            className="w-full text-sm p-3 border border-line-2 rounded-md focus:outline-none focus:border-ink-3 mb-3 resize-none"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() =>
                pivotMut.mutate({
                  id: m.mission_id,
                  version: m.version,
                  pivot_action: "pivot",
                  to_type: m.mission_type === "HEDGE" ? "OPPORTUNITY" : "HEDGE",
                  reason: pivotReason || "방향 전환",
                })
              }
              disabled={pivotMut.isPending || !pivotReason}
              className="px-4 py-2 rounded-md bg-opportunity-500 text-white text-[13px] font-medium hover:bg-opportunity-700 disabled:opacity-50"
            >
              전환 실행
            </button>
            <button
              type="button"
              onClick={() => setShowPivot(false)}
              className="px-4 py-2 rounded-md border border-line-2 text-ink-3 text-[13px]"
            >
              취소
            </button>
          </div>
        </div>
      )}

      {(confirmMut.error || rejectMut.error || pivotMut.error) && (
        <div className="mt-4 text-xs text-crisis-700">요청 처리 중 오류가 발생했습니다.</div>
      )}
    </div>
  );
}

function DetailStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1">{label}</div>
      <div className="font-display text-xl font-semibold text-ink-1 tabular-nums">{value}</div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// DecisionChainPanel — AI 권고가 실제 의사결정 chain의 input임을 명시
//
// 매니저의 의심 풀이: "수십억 결정이 1-click? 진짜 도구인가?"
// 답: 1-click은 trigger. 실제 실행은 매니저 → 데스크 → 위원회 chain 거침.
// ────────────────────────────────────────────────────────────────────────
function DecisionChainPanel({ mission }: { mission: Mission }) {
  // 각 단계 상태 — mission.status에 따라 어디까지 도달했는지 시뮬레이션
  const steps: { label: string; sub: string; state: "done" | "current" | "pending" }[] = [
    {
      label: "Supervisor 권고 생성",
      sub: `Mission Plan (FMA) · ${mission.created_at.slice(0, 10)}`,
      state: "done",
    },
    {
      label: "매니저 회부",
      sub:
        mission.status === "proposed"
          ? "검토 시작 버튼 클릭 대기"
          : mission.confirmed_at
            ? `${mission.confirmed_via === "slack" ? "Slack" : "Apps"} 회부 · ${mission.confirmed_at.slice(0, 10)}`
            : "회부 완료",
      state:
        mission.status === "proposed"
          ? "current"
          : "done",
    },
    {
      label: "트레이딩 데스크 검토",
      sub: "데스크 평가 + Hedging 비용 계산 (1-3일)",
      state:
        mission.status === "proposed"
          ? "pending"
          : ["active", "on_track"].includes(mission.status)
            ? "current"
            : ["pivoted", "completed"].includes(mission.status)
              ? "done"
              : "pending",
    },
    {
      label: "리스크 위원회 승인",
      sub: "수십~수백억 결정 — CFO/COO/CRO chain",
      state:
        mission.status === "proposed"
          ? "pending"
          : ["pivoted", "completed"].includes(mission.status)
            ? "done"
            : "pending",
    },
    {
      label: "실행 (OSP allocation)",
      sub: "Aramco/ADNOC OSP nominee + Spot 매입",
      state: mission.status === "completed" ? "done" : "pending",
    },
  ];

  return (
    <div className="mb-8 pb-8 border-b border-line-1">
      <div className="flex items-baseline justify-between mb-3">
        <div className="text-[11px] uppercase tracking-wider text-ink-3">의사결정 chain</div>
        <span className="text-[10px] text-ink-3">매니저 → 데스크 → 위원회 → 실행</span>
      </div>
      <ol className="space-y-2">
        {steps.map((step, i) => (
          <li
            key={i}
            className={`flex items-baseline gap-3 rounded-md p-2.5 ${
              step.state === "current"
                ? "bg-ink-1/5 border border-ink-1/15"
                : "border border-transparent"
            }`}
          >
            <span
              className={`shrink-0 inline-flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-mono font-semibold tabular-nums ${
                step.state === "done"
                  ? "bg-opportunity-500 text-white"
                  : step.state === "current"
                    ? "bg-ink-1 text-paper"
                    : "bg-line-1 text-ink-3"
              }`}
              aria-label={step.state}
            >
              {step.state === "done" ? "✓" : i + 1}
            </span>
            <div className="flex-1 min-w-0">
              <div
                className={`text-[13px] font-medium ${
                  step.state === "pending" ? "text-ink-3" : "text-ink-1"
                }`}
              >
                {step.label}
              </div>
              <div className="text-[11px] text-ink-3 leading-snug">{step.sub}</div>
            </div>
            {step.state === "current" && (
              <span className="shrink-0 text-[10px] uppercase tracking-wider text-ink-1 font-medium">
                현재 단계
              </span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
