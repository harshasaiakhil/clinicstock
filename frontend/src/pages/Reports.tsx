import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Building,
  History,
} from "lucide-react";

import api from "../api";
import { useAuth } from "../context/AuthContext";

interface Branch {
  id: string;
  name: string;
}

interface InventorySummary {
  id: string;
  total_quantity: number;
  available_quantity: number;
  reorder_level: number;
  medicine?: {
    name: string;
    generic_name: string | null;
  };
  branch?: Branch;
}

interface InventoryBatch {
  id: string;
  batch_number: string;
  expiry_date: string | null;
  purchase_price: number;
  selling_price: number;
  quantity: number;
  summary?: {
    medicine?: {
      name: string;
    };
    branch?: Branch;
  };
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
  batch?: {
    batch_number: string;
    summary?: {
      medicine?: {
        name: string;
      };
    };
  };
}

export const Reports: React.FC = () => {
  const { user } = useAuth();
  const isDoctor = user?.role === "doctor";
  const [activeReport, setActiveReport] = useState<"low-stock" | "expiry" | "valuation" | "tx">("low-stock");
  const [selectedBranchId, setSelectedBranchId] = useState("");

  // --- Fetch branches ---
  const { data: branches = [] } = useQuery<Branch[]>({
    queryKey: ["branches"],
    queryFn: async () => (await api.get("/branches/")).data,
  });

  // --- Fetch Queries for reports ---
  const { data: lowStock = [], isLoading: loadingLow } = useQuery<InventorySummary[]>({
    queryKey: ["report-low-stock", selectedBranchId],
    queryFn: async () => {
      const params: Record<string, any> = { is_low_stock: true };
      if (selectedBranchId) params.branch_id = selectedBranchId;
      return (await api.get("/inventory/summaries", { params })).data;
    },
    enabled: activeReport === "low-stock",
  });

  const { data: expiryList = [], isLoading: loadingExp } = useQuery<InventoryBatch[]>({
    queryKey: ["report-expiry", selectedBranchId],
    queryFn: async () => {
      // is_expired=true matches expired, wait, we can fetch all batches and filter or use filter
      const params: Record<string, any> = { is_expired: true };
      if (selectedBranchId) params.branch_id = selectedBranchId;
      return (await api.get("/inventory/batches", { params })).data;
    },
    enabled: activeReport === "expiry",
  });

  const { data: valuation = [], isLoading: loadingVal } = useQuery<InventoryBatch[]>({
    queryKey: ["report-valuation", selectedBranchId],
    queryFn: async () => {
      const params: Record<string, any> = {};
      if (selectedBranchId) params.branch_id = selectedBranchId;
      return (await api.get("/inventory/batches", { params })).data;
    },
    enabled: activeReport === "valuation",
  });

  const { data: transactions = [], isLoading: loadingTx } = useQuery<StockTx[]>({
    queryKey: ["report-tx", selectedBranchId],
    queryFn: async () => {
      const params: Record<string, any> = { limit: 200 };
      if (selectedBranchId) params.branch_id = selectedBranchId;
      return (await api.get("/inventory/transactions", { params })).data;
    },
    enabled: activeReport === "tx",
  });

  const calculateTotalValuation = () => {
    return valuation.reduce((acc, curr) => acc + curr.quantity * curr.purchase_price, 0);
  };

  const calculateTotalItems = () => {
    return valuation.reduce((acc, curr) => acc + curr.quantity, 0);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight">Analytics & Reports</h2>
          <p className="text-sm text-slate-500">Query and print stock levels and valuation assessments</p>
        </div>

        {isDoctor && (
          <div className="flex items-center space-x-3 bg-white border border-slate-200 shadow-sm rounded-xl px-4 py-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Branch:</span>
            <select
              value={selectedBranchId}
              onChange={(e) => setSelectedBranchId(e.target.value)}
              className="text-sm font-semibold text-slate-800 bg-transparent focus:outline-none border-none cursor-pointer"
            >
              <option value="">All Branches</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Reports navigation grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Low Stock Card */}
        <button
          onClick={() => setActiveReport("low-stock")}
          className={`flex flex-col items-start p-5 rounded-2xl border text-left cursor-pointer transition-all duration-200 ${
            activeReport === "low-stock"
              ? "border-teal-500 bg-teal-50/20 shadow-md ring-1 ring-teal-500"
              : "border-slate-100 bg-white hover:bg-slate-50/50 shadow-sm"
          }`}
        >
          <AlertTriangle className="h-6 w-6 text-amber-500 mb-3" />
          <span className="text-sm font-bold text-slate-800">Low Stock Alert</span>
          <span className="text-[10px] text-slate-400 font-semibold mt-1">Reorder levels checked</span>
        </button>

        {/* Expiry Alerts Card */}
        <button
          onClick={() => setActiveReport("expiry")}
          className={`flex flex-col items-start p-5 rounded-2xl border text-left cursor-pointer transition-all duration-200 ${
            activeReport === "expiry"
              ? "border-teal-500 bg-teal-50/20 shadow-md ring-1 ring-teal-500"
              : "border-slate-100 bg-white hover:bg-slate-50/50 shadow-sm"
          }`}
        >
          <AlertTriangle className="h-6 w-6 text-rose-500 mb-3" />
          <span className="text-sm font-bold text-slate-800">Expired Batches</span>
          <span className="text-[10px] text-slate-400 font-semibold mt-1">Expired items tracking</span>
        </button>

        {/* Inventory Valuation Card */}
        <button
          onClick={() => setActiveReport("valuation")}
          className={`flex flex-col items-start p-5 rounded-2xl border text-left cursor-pointer transition-all duration-200 ${
            activeReport === "valuation"
              ? "border-teal-500 bg-teal-50/20 shadow-md ring-1 ring-teal-500"
              : "border-slate-100 bg-white hover:bg-slate-50/50 shadow-sm"
          }`}
        >
          <Building className="h-6 w-6 text-teal-600 mb-3" />
          <span className="text-sm font-bold text-slate-800">Valuation Ledger</span>
          <span className="text-[10px] text-slate-400 font-semibold mt-1">Total valuation checks</span>
        </button>

        {/* Transaction History Card */}
        <button
          onClick={() => setActiveReport("tx")}
          className={`flex flex-col items-start p-5 rounded-2xl border text-left cursor-pointer transition-all duration-200 ${
            activeReport === "tx"
              ? "border-teal-500 bg-teal-50/20 shadow-md ring-1 ring-teal-500"
              : "border-slate-100 bg-white hover:bg-slate-50/50 shadow-sm"
          }`}
        >
          <History className="h-6 w-6 text-sky-600 mb-3" />
          <span className="text-sm font-bold text-slate-800">Audit timeline</span>
          <span className="text-[10px] text-slate-400 font-semibold mt-1">Dispenses & stock ins logs</span>
        </button>
      </div>

      {/* Report view list */}
      <div className="rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden p-6">
        {activeReport === "low-stock" && (
          <div className="space-y-4">
            <h3 className="text-base font-bold text-slate-800">Critical Low Stock Report</h3>
            {loadingLow ? (
              <div className="h-32 flex items-center justify-center"><div className="h-6 w-6 animate-spin rounded-full border-2 border-teal-600 border-t-transparent"></div></div>
            ) : lowStock.length === 0 ? (
              <p className="text-sm text-slate-400 italic">No low stock warnings triggered.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-100 text-sm">
                  <thead>
                    <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-400">
                      <th className="py-2.5">Medicine Name</th>
                      <th className="py-2.5">Branch</th>
                      <th className="py-2.5 text-right">Available Stock</th>
                      <th className="py-2.5 text-right">Reorder level</th>
                      <th className="py-2.5 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {lowStock.map((s) => (
                      <tr key={s.id}>
                        <td className="py-3 font-semibold text-slate-700">{s.medicine?.name}</td>
                        <td className="py-3 text-slate-500">{s.branch?.name}</td>
                        <td className="py-3 text-right font-extrabold text-slate-800">{s.available_quantity}</td>
                        <td className="py-3 text-right text-slate-400 font-semibold">{s.reorder_level}</td>
                        <td className="py-3 text-right">
                          <span className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                            s.available_quantity === 0 ? "bg-rose-50 text-rose-700" : "bg-amber-50 text-amber-700"
                          }`}>
                            {s.available_quantity === 0 ? "Out of Stock" : "Low Stock"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeReport === "expiry" && (
          <div className="space-y-4">
            <h3 className="text-base font-bold text-slate-800">Expired Inventory Batches</h3>
            {loadingExp ? (
              <div className="h-32 flex items-center justify-center"><div className="h-6 w-6 animate-spin rounded-full border-2 border-teal-600 border-t-transparent"></div></div>
            ) : expiryList.length === 0 ? (
              <p className="text-sm text-slate-400 italic">No expired stock batches detected.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-100 text-sm">
                  <thead>
                    <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-400">
                      <th className="py-2.5">Medicine Name</th>
                      <th className="py-2.5">Batch</th>
                      <th className="py-2.5">Branch</th>
                      <th className="py-2.5 text-center">Expiry Date</th>
                      <th className="py-2.5 text-right">Quantity</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {expiryList.map((b) => (
                      <tr key={b.id}>
                        <td className="py-3 font-semibold text-slate-700">{b.summary?.medicine?.name}</td>
                        <td className="py-3 font-bold text-slate-500">{b.batch_number}</td>
                        <td className="py-3 text-slate-500">{b.summary?.branch?.name}</td>
                        <td className="py-3 text-center">
                          <span className="inline-flex rounded bg-rose-50 px-1.5 py-0.5 text-[10px] font-bold text-rose-700">
                            {b.expiry_date}
                          </span>
                        </td>
                        <td className="py-3 text-right font-extrabold text-rose-600">{b.quantity}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeReport === "valuation" && (
          <div className="space-y-6">
            <div className="flex justify-between items-center bg-slate-50 p-5 rounded-2xl border border-slate-100">
              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Value (Cost basis)</span>
                <h4 className="text-2xl font-extrabold text-teal-800 mt-1">
                  ₹{calculateTotalValuation().toLocaleString("en-IN")}
                </h4>
              </div>
              <div className="text-right">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Stock units</span>
                <h4 className="text-2xl font-extrabold text-slate-800 mt-1">
                  {calculateTotalItems().toLocaleString("en-IN")}
                </h4>
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-bold text-slate-800">Inventory Valuation Breakdowns</h3>
              {loadingVal ? (
                <div className="h-32 flex items-center justify-center"><div className="h-6 w-6 animate-spin rounded-full border-2 border-teal-600 border-t-transparent"></div></div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-100 text-sm">
                    <thead>
                      <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-400">
                        <th className="py-2.5">Medicine Name</th>
                        <th className="py-2.5">Batch</th>
                        <th className="py-2.5">Branch</th>
                        <th className="py-2.5 text-right">Available Qty</th>
                        <th className="py-2.5 text-right">Unit Price</th>
                        <th className="py-2.5 text-right">Total Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {valuation.map((b) => (
                        <tr key={b.id}>
                          <td className="py-3 font-semibold text-slate-700">{b.summary?.medicine?.name}</td>
                          <td className="py-3 text-slate-500 font-bold">{b.batch_number}</td>
                          <td className="py-3 text-slate-400 font-medium">{b.summary?.branch?.name}</td>
                          <td className="py-3 text-right font-extrabold text-slate-700">{b.quantity}</td>
                          <td className="py-3 text-right font-semibold text-slate-500">₹{b.purchase_price.toFixed(2)}</td>
                          <td className="py-3 text-right font-extrabold text-slate-800">
                            ₹{(b.quantity * b.purchase_price).toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {activeReport === "tx" && (
          <div className="space-y-4">
            <h3 className="text-base font-bold text-slate-800">Transaction History Audits</h3>
            {loadingTx ? (
              <div className="h-32 flex items-center justify-center"><div className="h-6 w-6 animate-spin rounded-full border-2 border-teal-600 border-t-transparent"></div></div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-100 text-sm">
                  <thead>
                    <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-400">
                      <th className="py-2.5">Timestamp</th>
                      <th className="py-2.5">Branch</th>
                      <th className="py-2.5">Medicine</th>
                      <th className="py-2.5">Type</th>
                      <th className="py-2.5 text-right">Delta</th>
                      <th className="py-2.5">Operator</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {transactions.map((tx) => (
                      <tr key={tx.id} className="hover:bg-slate-50/50">
                        <td className="py-3 text-slate-400 text-xs">
                          {new Date(tx.timestamp).toLocaleString()}
                        </td>
                        <td className="py-3 font-medium text-slate-600">{tx.branch?.name}</td>
                        <td className="py-3 font-semibold text-slate-700">{tx.batch?.summary?.medicine?.name}</td>
                        <td className="py-3">
                          <span className="inline-flex rounded bg-slate-50 border px-1.5 py-0.5 text-[10px] font-bold text-slate-700">
                            {tx.transaction_type}
                          </span>
                        </td>
                        <td className={`py-3 text-right font-extrabold ${tx.quantity_changed > 0 ? "text-emerald-600" : "text-slate-800"}`}>
                          {tx.quantity_changed > 0 ? "+" : ""}{tx.quantity_changed}
                        </td>
                        <td className="py-3 text-slate-500 text-xs">
                          {tx.user?.first_name} {tx.user?.last_name}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
