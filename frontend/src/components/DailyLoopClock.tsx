/**
 * DailyLoopClock — 24h 원형 dial. 매 시간 어떤 job이 돌았는지 시각화.
 *
 * 외곽: 시계 face (24h, 0~24)
 * 안쪽: job run dots — start_time을 각도로 매핑
 * 하단: 누적 통계 strip
 */
import { useJobRunsToday } from "../lib/queries";

export function DailyLoopClock() {
  const { data, isLoading, isError } = useJobRunsToday();

  if (isLoading) return <div className="text-[11px] text-ink-3 p-4">불러오는 중...</div>;
  if (isError || !data) return <div className="text-[11px] text-ink-3 p-4">불러올 수 없습니다</div>;

  const { runs, summary } = data;
  const size = 240;
  const cx = size / 2, cy = size / 2;
  const rOuter = 110, rInner = 80;
  const now = new Date();
  const nowAngle = ((now.getHours() + now.getMinutes() / 60) / 24) * 360 - 90;

  return (
    <section className="bg-white rounded-lg border border-line-2 p-3">
      <header className="text-[11px] font-semibold text-ink mb-2">Daily AI Loop</header>
      <div className="flex flex-col items-center">
        <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[260px]">
          {/* 24 hour ticks */}
          {Array.from({ length: 24 }, (_, h) => {
            const a = (h / 24) * 360 - 90;
            const rad = (a * Math.PI) / 180;
            const x1 = cx + Math.cos(rad) * (rOuter - 4);
            const y1 = cy + Math.sin(rad) * (rOuter - 4);
            const x2 = cx + Math.cos(rad) * rOuter;
            const y2 = cy + Math.sin(rad) * rOuter;
            return (
              <line key={h} x1={x1} y1={y1} x2={x2} y2={y2} stroke="currentColor" strokeWidth="1" className="text-line-2" />
            );
          })}

          {/* job run dots */}
          {runs.map((r) => {
            if (!r.start_time) return null;
            const d = new Date(r.start_time);
            const hr = d.getHours() + d.getMinutes() / 60;
            const a = (hr / 24) * 360 - 90;
            const rad = (a * Math.PI) / 180;
            const rDot = rInner + (jobRadiusOffset(r.job_name) * 6);
            const x = cx + Math.cos(rad) * rDot;
            const y = cy + Math.sin(rad) * rDot;
            const fill = r.result_state === "SUCCESS" ? "rgb(16 185 129)" : "rgb(239 68 68)";
            return <circle key={r.run_id} cx={x} cy={y} r={2} fill={fill} />;
          })}

          {/* now hand */}
          {(() => {
            const rad = (nowAngle * Math.PI) / 180;
            const x = cx + Math.cos(rad) * (rOuter - 8);
            const y = cy + Math.sin(rad) * (rOuter - 8);
            return <line x1={cx} y1={cy} x2={x} y2={y} stroke="currentColor" strokeWidth="1.5" className="text-ink" />;
          })()}

          {/* center */}
          <circle cx={cx} cy={cy} r={3} fill="currentColor" className="text-ink" />
        </svg>

        {/* summary strip */}
        <div className="grid grid-cols-3 gap-2 w-full mt-3 text-[10px]">
          {Object.entries(summary).slice(0, 9).map(([k, v]) => (
            <div key={k} className="bg-base-paper rounded p-1.5 border border-line-2">
              <div className="text-ink-3 truncate">{k}</div>
              <div className="text-ink font-semibold">{v.count}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// job별 ring offset (0~3) — 같은 시간에 여러 job 겹치는 것 방지
const JOB_RING: Record<string, number> = {
  "gdelt-15min": 0,
  "price-pipeline": 1,
  "daily-curation": 2,
  "oil-prices-daily": 2,
  "ecos-daily": 2,
  "eia-weekly": 3,
  "opec-momr": 3,
};

function jobRadiusOffset(jobName: string): number {
  return JOB_RING[jobName] ?? 3;
}
