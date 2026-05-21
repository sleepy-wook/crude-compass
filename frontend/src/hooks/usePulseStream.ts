/**
 * usePulseStream — WebSocket subscribe + 누적 events buffer.
 *
 * 초기 snapshot은 useRecentPulse (REST), 이후 신규 events는 WS push로 buffer 앞에 append.
 * Reconnect 시 마지막 event ts 이후 events만 fetch (gap fill) — 단순 구현은 reconnect = 전체 refetch.
 *
 * Returns:
 *   events: ActivityEvent[]  // 최신 N개 (DESC), useRecentPulse data + WS 누적
 *   connected: boolean       // WS 상태
 */
import { useEffect, useRef, useState } from "react";
import type { ActivityEvent } from "../lib/types";
import { connectPulseWs } from "../lib/ws";
import { useRecentPulse } from "../lib/queries";

const MAX_BUFFER = 200;

export function usePulseStream(initialLimit = 50) {
  const [connected, setConnected] = useState(false);
  // WS 연결되면 REST polling 끔 (Lakebase scale-to-zero 보존).
  // 미연결 시에만 60s fallback polling — WS 실패해도 데이터는 갱신.
  const { data, refetch } = useRecentPulse(initialLimit, {
    refetchMs: connected ? false : 60_000,
  });
  const [wsEvents, setWsEvents] = useState<ActivityEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = connectPulseWs((msg) => {
      const m = msg as Record<string, unknown> | null;
      if (!m || typeof m !== "object") return;
      if (m.type === "connected") {
        setConnected(true);
        return;
      }
      if (m.type === "ping") return;
      if (m.type === "pulse") {
        // WS payload → ActivityEvent shape 변환
        const ts = typeof m.ts === "number" ? m.ts : Date.now() / 1000;
        const ev: ActivityEvent = {
          id: `ws-${ts}`,
          mission_id: (m.mission_id as string) ?? null,
          occurred_at: new Date(ts * 1000).toISOString(),
          actor: m.actor as string,
          action: m.action as string,
          result_preview: (m.result_preview as string) ?? null,
          metadata: (m.metadata as Record<string, unknown>) ?? null,
        };
        setWsEvents((prev) => [ev, ...prev].slice(0, MAX_BUFFER));
      }
    });
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    wsRef.current = ws;
    return () => ws.close();
  }, []);

  const restEvents = data?.events ?? [];
  // Dedup by id (REST + WS 합쳐서 — WS는 ws- prefix라 보통 안 겹침)
  const seen = new Set<string>();
  const merged: ActivityEvent[] = [];
  for (const e of [...wsEvents, ...restEvents]) {
    const key = String(e.id);
    if (!seen.has(key)) {
      seen.add(key);
      merged.push(e);
    }
  }
  return { events: merged.slice(0, MAX_BUFFER), connected, refetch };
}
