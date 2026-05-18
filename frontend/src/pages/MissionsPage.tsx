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
  useMissionPivot,
  useMissionReject,
} from "../lib/queries";
import { MissionSplitBar } from "../components/MissionSplitBar";
import { MissionTypePill, StatusPill } from "../components/StatusPill";
import {
  formatDate,
  missionTypeLabel,
  normalizeScenarioLabel,
  relativeTime,
  statusLabel,
  termSpotLabel,
} from "../lib/utils";
type Filter = "all" | "active" | "proposed";

export function MissionsPage() {
  const { id: routeId } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const { data, isLoading } = useMissionsActive();
  const missions = data?.missions || [];
  const [filter, setFilter] = useState<Filter>("all");
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
    if (filter === "active") return ["active", "on_track", "at_risk"].includes(m.status);
    if (filter === "proposed") return m.status === "proposed";
    return true;
  });

  return (
    <div className="flex h-[calc(100vh-56px)]">
      {/* Left — list */}
      <div className="w-[380px] border-r border-line-1 flex flex-col">
        {/* Page header */}
        <div className="px-6 py-5 border-b border-line-1">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-3 mb-1.5">내 결정</div>
          <h1 className="font-display text-xl font-semibold text-ink-1 mb-1">매니저 결정 기록</h1>
          <p className="text-[11px] text-ink-3 mb-3 leading-snug">
            AI가 결정하지 않습니다. 매니저가 기록 — 시장 메모리로 누적됩니다.
          </p>
          {/* Filter tabs */}
          <div className="flex gap-1 text-[12px]">
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
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading && <div className="p-6 text-sm text-ink-3">불러오는 중...</div>}
          {!isLoading && filtered.length === 0 && (
            <div className="p-6 text-sm text-ink-3">해당 상태의 임무가 없습니다.</div>
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
          모든 임무는 Slack에서도 채택/거절/방향 전환할 수 있습니다.
        </div>
      </div>

      {/* Right — detail */}
      <div className="flex-1 overflow-y-auto">
        {selectedId ? (
          <MissionDetail missionId={selectedId} />
        ) : (
          <div className="h-full flex items-center justify-center text-sm text-ink-3">
            왼쪽에서 임무를 선택하세요.
          </div>
        )}
      </div>
    </div>
  );
}

function MissionDetail({ missionId }: { missionId: string }) {
  const { data: m, isLoading } = useMission(missionId);
  const confirmMut = useMissionConfirm();
  const rejectMut = useMissionReject();
  const pivotMut = useMissionPivot();
  const [showPivot, setShowPivot] = useState(false);
  const [pivotReason, setPivotReason] = useState("");

  if (isLoading) return <div className="p-10 text-sm text-ink-3">불러오는 중...</div>;
  if (!m) return <div className="p-10 text-sm text-ink-3">임무를 찾을 수 없습니다.</div>;

  const canAct = ["proposed", "active", "on_track", "at_risk"].includes(m.status);
  // baseline은 시나리오 §4 K-Petroleum default (Term 60 / Spot 40)으로 강제.
  const target = m.target_pct ?? (m.mission_type === "HEDGE" ? 75 : 70);
  const action = m.mission_type === "HEDGE" ? "Term 비중 (장기 계약)" : "Spot 비중 (즉시 매입)";
  // 위기 강도 10점 만점 (TopBar와 통일)
  const intensityScore = m.pattern_score != null ? Math.round(m.pattern_score / 10) : null;
  const roiEntries = Object.entries(m.simulation_roi || {}).map(
    ([rawKey, value], idx) => [normalizeScenarioLabel(rawKey, idx), value] as [string, number]
  );

  return (
    <div className="max-w-3xl px-10 py-10">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <MissionTypePill type={m.mission_type} />
        <StatusPill status={m.status} label={statusLabel(m.status)} />
        {m.urgency === "urgent" && (
          <span className="text-[10px] uppercase tracking-wider bg-crisis-500 text-white px-2 py-0.5 rounded">
            긴급
          </span>
        )}
        <span className="ml-auto text-[11px] text-ink-3">생성 {formatDate(m.created_at)}</span>
      </div>

      <h1 className="font-display text-2xl md:text-3xl font-semibold tracking-tight text-ink-1 mb-2 leading-tight">
        {action} 권고
      </h1>
      <p className="text-sm text-ink-2 leading-relaxed mb-8">{m.reasoning}</p>

      {/* Term/Spot 분할 시각화 — 평시 baseline vs AI 권고 한눈에 */}
      <div className="mb-8 pb-8 border-b border-line-1">
        <MissionSplitBar
          missionType={m.mission_type}
          targetPct={target}
          size="full"
        />
      </div>

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
          <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-3">방향 전환 이력</div>
          <div className="space-y-3">
            {m.pivot_history.map((p, i) => (
              <div key={i} className="text-sm">
                <div className="text-xs text-ink-3 mb-0.5">
                  {formatDate(p.occurred_at)} · 위기 강도{" "}
                  {p.pattern_score_at != null ? Math.round(p.pattern_score_at / 10) : "—"}/10
                </div>
                <div className="text-ink-1">
                  {missionTypeLabel(p.from_type)} → {missionTypeLabel(p.to_type)}
                </div>
                <div className="text-xs text-ink-2 mt-0.5">{p.reason}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      {canAct && !showPivot && (
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
                내 결정으로 기록
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
              className="px-4 py-2 rounded-md bg-opportunity-600 text-white text-[13px] font-medium hover:bg-opportunity-700 disabled:opacity-50"
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
