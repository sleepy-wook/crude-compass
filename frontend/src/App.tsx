import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";

import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { MarketDataPage } from "./pages/MarketDataPage";
import { MissionsPage } from "./pages/MissionsPage";
import { AskPage } from "./pages/AskPage";

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
            <Route path="missions" element={<MissionsPage />} />
            <Route path="missions/:id" element={<MissionsPage />} />
            <Route path="ask" element={<AskPage />} />
            {/* Legacy redirects */}
            <Route path="what-if" element={<Navigate to="/ask" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
