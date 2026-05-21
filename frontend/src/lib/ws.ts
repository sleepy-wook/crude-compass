/**
 * WebSocket helpers — pulse stream (/api/ws/pulse).
 *
 * - connectPulseWs: usePulseStream이 wrap (events buffer).
 * - usePulseConnection: TopBar 실시간 연결 indicator (status only, REST 없음).
 */
import { useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "./api";

export type WSStatus = "disconnected" | "connecting" | "connected" | "error";

function pulseWsUrl(): string {
  // Production: API_BASE_URL == "" → window.location.origin 사용 (same-host wss://)
  // Dev: API_BASE_URL == "http://localhost:8000" → ws://localhost:8000
  const baseStr = API_BASE_URL || window.location.origin;
  const base = new URL(baseStr);
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  base.pathname = "/api/ws/pulse";
  return base.toString();
}

/**
 * Pulse WS connection — cross-mission Agent activity stream.
 *
 * `usePulseStream` hook이 wrap. 단순 callback 형태로 onMessage 전달.
 * dev: ws://localhost:8000/api/ws/pulse, prod: same-origin wss.
 */
export function connectPulseWs(onMessage: (data: unknown) => void): WebSocket {
  const ws = new WebSocket(pulseWsUrl());
  ws.onmessage = (ev) => {
    try {
      onMessage(JSON.parse(ev.data));
    } catch {
      // ignore malformed
    }
  };
  return ws;
}

/**
 * 실시간 연결 상태만 추적 (TopBar indicator).
 * /api/ws/pulse 연결 status만 반영 — 메시지 처리·REST 없음 → Lakebase wake 없음.
 */
export function usePulseConnection(): { status: WSStatus } {
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const reconnectTimerRef = useRef<number | null>(null);

  useEffect(() => {
    let mounted = true;
    let ws: WebSocket | null = null;

    function connect() {
      if (!mounted) return;
      setStatus("connecting");
      ws = new WebSocket(pulseWsUrl());
      ws.onopen = () => {
        if (mounted) setStatus("connected");
      };
      ws.onerror = () => {
        if (mounted) setStatus("error");
      };
      ws.onclose = () => {
        if (!mounted) return;
        setStatus("disconnected");
        // simple reconnect (3s)
        reconnectTimerRef.current = window.setTimeout(connect, 3_000);
      };
    }

    connect();

    return () => {
      mounted = false;
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
      }
      ws?.close();
    };
  }, []);

  return { status };
}
