/**
 * SuggestedNextActions — codex P0 신규 컴포넌트.
 *
 * Goal: binary approve/reject 구도 탈피 → 6 agent-like next actions panel.
 *       recommendation workflow → agentic workflow 인상 전환의 2번째 장치.
 *
 * 6 actions (모두 기존 endpoint 재사용, backend 신규 X):
 *   1. Approve Draft         → useMissionConfirm
 *   2. Adjust Draft          → /missions/:id (modify dialog open)
 *   3. Dismiss Case          → useMissionReject (proposed) / useMissionPivot(abort) (active)
 *   4. Keep Watching         → useMissionModify (duration_days +7)
 *   5. Ask for More Evidence → navigate /ask?case_id=...  (AskPage가 mission_id 자동 주입)
 *   6. Re-check Later        → useMissionModify (duration_days +14)
 *
 * 각 action 직후 agent_activity_events table에 manager:* event 기록됨 (backend hook).
 * UI는 그 결과를 useMissionActivity가 30s polling으로 자동 반영.
 *
 * mission status에 따라 일부 action disable.
 */
import { useNavigate } from "react-router-dom";
import {
  useMissionConfirm,
  useMissionModify,
  useMissionPivot,
  useMissionReject,
} from "../lib/queries";
import { cn } from "../lib/utils";
import type { Mission } from "../lib/types";

type ActionDef = {
  key: string;
  label: string;
  desc: string;
  /** primary = 강조 (Approve 등). neutral = 일반. */
  variant: "primary" | "neutral" | "danger";
  disabled?: boolean;
  loading?: boolean;
  handler: () => void;
};

export function SuggestedNextActions({
  mission,
  compact = false,
}: {
  mission: Mission;
  compact?: boolean;
}) {
  const navigate = useNavigate();
  const confirmMut = useMissionConfirm();
  const modifyMut = useMissionModify();
  const rejectMut = useMissionReject();
  const pivotMut = useMissionPivot();

  const id = mission.mission_id;
  const version = mission.version;
  const isProposed = mission.status === "proposed";
  const isActiveLike = ["active", "on_track", "at_risk"].includes(mission.status);
  const isTerminated = ["aborted", "completed"].includes(mission.status);

  const baseDays = mission.duration_days ?? 28;

  const dismissHandler = () => {
    if (isProposed) {
      rejectMut.mutate({ id, version, reason: "매니저 기각" });
    } else if (isActiveLike) {
      pivotMut.mutate({
        id,
        version,
        pivot_action: "abort",
        reason: "매니저 종결",
      });
    }
  };

  const actions: ActionDef[] = [
    {
      key: "approve",
      label: "Approve Draft",
      desc: "권고 그대로 승인 → active 전환",
      variant: "primary",
      disabled: !isProposed || confirmMut.isPending,
      loading: confirmMut.isPending,
      handler: () => confirmMut.mutate({ id, version }),
    },
    {
      key: "adjust",
      label: "Adjust Draft",
      desc: "비중/기간 조정 후 승인",
      variant: "neutral",
      disabled: isTerminated,
      handler: () => navigate(`/missions/${id}#adjust`),
    },
    {
      key: "dismiss",
      label: "Dismiss Case",
      desc: isProposed ? "권고 기각" : "case 종결",
      variant: "danger",
      disabled: isTerminated || rejectMut.isPending || pivotMut.isPending,
      loading: rejectMut.isPending || pivotMut.isPending,
      handler: dismissHandler,
    },
    {
      key: "keep_watching",
      label: "Keep Watching",
      desc: "권고 보류 — paused 상태로 모니터링만",
      variant: "neutral",
      disabled: isTerminated || pivotMut.isPending,
      loading: pivotMut.isPending,
      // pivot:pause → status='paused' (mission 자체는 active 안 되지만 시그널 계속 추적)
      handler: () =>
        pivotMut.mutate({
          id,
          version,
          pivot_action: "pause",
          reason: "매니저: 모니터링 유지 (수동 보류)",
        }),
    },
    {
      key: "ask_more",
      label: "Ask for More Evidence",
      desc: "Investigation으로 진입",
      variant: "neutral",
      disabled: isTerminated,
      handler: () => navigate(`/ask?case_id=${id}`),
    },
    {
      key: "recheck_later",
      label: "Re-check Later",
      desc: `${baseDays + 14}일 후 재검토 (기간 연장)`,
      variant: "neutral",
      disabled: isTerminated || modifyMut.isPending,
      loading: modifyMut.isPending,
      // modify:duration_days 연장 → status는 그대로 (방어 권고 active 유지)
      handler: () =>
        modifyMut.mutate({ id, version, duration_days: baseDays + 14 }),
    },
  ];

  return (
    <section
      className={cn(
        "bg-white border border-line-2 rounded-lg",
        compact ? "p-3" : "p-4",
      )}
    >
      {!compact && (
        <div className="mb-3">
          <h3 className="text-[13px] font-semibold text-ink tracking-tight">
            매니저의 다음 행동
          </h3>
          <p className="text-[10px] text-ink-3 mt-0.5">
            Supervisor가 현재 시그널 강도 기반으로 추천한 6가지 — approve 외에도 추가 조사 / 모니터링 /
            재검토 등 매니저가 1건 선택
          </p>
        </div>
      )}
      {compact && (
        <div className="mb-2">
          <h4 className="text-[11px] font-semibold text-ink-2 tracking-tight">
            Supervisor 권고 — 다음 행동 6가지
          </h4>
        </div>
      )}
      <div
        className={cn(
          "grid gap-2",
          compact ? "grid-cols-2 md:grid-cols-3" : "grid-cols-2 md:grid-cols-3",
        )}
      >
        {actions.map((a) => (
          <ActionChip key={a.key} def={a} />
        ))}
      </div>
    </section>
  );
}

function ActionChip({ def }: { def: ActionDef }) {
  const variantCls = {
    primary:
      "border-ink-1 bg-ink-1 text-paper hover:bg-ink-2 disabled:opacity-40",
    neutral:
      "border-line-2 bg-white text-ink-1 hover:bg-line-1 disabled:opacity-40",
    danger:
      "border-crisis-100 bg-white text-crisis-700 hover:bg-crisis-50 disabled:opacity-40",
  }[def.variant];

  return (
    <button
      type="button"
      onClick={def.handler}
      disabled={def.disabled}
      title={def.desc}
      className={cn(
        "text-left px-3 py-2 border rounded-md transition-colors disabled:cursor-not-allowed",
        variantCls,
      )}
    >
      <div className="text-[12px] font-semibold leading-tight">
        {def.loading ? "처리 중..." : def.label}
      </div>
      <div
        className={cn(
          "text-[10px] mt-0.5 leading-snug",
          def.variant === "primary" ? "text-paper opacity-80" : "text-ink-3",
        )}
      >
        {def.desc}
      </div>
    </button>
  );
}
