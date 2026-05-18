import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { ReactiveAlertToast } from "./ReactiveAlertToast";

export function Layout() {
  return (
    <div className="flex min-h-screen bg-paper text-ink font-body">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
      {/* Phase 6 — OilPriceAPI spike alert */}
      <ReactiveAlertToast />
    </div>
  );
}
