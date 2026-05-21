/**
 * useChatHistory — Investigation 대화 기록 localStorage 관리 (2026-05-21).
 *
 * 구조:
 *   { id, title, turns[], created_at, updated_at }
 * 최대 50개 저장 — 초과 시 oldest trim.
 * 자동 title = 첫 질문 50자.
 *
 * 다중 디바이스 sync 필요시 Lakebase persistence로 마이그레이션 가능 (별도 작업).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessageData } from "../components/ChatMessage";

const STORAGE_KEY = "crude-compass:chats:v1";
const MAX_CONVERSATIONS = 50;

export interface ChatTurn {
  question: string;
  enriched: string;
  similarCtx: ChatMessageData["similarContext"];
  message: ChatMessageData;
}

export interface ChatConversation {
  id: string;
  title: string;
  turns: ChatTurn[];
  created_at: string;
  updated_at: string;
}

function loadAll(): ChatConversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed as ChatConversation[];
  } catch {
    return [];
  }
}

function saveAll(convs: ChatConversation[]): void {
  try {
    const trimmed = convs.slice(0, MAX_CONVERSATIONS);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch {
    // quota / disabled — silent
  }
}

function newId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function makeTitle(firstQuestion: string): string {
  const t = firstQuestion.trim().replace(/\s+/g, " ");
  return t.length > 50 ? t.slice(0, 50) + "…" : t;
}

export function useChatHistory() {
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [activeId, setActiveId] = useState<string | undefined>(undefined);

  // activeId ref — useCallback closure가 stale activeId를 캡쳐하는 문제 회피.
  // appendTurn이 새 conversation을 만들면서 setActiveId 호출해도
  // 같은 tick의 runStream이 곧장 updateLastTurn(...) 부를 때 ref는 즉시 갱신됨.
  const activeIdRef = useRef<string | undefined>(undefined);
  useEffect(() => {
    activeIdRef.current = activeId;
  }, [activeId]);

  // 초기 load
  useEffect(() => {
    const all = loadAll();
    setConversations(all);
  }, []);

  const active = conversations.find((c) => c.id === activeId);

  /**
   * 새 대화 시작 — id 발급, list에 빈 conversation 추가, active로 설정.
   * 첫 turn append 전까지는 title이 "(새 대화)".
   */
  const startNew = useCallback(() => {
    const id = newId();
    const now = new Date().toISOString();
    const conv: ChatConversation = {
      id,
      title: "(새 대화)",
      turns: [],
      created_at: now,
      updated_at: now,
    };
    setConversations((prev) => {
      const next = [conv, ...prev].slice(0, MAX_CONVERSATIONS);
      saveAll(next);
      return next;
    });
    activeIdRef.current = id;
    setActiveId(id);
    return id;
  }, []);

  /**
   * turns 추가 — 첫 turn이면 title 자동 설정. updated_at 갱신 + list 최상위 이동.
   * activeId 없으면 새 conversation 자동 생성 후 append.
   */
  const appendTurn = useCallback((turn: ChatTurn) => {
    setConversations((prev) => {
      let convs = [...prev];
      let id = activeIdRef.current;
      const now = new Date().toISOString();
      const idx = convs.findIndex((c) => c.id === id);
      if (idx < 0) {
        // 새 conversation 생성 — ref 즉시 갱신, runStream의 다음 updateLastTurn이 잡도록
        id = newId();
        const conv: ChatConversation = {
          id,
          title: makeTitle(turn.question),
          turns: [turn],
          created_at: now,
          updated_at: now,
        };
        convs = [conv, ...convs];
        activeIdRef.current = id;
        setActiveId(id);
      } else {
        const conv = convs[idx];
        const updated: ChatConversation = {
          ...conv,
          title: conv.turns.length === 0 ? makeTitle(turn.question) : conv.title,
          turns: [...conv.turns, turn],
          updated_at: now,
        };
        convs.splice(idx, 1);
        convs = [updated, ...convs];
      }
      const trimmed = convs.slice(0, MAX_CONVERSATIONS);
      saveAll(trimmed);
      return trimmed;
    });
  }, []);

  /**
   * 가장 최근 turn의 message patch (pending → 완료 응답).
   * activeId의 마지막 turn만 업데이트.
   */
  const updateLastTurn = useCallback((patch: Partial<ChatMessageData>) => {
    setConversations((prev) => {
      const convs = [...prev];
      const idx = convs.findIndex((c) => c.id === activeIdRef.current);
      if (idx < 0) return prev;
      const conv = convs[idx];
      if (conv.turns.length === 0) return prev;
      const turns = [...conv.turns];
      const last = turns[turns.length - 1];
      turns[turns.length - 1] = {
        ...last,
        message: { ...last.message, ...patch },
      };
      const updated: ChatConversation = {
        ...conv,
        turns,
        updated_at: new Date().toISOString(),
      };
      convs[idx] = updated;
      saveAll(convs);
      return convs;
    });
  }, []);

  const select = useCallback((id: string) => {
    activeIdRef.current = id;
    setActiveId(id);
  }, []);

  const remove = useCallback((id: string) => {
    setConversations((prev) => {
      const next = prev.filter((c) => c.id !== id);
      saveAll(next);
      return next;
    });
    setActiveId((cur) => {
      const nextActive = cur === id ? undefined : cur;
      activeIdRef.current = nextActive;
      return nextActive;
    });
  }, []);

  return {
    conversations,
    activeId,
    active,
    startNew,
    appendTurn,
    updateLastTurn,
    select,
    remove,
  };
}
