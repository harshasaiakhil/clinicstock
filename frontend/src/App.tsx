import React, { Suspense } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";

// Code-split pages via React.lazy for high initial load performance
const Login = React.lazy(() => import("./pages/Login"));
const Dashboard = React.lazy(() => import("./pages/Dashboard"));
const Medicines = React.lazy(() =>
  import("./pages/Medicines").then((m) => ({ default: m.Medicines }))
);
const MasterData = React.lazy(() =>
  import("./pages/MasterData").then((m) => ({ default: m.MasterData }))
);
const Reports = React.lazy(() =>
  import("./pages/Reports").then((m) => ({ default: m.Reports }))
);
const Settings = React.lazy(() =>
  import("./pages/Settings").then((m) => ({ default: m.Settings }))
);
const UsersPage = React.lazy(() =>
  import("./pages/Users").then((m) => ({ default: m.UsersPage }))
);

const PageLoadingFallback: React.FC = () => (
  <div className="flex h-64 items-center justify-center">
    <div className="flex flex-col items-center space-y-3">
      <div className="h-8 w-8 animate-spin rounded-full border-3 border-teal-600 border-t-transparent" />
      <span className="text-xs font-medium text-slate-400">Loading module...</span>
    </div>
  </div>
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 60 * 1000, // 1 minute default stale time
      gcTime: 10 * 60 * 1000, // 10 minutes cache garbage collection
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <Suspense fallback={<PageLoadingFallback />}>
            <Routes>
              {/* Login Route */}
              <Route path="/login" element={<Login />} />

              {/* Protected Main App Routes */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <Dashboard />
                    </Layout>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/medicines"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <Medicines />
                    </Layout>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/inventory"
                element={<Navigate to="/medicines" replace />}
              />

              <Route
                path="/masters"
                element={
                  <ProtectedRoute allowedRoles={["doctor"]}>
                    <Layout>
                      <MasterData />
                    </Layout>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/reports"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <Reports />
                    </Layout>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/settings"
                element={
                  <ProtectedRoute allowedRoles={["doctor"]}>
                    <Layout>
                      <Settings />
                    </Layout>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/users"
                element={
                  <ProtectedRoute allowedRoles={["doctor"]}>
                    <Layout>
                      <UsersPage />
                    </Layout>
                  </ProtectedRoute>
                }
              />

              {/* Fallback Route */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
