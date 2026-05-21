/**
 * ChatHistorySidebar — Investigation 좌측 대화 기록 (2026-05-21).
 *
 * - [+ 새 대화] 버튼 (top)
 * - conversation list: title + relative time + turn count
 * - active highlight
 * - hover delete (×)
 */
import { Plus, Trash2 } from "lucide-react";
import { cn } from "../lib/utils";
import type { ChatConversation } from "../lib/useChatHistory";

interface Props {
  conversations: ChatConversation[];
  activeId: string | undefined;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRemove: (id: string) => void;
}

function relTime(iso: string): string {
  try {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return "방금";
    if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
    return `${Math.floor(diff / 86400)}일 전`;
  } catch {
    return "—";
  }
}

export function ChatHistorySidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onRemove,
}: Props) {
  return (
    <aside className="w-64 border-r border-line-1 bg-panel flex flex-col shrink-0">
      <div className="p-3 border-b border-line-1">
        <button
          type="button"
          onClick={onNew}
          className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-md bg-ink-1 text-paper text-[12px] font-medium hover:bg-ink-2 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          새 대화
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="px-4 py-8 text-center text-[11px] text-ink-3 leading-relaxed">
            대화 기록 없음
            <br />
            <span className="text-ink-3/70">질문을 시작하면 여기에 저장됩니다.</span>
          </div>
        ) : (
          <ul className="py-1">
            {conversations.map((c) => (
              <li key={c.id} className="group relative">
                <button
                  type="button"
                  onClick={() => onSelect(c.id)}
                  className={cn(
                    "w-full text-left px-3 py-2 transition-colors",
                    c.id === activeId
                      ? "bg-line-1 border-l-2 border-ink-1"
                      : "border-l-2 border-transparent hover:bg-line-1/60",
                  )}
                  title={c.title}
                >
                  <div
                    className="text-[12.5px] text-ink-1 leading-snug pr-6 truncate"
                    style={{
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {c.title}
                  </div>
                  <div className="mt-1 flex items-center gap-1.5 text-[10.5px] text-ink-3 tabular-nums">
                    <span>{relTime(c.updated_at)}</span>
                    <span aria-hidden>·</span>
                    <span>{c.turns.length} turn</span>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm("이 대화를 삭제할까요?")) onRemove(c.id);
                  }}
                  className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-line-2 text-ink-3 hover:text-crisis-700"
                  aria-label="대화 삭제"
                  title="삭제"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <footer className="px-4 py-2 border-t border-line-1 text-[10px] text-ink-3 leading-snug">
        브라우저에 저장 · 최대 50개
      </footer>
    </aside>
  );
}
