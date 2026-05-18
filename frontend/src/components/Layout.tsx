import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { ReactiveAlertToast } from "./ReactiveAlertToast";

export function Layout() {
  return (
    <div className="flex min-h-screen bg-paper text-ink font-body">
      <Sidebar />
      <main className="flex-1 px-8 py-10 overflow-y-auto">
        <Outlet />
      </main>
      {/* Phase 6 — OilPriceAPI spike alert */}
      <ReactiveAlertToast />
    </div>
  );
}
