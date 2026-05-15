/**
 * Phase 6 Reactive Trigger toast — OilPriceAPI spike alert.
 *
 * useMissionsWebSocket의 lastEvent watch → 'reactive.alert' 이벤트 시 5초 toast 표시.
 * 우상단 fixed 위치, 자동 사라짐.
 */
import { useEffect, useState } from "react";
import { useMissionsWebSocket } from "../lib/ws";
import type { WSEvent } from "../lib/types";

interface AlertDisplay {
  id: number;
  title: string;
  body: string;
  direction?: "bullish" | "bearish";
}

export function ReactiveAlertToast() {
  const { lastEvent } = useMissionsWebSocket();
  const [alert, setAlert] = useState<AlertDisplay | null>(null);

  useEffect(() => {
    if (!lastEvent) return;
    if ((lastEvent as WSEvent).type !== "reactive.alert") return;
    const ev = lastEvent as Extract<WSEvent, { type: "reactive.alert" }>;
    // 의도된 패턴: external WS event → React state sync. Effect가 적절한 사용처.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAlert({
      id: Date.now(),
      title: ev.title,
      body: ev.body,
      direction: ev.direction,
    });
    const timer = setTimeout(() => setAlert(null), 8000);
    return () => clearTimeout(timer);
  }, [lastEvent]);

  if (!alert) return null;

  const accent =
    alert.direction === "bullish"
      ? "bg-crisis-50 border-crisis-500 text-crisis-700"
      : alert.direction === "bearish"
      ? "bg-opportunity-50 border-opportunity-500 text-opportunity-700"
      : "bg-panel border-ink text-ink";

  return (
    <div className="fixed top-6 right-6 z-[70] max-w-sm">
      <div
        role="alert"
        className={`rounded-lg border-l-4 shadow-lg px-4 py-3 ${accent}`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="font-display font-semibold text-base mb-1">
              {alert.title}
            </div>
            <div className="text-sm leading-snug opacity-90">{alert.body}</div>
          </div>
          <button
            onClick={() => setAlert(null)}
            className="text-current opacity-60 hover:opacity-100 text-lg leading-none"
            aria-label="닫기"
          >
            ×
          </button>
        </div>
      </div>
    </div>
  );
}
