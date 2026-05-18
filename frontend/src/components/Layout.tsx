import { Outlet } from "react-router-dom";
import { RightSidebar } from "./RightSidebar";
import { ReactiveAlertToast } from "./ReactiveAlertToast";

export function Layout() {
  return (
    <div className="flex min-h-screen bg-paper text-ink font-body">
      <main className="flex-1 px-8 py-8 overflow-y-auto">
        <Outlet />
      </main>
      <RightSidebar />
      {/* Phase 6 — OilPriceAPI spike alert (시나리오 §15) */}
      <ReactiveAlertToast />
    </div>
  );
}
