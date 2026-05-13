import { NavLink } from "react-router-dom";
import { cn } from "../lib/utils";
import { useMissionsWebSocket } from "../lib/ws";

const navItems = [
  { to: "/", label: "Discovery", desc: "오늘의 발견" },
  { to: "/missions", label: "Mission", desc: "진행 중 미션" },
  { to: "/what-if", label: "What-if", desc: "Time Travel" },
];

export function Sidebar() {
  const { status, lastEventAt } = useMissionsWebSocket();
  const elapsed = lastEventAt ? Math.floor((Date.now() - lastEventAt) / 1000) : null;

  return (
    <aside className="w-60 bg-sidebar-bg text-white flex flex-col h-screen sticky top-0">
      <div className="p-6 border-b border-sidebar-bg2">
        <div className="text-[10px] uppercase tracking-widest text-sidebar-muted mb-1">
          Crude Compass
        </div>
        <div className="font-display text-lg font-semibold tracking-tight">
          K-Petroleum
        </div>
        <div className="text-[10px] text-sidebar-muted2 font-mono mt-1">
          Bidirectional Decision Agent
        </div>
      </div>

      <nav className="flex-1 p-3">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "block px-3 py-3 mb-1 rounded-md transition-colors",
                isActive
                  ? "bg-sidebar-bg3 text-white"
                  : "text-sidebar-muted hover:bg-sidebar-bg2 hover:text-white"
              )
            }
          >
            <div className="text-sm font-medium">{item.label}</div>
            <div className="text-[10px] text-sidebar-muted2 mt-0.5">{item.desc}</div>
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-sidebar-bg2">
        <div className="flex items-center gap-2 text-xs">
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              status === "connected" && "bg-ok",
              status === "connecting" && "bg-warn",
              status === "disconnected" && "bg-sidebar-muted2",
              status === "error" && "bg-crisis-500"
            )}
          />
          <span className="text-sidebar-muted">
            {status === "connected" ? "Live sync" : status}
          </span>
        </div>
        {elapsed !== null && elapsed < 60 && (
          <div className="text-[10px] text-sidebar-muted2 mt-1 font-mono">
            last event {elapsed}s ago
          </div>
        )}
      </div>
    </aside>
  );
}
