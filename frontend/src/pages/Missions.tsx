import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { MissionTypePill, StatusPill } from "../components/StatusPill";
import {
  useMission,
  useMissionConfirm,
  useMissionPivot,
  useMissionReject,
  useMissionsActive,
} from "../lib/queries";
import {
  formatDate,
  formatScore,
  relativeTime,
  statusLabel,
} from "../lib/utils";

export function MissionsList() {
  const { data, isLoading } = useMissionsActive();
  return (
    <div className="max-w-5xl mx-auto">
      <header className="mb-6">
        <div className="text-xs uppercase tracking-widest text-ink-3 mb-1">Missions</div>
        <h1 className="font-display text-3xl font-semibold">진행 중 미션</h1>
      </header>
      {isLoading && <div className="text-ink-3">로딩 중...</div>}
      <div className="space-y-3">
        {(data?.missions || []).map((m) => (
          <Link
            key={m.mission_id}
            to={`/missions/${m.mission_id}`}
            className="block bg-panel rounded-xl border border-line-1 p-5 hover:border-ink-3 transition-colors"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex gap-2 items-center">
                <MissionTypePill type={m.mission_type} />
                <StatusPill status={m.status} label={statusLabel(m.status)} />
                {m.urgency === "urgent" && (
                  <span className="text-[10px] uppercase tracking-wider bg-crisis-500 text-white px-2 py-0.5 rounded-full">
                    Urgent
                  </span>
                )}
              </div>
              <span className="text-[11px] font-mono text-ink-3">
                v{m.version} · {relativeTime(m.created_at)}
              </span>
            </div>
            <div className="font-medium text-ink mb-1">{m.goal_text}</div>
            <div className="text-sm text-ink-3 line-clamp-2">{m.reasoning}</div>
            <div className="mt-3 flex gap-4 text-xs font-mono text-ink-3">
              <span>Pattern Score {formatScore(m.pattern_score)}</span>
              {m.target_pct !== null && <span>target {m.target_pct}%</span>}
              <span>{m.duration_days}일</span>
              {m.pivot_history.length > 0 && (
                <span className="text-opportunity-700">{m.pivot_history.length}회 pivot</span>
              )}
            </div>
          </Link>
        ))}
        {data?.missions?.length === 0 && (
          <div className="bg-panel rounded-lg border border-line-1 p-8 text-center text-ink-3">
            현재 진행 중 미션 없음
          </div>
        )}
      </div>
    </div>
  );
}

export function MissionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: m, isLoading } = useMission(id);
  const confirmMut = useMissionConfirm();
  const rejectMut = useMissionReject();
  const pivotMut = useMissionPivot();

  const [pivotReason, setPivotReason] = useState("");
  const [showPivot, setShowPivot] = useState(false);

  if (isLoading) return <div className="text-ink-3 p-8">로딩 중...</div>;
  if (!m) return <div className="text-ink-3 p-8">미션을 찾을 수 없습니다.</div>;

  const canAct =
    m.status === "proposed" || m.status === "active" || m.status === "on_track";

  return (
    <div className="max-w-4xl mx-auto">
      <button
        onClick={() => navigate("/missions")}
        className="text-xs text-ink-3 hover:text-ink mb-4 inline-flex items-center gap-1"
      >
        ← 미션 목록
      </button>

      <header className="mb-6 bg-panel rounded-xl border border-line-1 p-6">
        <div className="flex items-center gap-2 mb-3">
          <MissionTypePill type={m.mission_type} />
          <StatusPill status={m.status} label={statusLabel(m.status)} />
          {m.urgency === "urgent" && (
            <span className="text-[10px] uppercase tracking-wider bg-crisis-500 text-white px-2 py-0.5 rounded-full">
              Urgent
            </span>
          )}
          <span className="ml-auto text-[11px] font-mono text-ink-3">
            v{m.version} · 생성 {formatDate(m.created_at)}
          </span>
        </div>
        <h1 className="font-display text-2xl font-semibold mb-2">{m.goal_text}</h1>
        <p className="text-sm text-ink-2 leading-relaxed">{m.reasoning}</p>

        <div className="mt-5 grid grid-cols-4 gap-4">
          <Field label="Pattern Score" value={formatScore(m.pattern_score)} />
          <Field
            label="Target"
            value={m.target_pct !== null ? `${m.target_pct}%` : "—"}
          />
          <Field label="Duration" value={`${m.duration_days}일`} />
          <Field
            label="Mission ID"
            value={m.mission_id.slice(0, 8)}
            mono
          />
        </div>
      </header>

      {/* Simulation ROI */}
      {Object.keys(m.simulation_roi || {}).length > 0 && (
        <section className="mb-6 bg-panel rounded-xl border border-line-1 p-6">
          <h2 className="text-xs uppercase tracking-widest text-ink-3 mb-3">
            시뮬레이션 — 시나리오별 ROI
          </h2>
          <div className="grid grid-cols-3 gap-3">
            {Object.entries(m.simulation_roi).map(([scenario, roi]) => (
              <div
                key={scenario}
                className="border border-line-1 rounded-md p-3 bg-paper"
              >
                <div className="text-xs text-ink-3 mb-1">{scenario}</div>
                <div
                  className={`font-display text-xl font-semibold ${
                    roi > 0 ? "text-opportunity-700" : roi < 0 ? "text-crisis-700" : "text-ink"
                  }`}
                >
                  {roi > 0 ? "+" : ""}
                  {roi}억
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Pivot History */}
      {m.pivot_history.length > 0 && (
        <section className="mb-6 bg-panel rounded-xl border border-line-1 p-6">
          <h2 className="text-xs uppercase tracking-widest text-ink-3 mb-3">
            Pivot 이력
          </h2>
          <div className="space-y-3">
            {m.pivot_history.map((p, i) => (
              <div key={i} className="border-l-2 border-opportunity-500 pl-3 py-1">
                <div className="text-xs font-mono text-ink-3 mb-1">
                  {formatDate(p.occurred_at)} · PS {formatScore(p.pattern_score_at)}
                </div>
                <div className="text-sm">
                  <strong>{p.from_type}</strong> → <strong>{p.to_type}</strong>
                </div>
                <div className="text-xs text-ink-2 mt-1">{p.reason}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Action Buttons */}
      {canAct && (
        <section className="bg-panel rounded-xl border border-line-1 p-6">
          <h2 className="text-xs uppercase tracking-widest text-ink-3 mb-4">의사결정</h2>

          {!showPivot ? (
            <div className="flex gap-3 flex-wrap">
              <button
                onClick={() =>
                  confirmMut.mutate({ id: m.mission_id, version: m.version })
                }
                disabled={confirmMut.isPending || m.status === "active"}
                className="px-4 py-2 rounded-md bg-crisis-500 text-white text-sm font-medium hover:bg-crisis-700 disabled:opacity-50"
              >
                {m.status === "active" ? "이미 승인됨" : "승인 (Confirm)"}
              </button>
              <button
                onClick={() =>
                  rejectMut.mutate({
                    id: m.mission_id,
                    version: m.version,
                    reason: "manager rejected",
                  })
                }
                disabled={rejectMut.isPending}
                className="px-4 py-2 rounded-md border border-line-2 text-ink-2 text-sm font-medium hover:bg-line-1 disabled:opacity-50"
              >
                거절
              </button>
              {m.status !== "proposed" && (
                <button
                  onClick={() => setShowPivot(true)}
                  className="px-4 py-2 rounded-md border border-opportunity-500 text-opportunity-700 text-sm font-medium hover:bg-opportunity-50"
                >
                  Pivot
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-sm text-ink-2">
                Pivot — {m.mission_type} →{" "}
                <strong>{m.mission_type === "HEDGE" ? "OPPORTUNITY" : "HEDGE"}</strong>
              </div>
              <textarea
                value={pivotReason}
                onChange={(e) => setPivotReason(e.target.value)}
                placeholder="Pivot 사유 (예: 휴전 임박 + SPR 방출 + PMI 49.2)"
                rows={3}
                className="w-full text-sm p-3 border border-line-2 rounded-md focus:outline-none focus:border-ink-3"
              />
              <div className="flex gap-2">
                <button
                  onClick={() =>
                    pivotMut.mutate({
                      id: m.mission_id,
                      version: m.version,
                      pivot_action: "pivot",
                      to_type:
                        m.mission_type === "HEDGE" ? "OPPORTUNITY" : "HEDGE",
                      reason: pivotReason || "Pivot",
                    })
                  }
                  disabled={pivotMut.isPending || !pivotReason}
                  className="px-4 py-2 rounded-md bg-opportunity-500 text-white text-sm font-medium hover:bg-opportunity-700 disabled:opacity-50"
                >
                  Pivot 실행
                </button>
                <button
                  onClick={() => setShowPivot(false)}
                  className="px-4 py-2 rounded-md border border-line-2 text-ink-3 text-sm hover:bg-line-1"
                >
                  취소
                </button>
              </div>
            </div>
          )}

          {(confirmMut.error || rejectMut.error || pivotMut.error) && (
            <div className="mt-3 text-xs text-crisis-700">
              에러:{" "}
              {confirmMut.error?.message ||
                rejectMut.error?.message ||
                pivotMut.error?.message}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-ink-3 mb-1">
        {label}
      </div>
      <div className={`text-sm font-medium ${mono ? "font-mono" : ""}`}>
        {value}
      </div>
    </div>
  );
}
