import React, { useState, useEffect } from "react";
import api from "../api";
import { useUser } from "../hooks/useUser";
import {
  Pill,
  Boxes,
  Coins,
  AlertTriangle,
  Building,
  ArrowDownLeft,
  ArrowUpRight,
  TrendingUp,
  RefreshCw,
} from "lucide-react";

interface Branch {
  id: string;
  name: string;
  code: string;
}

interface BranchStats {
  branch_id: string;
  branch_name: string;
  branch_code: string;
  total_inventory_items: number;
  total_inventory_value: number;
  low_stock_count: number;
}

interface TopMedicine {
  medicine_id: string;
  name: string;
  generic_name: string | null;
  value: number;
}

interface StockTx {
  id: string;
  transaction_type: string;
  quantity_changed: number;
  reason: string | null;
  timestamp: string;
  user: {
    first_name: string;
    last_name: string;
  };
  branch: {
    name: string;
  };
  batch: {
    batch_number: string;
    summary: {
      medicine: {
        name: string;
      };
    };
  };
}

interface DashboardStats {
  total_medicines: number;
  total_active_medicines: number;
  total_inventory_items: number;
  total_inventory_value: number;
  low_stock_count: number;
  out_of_stock_count: number;
  expiring_30_days_count: number;
  expired_count: number;
  todays_stock_in: number;
  todays_dispensed: number;
  todays_transfers: number;
  todays_adjustments: number;
  todays_damaged: number;
  branch_wise_stats: BranchStats[];
  top_dispensed_medicines: TopMedicine[];
  top_low_stock_medicines: TopMedicine[];
  recent_activity: StockTx[];
}

const Dashboard: React.FC = () => {
  const { user } = useUser();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [selectedBranchId, setSelectedBranchId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Set default branch for assistant
  useEffect(() => {
    if (user && user.role === "assistant") {
      setSelectedBranchId(user.default_branch_id);
    }
  }, [user]);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch Stats
      const statsParams: Record<string, string> = {};
      if (selectedBranchId) {
        statsParams.branch_id = selectedBranchId;
      }
      const statsRes = await api.get<DashboardStats>("/dashboard/stats", {
        params: statsParams,
      });
      setStats(statsRes.data);

      // 2. Fetch branches for doctor selection
      if (user && user.role === "doctor" && branches.length === 0) {
        const branchesRes = await api.get<Branch[]>("/branches/");
        setBranches(branchesRes.data);
      }
    } catch (err: any) {
      console.error(err);
      setError("Failed to fetch dashboard data. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Only load if assistant has their branch set, or if doctor
    if (user) {
      if (user.role === "assistant" && !selectedBranchId) {
        return;
      }
      loadDashboardData();
    }
  }, [selectedBranchId, user]);

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(val);
  };

  if (loading && !stats) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex flex-col items-center space-y-3">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-teal-600 border-t-transparent"></div>
          <span className="text-sm text-slate-500 font-medium">Gathering analytics...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Dashboard Top Section (Title & Filters) */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight">Clinic Summary</h2>
          <p className="text-sm text-slate-500">Real-time overview of medicines and stock changes</p>
        </div>

        {/* Branch Filter dropdown (Doctors only) */}
        {user?.role === "doctor" ? (
          <div className="flex items-center space-x-3 bg-white border border-slate-200 shadow-sm rounded-xl px-4 py-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Branch:</span>
            <select
              value={selectedBranchId}
              onChange={(e) => setSelectedBranchId(e.target.value)}
              className="text-sm font-semibold text-slate-800 bg-transparent focus:outline-none border-none cursor-pointer"
            >
              <option value="">All Branches (Global)</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div className="flex items-center space-x-2 bg-teal-50 border border-teal-100 rounded-xl px-4 py-2">
            <Building className="h-4 w-4 text-teal-600" />
            <span className="text-xs font-bold text-teal-800 uppercase tracking-wide">
              {user?.default_branch?.name} Branch Stats
            </span>
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-center space-x-3 rounded-xl bg-rose-50 border border-rose-100 p-4 text-sm text-rose-800">
          <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0" />
          <p className="font-medium">{error}</p>
          <button onClick={loadDashboardData} className="ml-auto flex items-center space-x-1 text-teal-600 hover:text-teal-700 font-semibold cursor-pointer">
            <RefreshCw className="h-4 w-4" />
            <span>Retry</span>
          </button>
        </div>
      )}

      {stats && (
        <>
          {/* 1. Core Summary Metrics Cards */}
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
            {/* Total Medicines Card */}
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm hover:shadow-md transition-all duration-200">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-500">Catalog Medicines</span>
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
                  <Pill className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-4">
                <span className="block text-2xl font-extrabold text-slate-800">{stats.total_medicines}</span>
                <span className="mt-1 text-xs font-semibold text-slate-400">
                  Active: <strong className="text-teal-600 font-bold">{stats.total_active_medicines}</strong>
                </span>
              </div>
            </div>

            {/* Total Available Quantity Card */}
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm hover:shadow-md transition-all duration-200">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-500">Total Stock Qty</span>
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-50 text-sky-700">
                  <Boxes className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-4">
                <span className="block text-2xl font-extrabold text-slate-800">
                  {stats.total_inventory_items.toLocaleString("en-IN")}
                </span>
                <span className="mt-1 text-xs font-semibold text-slate-400">
                  Out of stock: <strong className="text-rose-500 font-bold">{stats.out_of_stock_count}</strong>
                </span>
              </div>
            </div>

            {/* Total Inventory Value Card */}
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm hover:shadow-md transition-all duration-200">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-500">Stock Valuation</span>
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
                  <Coins className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-4">
                <span className="block text-2xl font-extrabold text-slate-800">
                  {formatCurrency(stats.total_inventory_value)}
                </span>
                <span className="mt-1 text-xs font-semibold text-slate-400">
                  Purchase cost basis
                </span>
              </div>
            </div>

            {/* Alerts & Expiries Card */}
            <div className={`rounded-2xl border bg-white p-6 shadow-sm hover:shadow-md transition-all duration-200 ${
              stats.expired_count > 0
                ? "border-rose-100 bg-rose-50/10"
                : stats.expiring_30_days_count > 0
                ? "border-amber-100 bg-amber-50/10"
                : "border-slate-100"
            }`}>
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-500">Expiration Alerts</span>
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${
                  stats.expired_count > 0
                    ? "bg-rose-50 text-rose-700"
                    : stats.expiring_30_days_count > 0
                    ? "bg-amber-50 text-amber-700"
                    : "bg-slate-50 text-slate-500"
                }`}>
                  <AlertTriangle className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-4">
                <span className={`block text-2xl font-extrabold ${stats.expired_count > 0 ? "text-rose-700" : "text-slate-800"}`}>
                  {stats.expired_count} Expired
                </span>
                <span className="mt-1 text-xs font-semibold text-slate-400">
                  Expiring in 30d: <strong className="text-amber-600 font-bold">{stats.expiring_30_days_count}</strong>
                </span>
              </div>
            </div>
          </div>

          {/* 2. Today's Activity & Low Stock Grid */}
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Today's Transactions meters (Left) */}
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm lg:col-span-1">
              <h3 className="text-base font-bold text-slate-800 mb-5">Today's stock Activity</h3>
              <div className="space-y-4">
                {/* Stock In */}
                <div>
                  <div className="flex justify-between text-xs font-bold text-slate-600 mb-1">
                    <span className="flex items-center space-x-1.5"><ArrowDownLeft className="h-3.5 w-3.5 text-emerald-500" /><span>Inward Stock</span></span>
                    <span>+{stats.todays_stock_in} units</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                    <div className="h-full rounded-full bg-emerald-500" style={{ width: `${Math.min(100, stats.todays_stock_in)}%` }}></div>
                  </div>
                </div>

                {/* Dispensed */}
                <div>
                  <div className="flex justify-between text-xs font-bold text-slate-600 mb-1">
                    <span className="flex items-center space-x-1.5"><ArrowUpRight className="h-3.5 w-3.5 text-sky-500" /><span>Dispensed</span></span>
                    <span>-{stats.todays_dispensed} units</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                    <div className="h-full rounded-full bg-sky-500" style={{ width: `${Math.min(100, stats.todays_dispensed)}%` }}></div>
                  </div>
                </div>

                {/* Transfers */}
                <div>
                  <div className="flex justify-between text-xs font-bold text-slate-600 mb-1">
                    <span className="flex items-center space-x-1.5"><TrendingUp className="h-3.5 w-3.5 text-purple-500" /><span>Transfers</span></span>
                    <span>{stats.todays_transfers} units</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                    <div className="h-full rounded-full bg-purple-500" style={{ width: `${Math.min(100, stats.todays_transfers)}%` }}></div>
                  </div>
                </div>

                {/* Adjustments */}
                <div>
                  <div className="flex justify-between text-xs font-bold text-slate-600 mb-1">
                    <span className="flex items-center space-x-1.5"><RefreshCw className="h-3.5 w-3.5 text-slate-500" /><span>Adjustments</span></span>
                    <span>{stats.todays_adjustments >= 0 ? "+" : ""}{stats.todays_adjustments} units</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                    <div className="h-full rounded-full bg-slate-500" style={{ width: `${Math.min(100, Math.abs(stats.todays_adjustments))}%` }}></div>
                  </div>
                </div>

                {/* Damaged */}
                <div>
                  <div className="flex justify-between text-xs font-bold text-slate-600 mb-1">
                    <span className="flex items-center space-x-1.5"><AlertTriangle className="h-3.5 w-3.5 text-rose-500" /><span>Damaged / Expired</span></span>
                    <span className="text-rose-600">-{stats.todays_damaged} units</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                    <div className="h-full rounded-full bg-rose-500" style={{ width: `${Math.min(100, stats.todays_damaged)}%` }}></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Low stock Count summary (Right) */}
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm lg:col-span-2">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-base font-bold text-slate-800">Critical Stock Status</h3>
                  <p className="text-xs text-slate-400">Inventory lines requiring reorder attention</p>
                </div>
                <div className="rounded-full bg-amber-50 border border-amber-100 px-3 py-1 text-xs text-amber-700 font-bold uppercase tracking-wider">
                  {stats.low_stock_count} Warnings
                </div>
              </div>

              {stats.top_low_stock_medicines.length === 0 ? (
                <div className="flex h-44 items-center justify-center border border-dashed border-slate-200 rounded-xl">
                  <span className="text-sm text-slate-400 font-medium">All medicines have adequate stock levels!</span>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-100">
                    <thead>
                      <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-400">
                        <th className="py-2.5">Medicine Name</th>
                        <th className="py-2.5">Generic Name</th>
                        <th className="py-2.5 text-right">Available Qty</th>
                        <th className="py-2.5 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-sm">
                      {stats.top_low_stock_medicines.map((med) => (
                        <tr key={med.medicine_id} className="hover:bg-slate-50/50">
                          <td className="py-3 font-semibold text-slate-700">{med.name}</td>
                          <td className="py-3 text-slate-400">{med.generic_name || "—"}</td>
                          <td className="py-3 text-right font-bold text-slate-800">{med.value}</td>
                          <td className="py-3 text-right">
                            <span className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
                              med.value === 0
                                ? "bg-rose-50 text-rose-700 border border-rose-100"
                                : "bg-amber-50 text-amber-700 border border-amber-100"
                            }`}>
                              {med.value === 0 ? "Out of Stock" : "Low Stock"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* 3. Frequently Dispensed & Recent Activity Grid */}
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Top Dispensed Table */}
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm lg:col-span-1">
              <h3 className="text-base font-bold text-slate-800 mb-4">Top 10 Dispensed</h3>
              {stats.top_dispensed_medicines.length === 0 ? (
                <div className="flex h-56 items-center justify-center border border-dashed border-slate-200 rounded-xl">
                  <span className="text-sm text-slate-400 font-medium">No sales recorded yet today.</span>
                </div>
              ) : (
                <div className="space-y-3">
                  {stats.top_dispensed_medicines.map((med, idx) => (
                    <div key={med.medicine_id} className="flex items-center justify-between p-3 rounded-xl border border-slate-50 bg-slate-50/30 hover:bg-slate-50 transition-colors duration-200">
                      <div className="flex items-center space-x-3">
                        <span className="flex h-6 w-6 items-center justify-center rounded bg-teal-50 text-xs font-bold text-teal-700">
                          {idx + 1}
                        </span>
                        <div>
                          <span className="block text-sm font-semibold text-slate-700 leading-none">{med.name}</span>
                          <span className="text-[10px] text-slate-400">{med.generic_name || "—"}</span>
                        </div>
                      </div>
                      <span className="text-sm font-extrabold text-slate-800">{med.value} units</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recent Timeline (Right) */}
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm lg:col-span-2">
              <h3 className="text-base font-bold text-slate-800 mb-5">Recent Transaction Log</h3>
              {stats.recent_activity.length === 0 ? (
                <div className="flex h-56 items-center justify-center border border-dashed border-slate-200 rounded-xl">
                  <span className="text-sm text-slate-400 font-medium">No activities recorded.</span>
                </div>
              ) : (
                <div className="relative border-l border-slate-100 ml-3.5 pl-6 space-y-6 max-h-[460px] overflow-y-auto pr-2">
                  {stats.recent_activity.map((tx) => (
                    <div key={tx.id} className="relative">
                      {/* Timeline dot */}
                      <span className={`absolute -left-[31px] top-1 flex h-4.5 w-4.5 items-center justify-center rounded-full border border-white shadow-sm ring-4 ring-white ${
                        tx.quantity_changed > 0 ? "bg-emerald-500" : "bg-teal-600"
                      }`} />

                      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2.5">
                        <div>
                          <div className="flex items-center gap-2">
                            <strong className="text-sm font-bold text-slate-700">
                              {tx.batch?.summary?.medicine?.name}
                            </strong>
                            <span className="text-[10px] text-slate-400">
                              Batch: {tx.batch?.batch_number}
                            </span>
                          </div>
                          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-400 items-center font-medium">
                            <span className="font-semibold text-teal-800 bg-teal-50 border border-teal-100 rounded px-1 text-[10px]">
                              {tx.transaction_type}
                            </span>
                            <span>By {tx.user?.first_name ?? "System"} {tx.user?.last_name ?? ""}</span>
                            {tx.branch && <span>@{tx.branch.name}</span>}
                            {tx.reason && <span className="italic text-slate-500">"{tx.reason}"</span>}
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <span className={`block text-sm font-extrabold ${
                            tx.quantity_changed > 0 ? "text-emerald-600" : "text-slate-800"
                          }`}>
                            {tx.quantity_changed > 0 ? "+" : ""}{tx.quantity_changed} units
                          </span>
                          <span className="block text-[10px] text-slate-400 font-medium">
                            {new Date(tx.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 4. Branch breakdown table (Doctor only when system-wide) */}
          {user?.role === "doctor" && !selectedBranchId && stats.branch_wise_stats.length > 0 && (
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <h3 className="text-base font-bold text-slate-800 mb-4">Branch Performance Breakdown</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-100">
                  <thead>
                    <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-400">
                      <th className="py-2.5">Branch Name</th>
                      <th className="py-2.5">Code</th>
                      <th className="py-2.5 text-right">Inventory Count</th>
                      <th className="py-2.5 text-right">Value (Cost Basis)</th>
                      <th className="py-2.5 text-right">Low Stock Warnings</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-sm">
                    {stats.branch_wise_stats.map((b) => (
                      <tr key={b.branch_id} className="hover:bg-slate-50/50">
                        <td className="py-3.5 font-semibold text-slate-800">{b.branch_name}</td>
                        <td className="py-3.5 font-bold text-slate-500">{b.branch_code}</td>
                        <td className="py-3.5 text-right font-extrabold text-slate-700">
                          {b.total_inventory_items.toLocaleString("en-IN")}
                        </td>
                        <td className="py-3.5 text-right font-extrabold text-slate-800">
                          {formatCurrency(b.total_inventory_value)}
                        </td>
                        <td className="py-3.5 text-right">
                          <span className={`inline-flex rounded px-2 py-0.5 text-xs font-bold ${
                            b.low_stock_count > 0 ? "bg-amber-50 text-amber-700 border border-amber-100" : "bg-slate-50 text-slate-400"
                          }`}>
                            {b.low_stock_count} Critical
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Dashboard;
