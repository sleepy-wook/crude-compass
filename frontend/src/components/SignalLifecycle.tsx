/**
 * SignalLifecycle — 4-stage forensic view of a single signal.
 *
 * Stage 1: Detected (bronze.news_articles row — title/source/published_at)
 * Stage 2: Scored (importance/direction/horizon/confidence)
 * Stage 3: Decay (silver.signal_events_decayed SVG sparkline)
 * Stage 4: Contribution (gold.signal_contribution_30d + referenced cases)
 */
import { Link } from "react-router-dom";
import { useSignalLifecycle } from "../lib/queries";

export function SignalLifecycle({ signalId }: { signalId: string | undefined }) {
  const { data, isLoading, isError } = useSignalLifecycle(signalId);

  if (!signalId) {
    return (
      <div className="text-[11px] text-ink-3 p-4">
        Live Pulse에서 [GDELT] 항목을 클릭하면 그 시그널의 lifecycle을 추적합니다.
      </div>
    );
  }
  if (isLoading) return <div className="text-[11px] text-ink-3 p-4">불러오는 중...</div>;
  if (isError || !data) return <div className="text-[11px] text-ink-3 p-4">불러올 수 없습니다</div>;

  const { stages } = data;

  return (
    <section className="space-y-4">
      {/* Stage 1 — Detected */}
      <Stage num={1} title="Detected">
        {stages.detected ? (
          <div className="text-[11px]">
            <div className="font-medium text-ink-1">{String(stages.detected.title ?? "(제목 없음)")}</div>
            <div className="text-ink-3 mt-1">
              {String(stages.detected.source ?? "")} · {String(stages.detected.published_at ?? "")}
            </div>
          </div>
        ) : (
          <Empty />
        )}
      </Stage>

      {/* Stage 2 — Scored */}
      <Stage num={2} title="Scored by LLM">
        {stages.scored ? (
          <div className="grid grid-cols-4 gap-2 text-[11px]">
            <Kv k="importance" v={stages.scored.importance} />
            <Kv k="direction" v={stages.scored.direction} />
            <Kv k="horizon" v={stages.scored.horizon} />
            <Kv k="confidence" v={stages.scored.confidence} />
          </div>
        ) : (
          <Empty />
        )}
      </Stage>

      {/* Stage 3 — Decay */}
      <Stage num={3} title="Decay (time-weighted)">
        {stages.decay.length > 0 ? (
          <DecayChart points={stages.decay} />
        ) : (
          <Empty msg="감쇠 데이터 없음 (검출된 지 24h 미만)" />
        )}
      </Stage>

      {/* Stage 4 — Contribution */}
      <Stage num={4} title="Contribution (30-day cumulative)">
        {stages.contribution ? (
          <div className="text-[11px] space-y-1">
            <div>
              총 누적:{" "}
              <span className="font-semibold">
                {stages.contribution.total_contribution.toFixed(2)}
              </span>
            </div>
            <div>
              피크: {stages.contribution.peak_contribution.toFixed(2)} ({stages.contribution.peak_date})
            </div>
            <div className="pt-1">
              참고된 case ({stages.contribution.referenced_case_ids.length}):
              <ul className="mt-1 space-y-0.5">
                {stages.contribution.referenced_case_ids.map((cid) => (
                  <li key={cid}>
                    <Link
                      to={`/missions?id=${cid}`}
                      className="text-opportunity-700 hover:underline"
                    >
                      {cid}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          <Empty msg="아직 case 참고 이력 없음" />
        )}
      </Stage>
    </section>
  );
}

function Stage({
  num,
  title,
  children,
}: {
  num: number;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-lg border border-line-2 p-3">
      <div className="text-[10px] text-ink-3 font-semibold tracking-wide mb-2">
        STAGE {num} · {title}
      </div>
      {children}
    </div>
  );
}

function Kv({ k, v }: { k: string; v: unknown }) {
  return (
    <div>
      <div className="text-[9px] text-ink-3 uppercase">{k}</div>
      <div className="text-ink-1 font-medium">{v == null ? "—" : String(v)}</div>
    </div>
  );
}

function Empty({ msg = "데이터 없음" }: { msg?: string }) {
  return <div className="text-[11px] text-ink-3 italic">{msg}</div>;
}

function DecayChart({ points }: { points: Array<{ as_of_date: string; weight: number }> }) {
  // 간단 SVG sparkline — Recharts 없이 (5/19 결정: Recharts X)
  if (points.length === 0) return null;
  const w = 320;
  const h = 80;
  const pad = 4;
  const maxWeight = Math.max(...points.map((p) => p.weight));
  const minWeight = Math.min(...points.map((p) => p.weight));
  const range = maxWeight - minWeight || 1;
  const xStep = (w - 2 * pad) / Math.max(points.length - 1, 1);
  const path = points
    .map((p, i) => {
      const x = pad + i * xStep;
      const y = pad + (h - 2 * pad) * (1 - (p.weight - minWeight) / range);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-20">
      <path
        d={path}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="text-crisis-500"
      />
    </svg>
  );
}
