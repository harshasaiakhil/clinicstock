import React, { useState } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Pill, Mail, Lock, AlertCircle, Eye, EyeOff, UserCheck } from "lucide-react";

const Login: React.FC = () => {
  const { login, isAuthenticated, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Redirect path after login
  const from = (location.state as any)?.from?.pathname || "/";

  if (isAuthenticated && !authLoading) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err: any) {
      console.error("Login failure:", err);
      if (!err.response) {
        setError("Network error: Cannot reach the backend API at http://127.0.0.1:8000. Please ensure the FastAPI server is running.");
      } else if (err.response.status === 400 || err.response.status === 401) {
        setError(err.response.data?.detail || "Incorrect email or password. Please check your credentials.");
      } else {
        setError(err.response.data?.detail || `Server error (${err.response.status}). Please check the backend.`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50 font-sans">
      {/* Left decorative sidebar panel */}
      <div className="relative hidden w-1/2 flex-col justify-between bg-teal-900 p-12 text-white lg:flex">
        {/* Graphic background curves */}
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-teal-400 via-teal-900 to-slate-900 pointer-events-none" />
        
        <div className="flex items-center space-x-3 z-10">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-500 shadow-md">
            <Pill className="h-6 w-6 text-teal-950" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight text-white block">ClinicStock</span>
            <span className="text-xs text-teal-300 font-medium uppercase tracking-wider">ERP System</span>
          </div>
        </div>

        <div className="space-y-6 z-10">
          <h2 className="text-4xl font-extrabold tracking-tight leading-tight text-white">
            Smart Inventory Management for Homeopathy Clinics
          </h2>
          <p className="text-lg text-teal-100 max-w-md font-light leading-relaxed">
            Efficiently catalog medicines, coordinate stock batches, trace branch-level transactions, and monitor expiration alerts inside a unified environment.
          </p>
        </div>

        <div className="z-10 text-xs text-teal-300 font-medium">
          © {new Date().getFullYear()} ClinicStock ERP Inc. All rights reserved.
        </div>
      </div>

      {/* Right Login Panel */}
      <div className="flex w-full items-center justify-center p-8 lg:w-1/2 bg-white">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center lg:text-left">
            <div className="lg:hidden flex justify-center mb-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-teal-600 shadow-md">
                <Pill className="h-7 w-7 text-white" />
              </div>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-800">
              Sign In
            </h1>
            <p className="mt-2 text-sm text-slate-500">
              Enter your email and password to access your clinic portal
            </p>
          </div>

          {error && (
            <div className="flex items-center space-x-3 rounded-xl bg-rose-50 border border-rose-100 p-4 text-sm text-rose-800">
              <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
              <p className="font-medium">{error}</p>
            </div>
          )}

          {/* Quick-fill Seed Credentials Card for Local Development */}
          <div className="rounded-xl border border-teal-100 bg-teal-50/70 p-4 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="flex items-center text-xs font-bold uppercase tracking-wider text-teal-800">
                <UserCheck className="h-3.5 w-3.5 mr-1.5 text-teal-600" />
                Quick-Fill Demo Credentials
              </span>
              <span className="text-[11px] text-teal-600 font-medium">Click to fill</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  setEmail("doctor@clinicstock.com");
                  setPassword("Password123");
                  setError(null);
                }}
                className="flex flex-col text-left rounded-lg bg-white p-2.5 border border-teal-200/70 hover:border-teal-500 hover:shadow-sm transition-all cursor-pointer"
              >
                <div className="flex items-center justify-between w-full">
                  <span className="font-bold text-teal-900 text-xs">Doctor</span>
                  <span className="rounded bg-teal-100 px-1 py-0.2 text-[9px] font-bold text-teal-800">Admin</span>
                </div>
                <span className="text-slate-500 text-[11px] truncate mt-0.5">doctor@clinicstock.com</span>
                <span className="text-[10px] text-teal-700 mt-1 font-mono font-medium">Password: Password123</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setEmail("assistant@clinicstock.com");
                  setPassword("Password123");
                  setError(null);
                }}
                className="flex flex-col text-left rounded-lg bg-white p-2.5 border border-teal-200/70 hover:border-teal-500 hover:shadow-sm transition-all cursor-pointer"
              >
                <div className="flex items-center justify-between w-full">
                  <span className="font-bold text-teal-900 text-xs">Assistant</span>
                  <span className="rounded bg-slate-100 px-1 py-0.2 text-[9px] font-bold text-slate-700">Kaikaluru</span>
                </div>
                <span className="text-slate-500 text-[11px] truncate mt-0.5">assistant@clinicstock.com</span>
                <span className="text-[10px] text-teal-700 mt-1 font-mono font-medium">Password: Password123</span>
              </button>
            </div>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label
                htmlFor="email"
                className="text-xs font-semibold uppercase tracking-wider text-slate-600 block"
              >
                Email Address
              </label>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none">
                  <Mail className="h-4.5 w-4.5 text-slate-400" />
                </div>
                <input
                  type="email"
                  id="email"
                  required
                  placeholder="name@clinic.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full rounded-xl border border-slate-200 bg-slate-50 py-3 pl-11 pr-4 text-sm text-slate-800 placeholder-slate-400 focus:border-teal-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-teal-500 transition-all duration-200"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="password"
                className="text-xs font-semibold uppercase tracking-wider text-slate-600 block"
              >
                Password
              </label>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none">
                  <Lock className="h-4.5 w-4.5 text-slate-400" />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  id="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full rounded-xl border border-slate-200 bg-slate-50 py-3 pl-11 pr-11 text-sm text-slate-800 placeholder-slate-400 focus:border-teal-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-teal-500 transition-all duration-200"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-slate-400 hover:text-slate-600 cursor-pointer"
                >
                  {showPassword ? <EyeOff className="h-4.5 w-4.5" /> : <Eye className="h-4.5 w-4.5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="flex w-full justify-center rounded-xl bg-teal-600 py-3 px-4 text-sm font-bold text-white hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:bg-teal-400 disabled:cursor-not-allowed shadow-md cursor-pointer transition-all duration-200"
            >
              {loading ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
              ) : (
                "Sign In to ClinicStock"
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Login;
