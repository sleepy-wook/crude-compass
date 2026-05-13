import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { Discovery } from "./pages/Discovery";
import { MissionDetail, MissionsList } from "./pages/Missions";
import { WhatIf } from "./pages/WhatIf";

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
            <Route index element={<Discovery />} />
            <Route path="missions" element={<MissionsList />} />
            <Route path="missions/:id" element={<MissionDetail />} />
            <Route path="what-if" element={<WhatIf />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
