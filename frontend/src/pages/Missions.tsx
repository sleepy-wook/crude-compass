import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { MissionTypePill, StatusPill } from "../components/StatusPill";
import { Term } from "../components/Glossary";
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
  missionTypeLabel,
  relativeTime,
  statusLabel,
} from "../lib/utils";

export function MissionsList() {
  const { data, isLoading } = useMissionsActive();
  const missions = data?.missions || [];
  return (
    <div className="max-w-5xl mx-auto">
      <header className="mb-6">
        <h1 className="font-display text-3xl font-semibold">진행 중 미션</h1>
        <p className="text-sm text-ink-3 mt-1">
          AI가 제안한 매입 비중 조정 — Slack 또는 Apps에서 승인하면 5초 안에 양쪽 동기화
        </p>
      </header>
      {isLoading && <div className="text-ink-3">로딩 중...</div>}
      <div className="space-y-3">
        {missions.map((m, i) => (
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
              <span>
                {/* 첫 카드에만 Tooltip 노출 — 도배 방지. position=bottom: 카드 첫 줄이라 잘림 방지 */}
                {i === 0 ? (
                  <Term name="PATTERN_SCORE" position="bottom">위기 신호 점수</Term>
                ) : (
                  "위기 신호 점수"
                )}{" "}
                {formatScore(m.pattern_score)}
              </span>
              {m.target_pct !== null && (
                <span>
                  {m.mission_type === "HEDGE" ? "Term" : "Spot"} {m.target_pct}%
                </span>
              )}
              <span>{m.duration_days}일</span>
              {m.pivot_history.length > 0 && (
                <span className="text-opportunity-700">
                  {m.pivot_history.length}회 방향 전환
                </span>
              )}
            </div>
          </Link>
        ))}
        {missions.length === 0 && (
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
          <Field
            label={<Term name="PATTERN_SCORE" position="bottom">위기 신호 점수</Term>}
            value={formatScore(m.pattern_score)}
          />
          <Field
            label={m.mission_type === "HEDGE" ? "장기계약 목표" : "즉시구매 목표"}
            value={m.target_pct !== null ? `${m.target_pct}%` : "—"}
          />
          <Field label="기간" value={`${m.duration_days}일`} />
          <Field
            label="미션 ID"
            value={m.mission_id.slice(0, 8)}
            mono
          />
        </div>
      </header>

      {/* Simulation ROI */}
      {Object.keys(m.simulation_roi || {}).length > 0 && (
        <section className="mb-6 bg-panel rounded-xl border border-line-1 p-6">
          <h2 className="text-xs uppercase tracking-widest text-ink-3 mb-3">
            시뮬레이션 — 시나리오별 절감액 (단위: 억원)
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
            방향 전환 이력
          </h2>
          <div className="space-y-3">
            {m.pivot_history.map((p, i) => (
              <div key={i} className="border-l-2 border-opportunity-500 pl-3 py-1">
                <div className="text-xs font-mono text-ink-3 mb-1">
                  {formatDate(p.occurred_at)} · 위기점수 {formatScore(p.pattern_score_at)}
                </div>
                <div className="text-sm">
                  <strong>{missionTypeLabel(p.from_type)}</strong> →{" "}
                  <strong>{missionTypeLabel(p.to_type)}</strong>
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
                  방향 전환
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-sm text-ink-2">
                방향 전환 — {missionTypeLabel(m.mission_type)} →{" "}
                <strong>
                  {missionTypeLabel(m.mission_type === "HEDGE" ? "OPPORTUNITY" : "HEDGE")}
                </strong>
              </div>
              <textarea
                value={pivotReason}
                onChange={(e) => setPivotReason(e.target.value)}
                placeholder="방향 전환 사유 (예: 휴전 임박 + 미국 비축유 방출 같은 약세 시그널)"
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
                      reason: pivotReason || "방향 전환",
                    })
                  }
                  disabled={pivotMut.isPending || !pivotReason}
                  className="px-4 py-2 rounded-md bg-opportunity-500 text-white text-sm font-medium hover:bg-opportunity-700 disabled:opacity-50"
                >
                  방향 전환 실행
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
  label: React.ReactNode;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="text-[10px] text-ink-3 mb-1">{label}</div>
      <div className={`text-sm font-medium ${mono ? "font-mono" : ""}`}>
        {value}
      </div>
    </div>
  );
}
