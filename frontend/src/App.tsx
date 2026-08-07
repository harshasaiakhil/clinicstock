import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import { Medicines } from "./pages/Medicines";

import { MasterData } from "./pages/MasterData";
import { Reports } from "./pages/Reports";
import { Settings } from "./pages/Settings";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          {/* Main App Routes */}
          <Route
            path="/"
            element={
              <Layout>
                <Dashboard />
              </Layout>
            }
          />

          <Route
            path="/medicines"
            element={
              <Layout>
                <Medicines />
              </Layout>
            }
          />

          <Route
            path="/inventory"
            element={<Navigate to="/medicines" replace />}
          />

          <Route
            path="/masters"
            element={
              <Layout>
                <MasterData />
              </Layout>
            }
          />

          <Route
            path="/reports"
            element={
              <Layout>
                <Reports />
              </Layout>
            }
          />

          <Route
            path="/settings"
            element={
              <Layout>
                <Settings />
              </Layout>
            }
          />

          {/* Fallback Route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
