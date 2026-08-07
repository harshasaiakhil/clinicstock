import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./context/AuthContext";
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
      <AuthProvider>
        <Router>
          <Routes>
            {/* Dashboard */}
            <Route
              path="/"
              element={
                <Layout>
                  <Dashboard />
                </Layout>
              }
            />

            {/* Medicines */}
            <Route
              path="/medicines"
              element={
                <Layout>
                  <Medicines />
                </Layout>
              }
            />

            {/* Inventory */}
            <Route
              path="/inventory"
              element={<Navigate to="/medicines" replace />}
            />

            {/* Master Data */}
            <Route
              path="/masters"
              element={
                <Layout>
                  <MasterData />
                </Layout>
              }
            />

            {/* Reports */}
            <Route
              path="/reports"
              element={
                <Layout>
                  <Reports />
                </Layout>
              }
            />

            {/* Settings */}
            <Route
              path="/settings"
              element={
                <Layout>
                  <Settings />
                </Layout>
              }
            />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;