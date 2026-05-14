import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { ReactiveAlertToast } from "./ReactiveAlertToast";

export function Layout() {
  return (
    <div className="flex min-h-screen bg-paper text-ink font-body">
      <Sidebar />
      <main className="flex-1 p-8 overflow-y-auto">
        <Outlet />
      </main>
      {/* Phase 6 — OilPriceAPI spike alert (시나리오 §15) */}
      <ReactiveAlertToast />
    </div>
  );
}
