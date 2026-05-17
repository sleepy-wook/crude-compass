/**
 * WebSocket hook — /api/ws/missions 5초 sync.
 * 서버 events → React Query cache invalidate → UI 즉시 반영.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { API_BASE_URL } from "./api";
import { queryKeys } from "./queries";
import type { Mission, WSEvent } from "./types";

export type WSStatus = "disconnected" | "connecting" | "connected" | "error";

function wsUrl(): string {
  // Production: API_BASE_URL == "" → window.location.origin 사용 (same-host wss://)
  // Dev: API_BASE_URL == "http://localhost:8000" → ws://localhost:8000
  const baseStr = API_BASE_URL || window.location.origin;
  const base = new URL(baseStr);
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  base.pathname = "/api/ws/missions";
  return base.toString();
}

interface UseWebSocketResult {
  status: WSStatus;
  lastEvent: WSEvent | null;
  lastEventAt: number | null;
}

export function useMissionsWebSocket(): UseWebSocketResult {
  const qc = useQueryClient();
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(null);
  const [lastEventAt, setLastEventAt] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  useEffect(() => {
    let mounted = true;

    function connect() {
      if (!mounted) return;
      setStatus("connecting");
      const ws = new WebSocket(wsUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mounted) return;
        setStatus("connected");
        try {
          ws.send(JSON.stringify({ type: "subscribe" }));
        } catch {
          // ignore
        }
      };

      ws.onmessage = (msg) => {
        if (!mounted) return;
        try {
          const ev = JSON.parse(msg.data) as WSEvent;
          setLastEvent(ev);
          setLastEventAt(Date.now());

          // Cache invalidation based on event type
          if (ev.type === "ping") {
            // keepalive — echo pong (optional)
            try {
              ws.send(JSON.stringify({ type: "pong", ts: ev.ts }));
            } catch {
              // ignore
            }
            return;
          }
          if (
            ev.type === "mission.proposed" ||
            ev.type === "mission.confirmed" ||
            ev.type === "mission.pivoted" ||
            ev.type === "mission.updated"
          ) {
            const mission: Mission = ev.mission;
            qc.setQueryData(queryKeys.mission(mission.mission_id), mission);
            qc.invalidateQueries({ queryKey: queryKeys.missionsActive });
          }
          if (ev.type === "pattern.changed") {
            qc.invalidateQueries({ queryKey: queryKeys.patternCurrent });
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onerror = () => {
        setStatus("error");
      };

      ws.onclose = () => {
        if (!mounted) return;
        setStatus("disconnected");
        // exponential backoff reconnect (max 30s)
        reconnectTimerRef.current = window.setTimeout(() => {
          connect();
        }, 3_000);
      };
    }

    connect();

    return () => {
      mounted = false;
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
      }
      wsRef.current?.close();
    };
  }, [qc]);

  return { status, lastEvent, lastEventAt };
}
