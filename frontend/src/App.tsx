import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ArchivePage } from "./pages/ArchivePage";
import { Dashboard } from "./pages/Dashboard";
import { LibraryPage } from "./pages/LibraryPage";
import { MarketDataPage } from "./pages/MarketDataPage";
import { AskPage } from "./pages/AskPage";
import { EvidenceBoardPage } from "./pages/EvidenceBoardPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="market" element={<MarketDataPage />} />
            <Route path="ask" element={<AskPage />} />
            {/* D-2: sub-pages (no sidebar tab — 4탭 IA 유지) */}
            <Route path="evidence" element={<EvidenceBoardPage />} />
            <Route path="archive" element={<ArchivePage />} />
            <Route path="library" element={<LibraryPage />} />
            {/* Legacy redirects */}
            <Route path="what-if" element={<Navigate to="/ask" replace />} />
            <Route path="backtest" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
