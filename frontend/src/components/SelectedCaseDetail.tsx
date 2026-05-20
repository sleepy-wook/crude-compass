/**
 * SelectedCaseDetail — Decision Room hero right column (slim Mission card).
 *
 * Phase 3 slim refactor — 기존 Dashboard inline MissionSummaryCard 흡수.
 *   - Stat row 제거 (위기 강도 / 기간 / 시뮬레이션)
 *   - Pills: TypePill (solid) + StatusPill (muted variant) + urgency badge
 *   - MissionSplitBar compact
 *   - Reasoning 3줄 (line-clamp-3) — Stat row 자리에 격상
 *   - $ Impact + OSP D-day inline strip (신규)
 *   - Actions: [Approve ▼] primary + [Ask for More Evidence] + [More ▾] overflow
 *   - 상세 (Case File) → 우하단
 */
import { useNavigate, Link } from "react-router-dom";
import { useState } from "react";
import { MissionSplitBar } from "./MissionSplitBar";
import { MissionTypePill } from "./StatusPill";
import {
  useMissionConfirm,
  useMissionModify,
  useMissionPivot,
  useMissionReject,
} from "../lib/queries";
import { cn } from "../lib/utils";
import type { Mission } from "../lib/types";

interface Props {
  mission: Mission | null;
  operatingMission: Mission | null;
  isLoading: boolean;
}

// 현재 운영 비중 helper — mission_type에 따라 Term ratio 환산
function getCurrentTermPct(op: Mission | null): number {
  if (!op || op.target_pct == null) return 60;
  return op.mission_type === "HEDGE" ? op.target_pct : 100 - op.target_pct;
}

// 억원 -> $M (1 USD = 1350 KRW 가정). 시나리오 demo 데이터 단위 = 억 KRW
function okuToUsdM(oku: number): number {
  return (oku * 100_000_000) / 1_350 / 1_000_000;
}

// simulation_roi median 추출 (base scenario)
function getBaseImpactOku(roi: Record<string, number> | null | undefined): number | null {
  if (!roi) return null;
  const values = Object.values(roi).filter((v) => typeof v === "number");
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
}

// OSP D-day — Dashboard와 동일 로직 inline
function getOspDday(): number {
  const today = new Date();
  const day = today.getDate();
  const month = today.getMonth();
  const year = today.getFullYear();
  const lastDay = new Date(year, month + 1, 0).getDate();
  return lastDay - day + 5;
}

export function SelectedCaseDetail({ mission, operatingMission, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="bg-panel border border-line-1 rounded-2xl p-8 flex items-center text-sm text-ink-3 min-h-[420px]">
        불러오는 중...
      </div>
    );
  }

  if (!mission) {
    return (
      <div className="bg-panel border border-line-1 rounded-2xl p-6 min-h-[420px] flex flex-col justify-center">
        <div className="text-[11px] uppercase tracking-wider text-ink-3 mb-2">Case</div>
        <div className="text-base text-ink-1 mb-3">선택된 case 없음</div>
        <p className="text-[13px] text-ink-3 leading-relaxed">
          현재 검토 필요한 case가 없습니다. 시그널 변화 시 좌측 큐에 새 case가 나타납니다.
        </p>
      </div>
    );
  }

  return <CaseDetailBody mission={mission} operatingMission={operatingMission} />;
}

function CaseDetailBody({
  mission,
  operatingMission,
}: {
  mission: Mission;
  operatingMission: Mission | null;
}) {
  const navigate = useNavigate();
  const [moreOpen, setMoreOpen] = useState(false);

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

  const target = mission.target_pct ?? (mission.mission_type === "HEDGE" ? 75 : 70);
  const baseOku = getBaseImpactOku(mission.simulation_roi);
  const baseUsdM = baseOku !== null ? okuToUsdM(baseOku) : null;
  const ospD = getOspDday();

  const onApprove = () => {
    if (isProposed) confirmMut.mutate({ id, version });
  };
  const onAdjust = () => navigate(`/missions/${id}#adjust`);
  const onAskMore = () => navigate(`/ask?case_id=${id}`);
  const onKeepWatching = () =>
    pivotMut.mutate({
      id,
      version,
      pivot_action: "pause",
      reason: "매니저: 모니터링 유지",
    });
  const onRecheckLater = () =>
    modifyMut.mutate({ id, version, duration_days: baseDays + 14 });
  const onDismiss = () => {
    if (isProposed) {
      rejectMut.mutate({ id, version, reason: "매니저 기각" });
    } else if (isActiveLike) {
      pivotMut.mutate({ id, version, pivot_action: "abort", reason: "매니저 종결" });
    }
  };

  const approveDisabled = !isProposed || confirmMut.isPending;
  const askDisabled = isTerminated;

  return (
    <div className="bg-white border border-line-2 rounded-2xl p-6 flex flex-col min-h-[420px] shadow-sm">
      {/* Pills row */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <MissionTypePill type={mission.mission_type} />
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] tracking-wider border font-medium bg-transparent text-ink-3 border-line-2">
          {statusMutedLabel(mission.status)}
        </span>
        {mission.urgency === "urgent" && (
          <span className="text-[10px] uppercase tracking-wider bg-crisis-500 text-white px-2 py-0.5 rounded">
            긴급
          </span>
        )}
        <span className="ml-auto text-[10px] text-ink-3 tabular-nums">
          #{mission.mission_id.slice(0, 6)}
        </span>
      </div>

      {/* MissionSplitBar compact */}
      <div className="mb-5">
        <MissionSplitBar
          missionType={mission.mission_type}
          targetPct={target}
          currentTermPct={getCurrentTermPct(operatingMission)}
          currentSourceLabel={
            operatingMission
              ? `직전 운영 mission ${operatingMission.created_at.slice(0, 10)} 기록 기준`
              : "회사 평시 기준 (운영 history 없음)"
          }
          size="compact"
        />
      </div>

      {/* Reasoning — Stat row 자리에 격상 (3줄 line-clamp) */}
      <p className="text-[13px] text-ink-2 leading-relaxed mb-5 line-clamp-3">
        {mission.reasoning}
      </p>

      {/* $ Impact + OSP D-day inline strip */}
      <div className="flex items-center gap-3 text-[12px] py-2.5 border-y border-line-1 mb-5 flex-wrap">
        {baseUsdM !== null ? (
          <span className="inline-flex items-baseline gap-1.5 text-ink-1">
            <span className="text-[10px] uppercase tracking-wider text-ink-3">예상 절감</span>
            <span className="font-semibold tabular-nums">
              ~${baseUsdM.toFixed(1)}M
            </span>
            <span className="text-ink-3 text-[11px]">(base)</span>
          </span>
        ) : (
          <span className="text-ink-3 text-[11px]">시뮬레이션 미실행</span>
        )}
        <span className="text-line-2" aria-hidden>·</span>
        <span className="inline-flex items-baseline gap-1.5 text-ink-2">
          <span className="text-[10px] uppercase tracking-wider text-ink-3">OSP 결재</span>
          <span className="font-medium tabular-nums">D-{ospD}</span>
        </span>
      </div>

      {/* Actions row */}
      <div className="flex items-center gap-2 mb-4 flex-wrap relative">
        {/* Primary: [Approve ▼] (single button + chevron toggle) */}
        <div className="inline-flex">
          <button
            type="button"
            onClick={onApprove}
            disabled={approveDisabled}
            className={cn(
              "px-3.5 py-2 rounded-l-md text-[12px] font-semibold transition-colors",
              "bg-ink-1 text-paper hover:bg-ink-2 disabled:opacity-40 disabled:cursor-not-allowed",
            )}
          >
            {confirmMut.isPending ? "승인 중..." : "승인"}
          </button>
          <button
            type="button"
            onClick={onAdjust}
            disabled={isTerminated}
            title="조정 — 비중/기간 조정 후 승인"
            className={cn(
              "px-2 py-2 rounded-r-md text-[12px] border-l border-paper/20",
              "bg-ink-1 text-paper hover:bg-ink-2 disabled:opacity-40 disabled:cursor-not-allowed",
            )}
            aria-label="조정"
          >
            ▾
          </button>
        </div>

        {/* Secondary */}
        <button
          type="button"
          onClick={onAskMore}
          disabled={askDisabled}
          className={cn(
            "px-3 py-2 rounded-md text-[12px] font-medium border transition-colors",
            "border-line-2 bg-white text-ink-1 hover:bg-line-1 disabled:opacity-40 disabled:cursor-not-allowed",
          )}
        >
          추가 조사
        </button>

        {/* More overflow */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setMoreOpen((v) => !v)}
            className="px-2.5 py-2 rounded-md text-[12px] font-medium border border-line-2 bg-white text-ink-2 hover:bg-line-1 transition-colors"
          >
            더 보기 ▾
          </button>
          {moreOpen && (
            <div
              role="menu"
              className="absolute left-0 top-full mt-1 w-48 bg-white border border-line-2 rounded-md shadow-md py-1 z-10"
              onMouseLeave={() => setMoreOpen(false)}
            >
              <MenuItem
                label="모니터링 유지"
                onClick={() => {
                  setMoreOpen(false);
                  onKeepWatching();
                }}
                disabled={isTerminated || pivotMut.isPending}
              />
              <MenuItem
                label="재검토 예약"
                onClick={() => {
                  setMoreOpen(false);
                  onRecheckLater();
                }}
                disabled={isTerminated || modifyMut.isPending}
              />
              <MenuItem
                label="기각"
                onClick={() => {
                  setMoreOpen(false);
                  onDismiss();
                }}
                disabled={isTerminated || rejectMut.isPending || pivotMut.isPending}
                danger
              />
            </div>
          )}
        </div>
      </div>

      <div className="mt-auto pt-2 flex justify-end">
        <Link
          to={`/missions/${mission.mission_id}`}
          className="inline-flex items-center gap-1.5 text-[12px] text-ink-3 hover:text-ink-1 transition-colors"
        >
          상세 보기 <span aria-hidden>→</span>
        </Link>
      </div>
    </div>
  );
}

function MenuItem({
  label,
  onClick,
  disabled,
  danger,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "w-full text-left px-3 py-1.5 text-[12px] transition-colors",
        "hover:bg-line-1 disabled:opacity-40 disabled:cursor-not-allowed",
        danger ? "text-crisis-700" : "text-ink-1",
      )}
    >
      {label}
    </button>
  );
}

// Status pill을 hero에서는 톤 격하 (outline ink-3) — 기존 StatusPill solid 변형 대신 muted label만.
// label은 statusLabel()과 매핑 동일하게 유지.
function statusMutedLabel(status: string): string {
  // re-use shared status→label (StatusPill uses statusLabel internally; we just need text here)
  const map: Record<string, string> = {
    proposed: "검토 대기",
    active: "진행 중",
    on_track: "정상",
    at_risk: "주의",
    paused: "모니터링",
    pivoted: "재편됨",
    aborted: "기각",
    completed: "완료",
  };
  return map[status] || status;
}
