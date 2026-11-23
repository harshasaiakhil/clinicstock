import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as zod from "zod";
import {
  Plus,
  ArrowRight,
  TrendingDown,
  Sliders,
  FileText,
  Boxes,
} from "lucide-react";

import api from "../api";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";

// --- Types ---
interface Medicine {
  id: string;
  name: string;
  generic_name: string | null;
}

interface Branch {
  id: string;
  name: string;
}

interface Supplier {
  id: string;
  name: string;
}

interface InventorySummary {
  id: string;
  medicine_id: string;
  branch_id: string;
  total_quantity: number;
  available_quantity: number;
  min_stock_level: number;
  reorder_level: number;
  building: string | null;
  room: string | null;
  cupboard: string | null;
  rack: string | null;
  shelf: string | null;
  medicine?: Medicine;
  branch?: Branch;
}

interface InventoryBatch {
  id: string;
  inventory_summary_id: string;
  batch_number: string;
  supplier_id: string | null;
  purchase_date: string | null;
  expiry_date: string | null;
  purchase_price: number;
  selling_price: number;
  quantity: number;
  building: string | null;
  room: string | null;
  cupboard: string | null;
  rack: string | null;
  shelf: string | null;
  supplier?: Supplier;
  summary?: {
    branch_id: string;
    branch?: Branch;
    medicine?: Medicine;
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
      medicine?: Medicine;
    };
  };
}

// --- Validation Schemas ---

const stockInSchema = zod.object({
  medicine_id: zod.string().uuid("Invalid medicine"),
  branch_id: zod.string().uuid("Invalid branch"),
  batch_number: zod.string().min(1, "Batch number required").max(100),
  supplier_id: zod.string().uuid("Invalid supplier").nullable().optional().or(zod.literal("")),
  purchase_date: zod.string().nullable().optional().or(zod.literal("")),
  expiry_date: zod.string().nullable().optional().or(zod.literal("")),
  purchase_price: zod.coerce.number().nonnegative("Cannot be negative"),
  selling_price: zod.coerce.number().nonnegative("Cannot be negative"),
  quantity: zod.coerce.number().int().gt(0, "Quantity must be greater than 0"),
  building: zod.string().max(100).nullable().optional().or(zod.literal("")),
  room: zod.string().max(100).nullable().optional().or(zod.literal("")),
  cupboard: zod.string().max(100).nullable().optional().or(zod.literal("")),
  rack: zod.string().max(100).nullable().optional().or(zod.literal("")),
  shelf: zod.string().max(100).nullable().optional().or(zod.literal("")),
  reason: zod.string().max(255).nullable().optional().or(zod.literal("")),
});

const dispenseSchema = zod.object({
  batch_id: zod.string().uuid("Invalid batch"),
  quantity: zod.coerce.number().int().gt(0, "Quantity must be greater than 0"),
  reason: zod.string().max(255).nullable().optional().or(zod.literal("")),
});

const transferSchema = zod.object({
  batch_id: zod.string().uuid("Invalid batch"),
  to_branch_id: zod.string().uuid("Invalid branch"),
  quantity: zod.coerce.number().int().gt(0, "Quantity must be greater than 0"),
  reason: zod.string().max(255).nullable().optional().or(zod.literal("")),
});

const adjustSchema = zod.object({
  batch_id: zod.string().uuid("Invalid batch"),
  quantity_changed: zod.coerce.number().int("Quantity must be an integer"),
  transaction_type: zod.string().min(1, "Select adjustment type"),
  reason: zod.string().max(255).nullable().optional().or(zod.literal("")),
});

export const Inventory: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const isDoctor = user?.role === "doctor";

  // --- UI state ---
  const [activeTab, setActiveTab] = useState<"summary" | "batches" | "tx">("summary");
  const [selectedBranchId, setSelectedBranchId] = useState("");

  // Modals status
  const [modalOpen, setModalOpen] = useState<"stock-in" | "dispense" | "transfer" | "adjust" | null>(null);

  // --- Fetch Core Masters ---
  const { data: medicines = [] } = useQuery<Medicine[]>({
    queryKey: ["medicines-min"],
    queryFn: async () => (await api.get("/medicines/", { params: { limit: 1000 } })).data,
  });

  const { data: branches = [] } = useQuery<Branch[]>({
    queryKey: ["branches"],
    queryFn: async () => (await api.get("/branches/")).data,
  });

  const { data: suppliers = [] } = useQuery<Supplier[]>({
    queryKey: ["suppliers"],
    queryFn: async () => (await api.get("/suppliers/")).data,
  });

  // --- Fetch Queries for active tab ---
  const { data: summaries = [], isLoading: loadingSummary } = useQuery<InventorySummary[]>({
    queryKey: ["inventory-summaries", selectedBranchId],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (selectedBranchId) params.branch_id = selectedBranchId;
      const res = await api.get("/inventory/summaries", { params });
      return res.data;
    },
    enabled: activeTab === "summary",
  });

  const { data: batches = [], isLoading: loadingBatches } = useQuery<InventoryBatch[]>({
    queryKey: ["inventory-batches", selectedBranchId],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (selectedBranchId) params.branch_id = selectedBranchId;
      const res = await api.get("/inventory/batches", { params });
      return res.data;
    },
    enabled: activeTab === "batches",
  });

  const { data: transactions = [], isLoading: loadingTx } = useQuery<StockTx[]>({
    queryKey: ["inventory-tx", selectedBranchId],
    queryFn: async () => {
      const params: Record<string, any> = { limit: 100 };
      if (selectedBranchId) params.branch_id = selectedBranchId;
      const res = await api.get("/inventory/transactions", { params });
      return res.data;
    },
    enabled: activeTab === "tx",
  });

  // --- Forms Instantiations ---
  const stockInForm = useForm({
    resolver: zodResolver(stockInSchema),
    defaultValues: { purchase_price: 0, selling_price: 0 } as any,
  });

  const dispenseForm = useForm({
    resolver: zodResolver(dispenseSchema),
  });

  const transferForm = useForm({
    resolver: zodResolver(transferSchema),
  });

  const adjustForm = useForm({
    resolver: zodResolver(adjustSchema),
  });

  // --- Mutations ---
  const actionMutation = useMutation({
    mutationFn: async ({ path, data }: { path: string; data: any }) => {
      const res = await api.post(`/inventory/${path}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory-summaries"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-batches"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-tx"] });
      setModalOpen(null);
      // Reset forms
      stockInForm.reset();
      dispenseForm.reset();
      transferForm.reset();
      adjustForm.reset();
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || "Operation failed. Check stock levels or expiry dates.");
    },
  });

  const handleStockIn = (data: any) => {
    // Clean nulls
    if (!data.supplier_id) delete data.supplier_id;
    if (!data.purchase_date) delete data.purchase_date;
    if (!data.expiry_date) delete data.expiry_date;
    actionMutation.mutate({ path: "stock-in", data });
  };

  const handleDispense = (data: any) => {
    actionMutation.mutate({ path: "dispense", data });
  };

  const handleTransfer = (data: any) => {
    actionMutation.mutate({ path: "transfer", data });
  };

  const handleAdjust = (data: any) => {
    actionMutation.mutate({ path: "adjust", data });
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight">Stock Inventory</h2>
          <p className="text-sm text-slate-500">Coordinate batch receipts, branches transfers, and dispense logs</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Dispatch actions */}
          <Button variant="outline" size="sm" onClick={() => setModalOpen("dispense")}>
            <TrendingDown className="mr-2 h-4 w-4 text-sky-600" />
            Dispense
          </Button>
          {isDoctor && (
            <>
              <Button variant="outline" size="sm" onClick={() => setModalOpen("transfer")}>
                <ArrowRight className="mr-2 h-4 w-4 text-purple-600" />
                Transfer Stock
              </Button>
              <Button variant="outline" size="sm" onClick={() => setModalOpen("adjust")}>
                <Sliders className="mr-2 h-4 w-4 text-slate-500" />
                Adjust Stock
              </Button>
              <Button size="sm" onClick={() => setModalOpen("stock-in")}>
                <Plus className="mr-2 h-4 w-4 text-white" />
                Stock In
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Tabs & Branch Filter */}
      <div className="flex flex-col md:flex-row justify-between gap-4">
        {/* Navigation tabs */}
        <div className="flex space-x-1.5 bg-slate-100 rounded-xl p-1 shrink-0 self-start">
          <button
            onClick={() => setActiveTab("summary")}
            className={`rounded-lg px-4 py-2 text-xs font-bold transition-all duration-200 cursor-pointer ${
              activeTab === "summary" ? "bg-white text-slate-800 shadow" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            Inventory Summary
          </button>
          <button
            onClick={() => setActiveTab("batches")}
            className={`rounded-lg px-4 py-2 text-xs font-bold transition-all duration-200 cursor-pointer ${
              activeTab === "batches" ? "bg-white text-slate-800 shadow" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            Batches list
          </button>
          <button
            onClick={() => setActiveTab("tx")}
            className={`rounded-lg px-4 py-2 text-xs font-bold transition-all duration-200 cursor-pointer ${
              activeTab === "tx" ? "bg-white text-slate-800 shadow" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            Audit Log Timeline
          </button>
        </div>

        {/* Global branch query filter (Doctors only) */}
        {isDoctor && (
          <div className="flex items-center space-x-3 bg-white border border-slate-200 shadow-sm rounded-xl px-4 py-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Filter Branch:</span>
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

      {/* --- CONTENT TABS SWITCH --- */}

      {activeTab === "summary" && (
        <div className="rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
          {loadingSummary ? (
            <div className="flex h-64 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-600 border-t-transparent"></div>
            </div>
          ) : summaries.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center border-2 border-dashed border-slate-100 m-6 rounded-2xl">
              <Boxes className="h-10 w-10 text-slate-300 mb-2" />
              <span className="text-sm text-slate-500 font-semibold">No stock summaries found</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-100">
                <thead>
                  <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-400 bg-slate-50">
                    <th className="px-6 py-4">Medicine</th>
                    <th className="px-6 py-4">Branch</th>
                    <th className="px-6 py-4 text-right">Available Stock</th>
                    <th className="px-6 py-4 text-right">Reorder Level</th>
                    <th className="px-6 py-4">Location</th>
                    <th className="px-6 py-4 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm">
                  {summaries.map((s) => (
                    <tr key={s.id} className="hover:bg-slate-50/50">
                      <td className="px-6 py-4 font-semibold text-slate-800">{s.medicine?.name}</td>
                      <td className="px-6 py-4 text-slate-600 font-medium">{s.branch?.name}</td>
                      <td className="px-6 py-4 text-right font-extrabold text-slate-800">
                        {s.available_quantity} units
                      </td>
                      <td className="px-6 py-4 text-right font-semibold text-slate-400">
                        {s.reorder_level} units
                      </td>
                      <td className="px-6 py-4 text-slate-500">
                        {s.building || s.room ? `${s.building || ""} -> ${s.room || ""}` : "—"}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                          s.available_quantity === 0
                            ? "bg-rose-50 text-rose-700 border border-rose-100"
                            : s.available_quantity <= s.reorder_level
                            ? "bg-amber-50 text-amber-700 border border-amber-100"
                            : "bg-emerald-50 text-emerald-700 border border-emerald-100"
                        }`}>
                          {s.available_quantity === 0 ? "Out of Stock" : s.available_quantity <= s.reorder_level ? "Low Stock" : "Healthy"}
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

      {activeTab === "batches" && (
        <div className="rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
          {loadingBatches ? (
            <div className="flex h-64 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-600 border-t-transparent"></div>
            </div>
          ) : batches.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center border-2 border-dashed border-slate-100 m-6 rounded-2xl">
              <Boxes className="h-10 w-10 text-slate-300 mb-2" />
              <span className="text-sm text-slate-500 font-semibold">No stock batches found</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-100">
                <thead>
                  <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-400 bg-slate-50">
                    <th className="px-6 py-4">Medicine</th>
                    <th className="px-6 py-4">Batch No.</th>
                    <th className="px-6 py-4">Branch</th>
                    <th className="px-6 py-4 text-right">Qty</th>
                    <th className="px-6 py-4 text-right">Selling Price</th>
                    <th className="px-6 py-4 text-center">Expiry</th>
                    <th className="px-6 py-4">Supplier</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm">
                  {batches.map((b) => (
                    <tr key={b.id} className="hover:bg-slate-50/50">
                      <td className="px-6 py-4 font-semibold text-slate-800">{b.summary?.medicine?.name}</td>
                      <td className="px-6 py-4 font-bold text-slate-600">{b.batch_number}</td>
                      <td className="px-6 py-4 text-slate-500 font-semibold">{b.summary?.branch?.name}</td>
                      <td className="px-6 py-4 text-right font-extrabold text-slate-800">{b.quantity}</td>
                      <td className="px-6 py-4 text-right font-semibold text-slate-800">₹{b.selling_price.toFixed(2)}</td>
                      <td className="px-6 py-4 text-center">
                        {b.expiry_date ? (
                          <span className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold ${
                            new Date(b.expiry_date) < new Date()
                              ? "bg-rose-50 text-rose-700 border border-rose-100"
                              : "bg-slate-50 text-slate-700"
                          }`}>
                            {b.expiry_date}
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-slate-400">{b.supplier?.name || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "tx" && (
        <div className="rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden p-6">
          {loadingTx ? (
            <div className="flex h-64 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-600 border-t-transparent"></div>
            </div>
          ) : transactions.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center border-2 border-dashed border-slate-100 rounded-2xl">
              <FileText className="h-10 w-10 text-slate-300 mb-2" />
              <span className="text-sm text-slate-500 font-semibold">No stock transactions logged</span>
            </div>
          ) : (
            <div className="relative border-l border-slate-100 ml-4 pl-6 space-y-6">
              {transactions.map((tx) => (
                <div key={tx.id} className="relative">
                  <span className={`absolute -left-[32px] top-1 h-4 w-4 rounded-full border-2 border-white ring-4 ring-white ${
                    tx.quantity_changed > 0 ? "bg-emerald-500" : "bg-sky-600"
                  }`} />
                  <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <strong className="text-sm text-slate-800 font-bold">{tx.batch?.summary?.medicine?.name}</strong>
                        <span className="text-[10px] text-slate-400 font-semibold">Batch: {tx.batch?.batch_number}</span>
                      </div>
                      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-400 items-center font-medium">
                        <span className="font-semibold text-teal-800 bg-teal-50 border border-teal-100 rounded px-1.5 text-[10px]">
                          {tx.transaction_type}
                        </span>
                        <span>By {tx.user?.first_name ?? "System"} {tx.user?.last_name ?? ""}</span>
                        <span>@{tx.branch?.name ?? "Unknown Branch"}</span>
                        {tx.reason && <span className="italic text-slate-500">"{tx.reason}"</span>}
                      </div>
                    </div>
                    <div className="text-right whitespace-nowrap shrink-0">
                      <span className={`block text-sm font-extrabold ${tx.quantity_changed > 0 ? "text-emerald-600" : "text-slate-800"}`}>
                        {tx.quantity_changed > 0 ? "+" : ""}{tx.quantity_changed} units
                      </span>
                      <span className="text-[10px] text-slate-400 font-medium">{new Date(tx.timestamp).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* --- STOCK IN MODAL --- */}
      <Modal isOpen={modalOpen === "stock-in"} onClose={() => setModalOpen(null)} title="Stock In Dilutions" size="lg">
        <form onSubmit={stockInForm.handleSubmit(handleStockIn)} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Dilution Medicine *</label>
              <select
                required
                {...stockInForm.register("medicine_id")}
                className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-teal-500"
              >
                <option value="">Select Medicine</option>
                {medicines.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Target Branch *</label>
              <select
                required
                {...stockInForm.register("branch_id")}
                className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-teal-500"
              >
                <option value="">Select Branch</option>
                {branches.map((b) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Batch Number *</label>
              <input
                type="text"
                required
                placeholder="e.g. BATCH-SBL-001"
                {...stockInForm.register("batch_number")}
                className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-teal-500"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Supplier</label>
              <select
                {...stockInForm.register("supplier_id")}
                className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-teal-500"
              >
                <option value="">Select Supplier</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Quantity *</label>
              <input
                type="number"
                required
                {...stockInForm.register("quantity")}
                className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-teal-500"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Expiry Date</label>
              <input
                type="date"
                {...stockInForm.register("expiry_date")}
                className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-teal-500"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Purchase Price *</label>
              <input
                type="number"
                step="0.01"
                required
                {...stockInForm.register("purchase_price")}
                className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-teal-500"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Selling Price *</label>
              <input
                type="number"
                step="0.01"
                required
                {...stockInForm.register("selling_price")}
                className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-teal-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase">Building</label>
              <input type="text" {...stockInForm.register("building")} className="mt-1 block w-full rounded border p-2 text-xs focus:outline-none" />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase">Room</label>
              <input type="text" {...stockInForm.register("room")} className="mt-1 block w-full rounded border p-2 text-xs focus:outline-none" />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase">Cupboard</label>
              <input type="text" {...stockInForm.register("cupboard")} className="mt-1 block w-full rounded border p-2 text-xs focus:outline-none" />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase">Rack</label>
              <input type="text" {...stockInForm.register("rack")} className="mt-1 block w-full rounded border p-2 text-xs focus:outline-none" />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase">Shelf</label>
              <input type="text" {...stockInForm.register("shelf")} className="mt-1 block w-full rounded border p-2 text-xs focus:outline-none" />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Reason / Notes</label>
            <textarea
              {...stockInForm.register("reason")}
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none"
              rows={2}
            />
          </div>

          <div className="flex justify-end space-x-3 border-t pt-4">
            <Button variant="outline" type="button" onClick={() => setModalOpen(null)}>Cancel</Button>
            <Button type="submit">Complete Stock In</Button>
          </div>
        </form>
      </Modal>

      {/* --- DISPENSE MODAL --- */}
      <Modal isOpen={modalOpen === "dispense"} onClose={() => setModalOpen(null)} title="Dispense Dilutions" size="md">
        <form onSubmit={dispenseForm.handleSubmit(handleDispense)} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Select Available Batch *</label>
            <select
              required
              {...dispenseForm.register("batch_id")}
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-teal-500"
            >
              <option value="">Select Batch</option>
              {batches.filter(b => b.quantity > 0).map((b) => (
                <option key={b.id} value={b.id}>
                  {b.summary?.medicine?.name} (Batch: {b.batch_number} | Stock: {b.quantity} | {b.summary?.branch?.name})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Dispense Quantity *</label>
            <input
              type="number"
              required
              {...dispenseForm.register("quantity")}
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Dispense Reason / Notes</label>
            <textarea
              {...dispenseForm.register("reason")}
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none"
              rows={2}
            />
          </div>

          <div className="flex justify-end space-x-3 border-t pt-4">
            <Button variant="outline" type="button" onClick={() => setModalOpen(null)}>Cancel</Button>
            <Button type="submit" variant="primary">Confirm Dispensation</Button>
          </div>
        </form>
      </Modal>

      {/* --- TRANSFER MODAL --- */}
      <Modal isOpen={modalOpen === "transfer"} onClose={() => setModalOpen(null)} title="Cross-Branch Transfer" size="md">
        <form onSubmit={transferForm.handleSubmit(handleTransfer)} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Select Source Batch *</label>
            <select
              required
              {...transferForm.register("batch_id")}
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-teal-500"
            >
              <option value="">Select Batch</option>
              {batches.filter(b => b.quantity > 0).map((b) => (
                <option key={b.id} value={b.id}>
                  {b.summary?.medicine?.name} ({b.summary?.branch?.name} | Batch: {b.batch_number} | Stock: {b.quantity})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Destination Branch *</label>
            <select
              required
              {...transferForm.register("to_branch_id")}
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-teal-500"
            >
              <option value="">Select Destination Branch</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Transfer Quantity *</label>
            <input
              type="number"
              required
              {...transferForm.register("quantity")}
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Reason / Notes</label>
            <textarea
              {...transferForm.register("reason")}
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none"
              rows={2}
            />
          </div>

          <div className="flex justify-end space-x-3 border-t pt-4">
            <Button variant="outline" type="button" onClick={() => setModalOpen(null)}>Cancel</Button>
            <Button type="submit">Dispatch Transfer</Button>
          </div>
        </form>
      </Modal>

      {/* --- ADJUST STOCK MODAL --- */}
      <Modal isOpen={modalOpen === "adjust"} onClose={() => setModalOpen(null)} title="Manual Stock Adjustment" size="md">
        <form onSubmit={adjustForm.handleSubmit(handleAdjust)} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Select Target Batch *</label>
            <select
              required
              {...adjustForm.register("batch_id")}
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-teal-500"
            >
              <option value="">Select Batch</option>
              {batches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.summary?.medicine?.name} ({b.summary?.branch?.name} | Batch: {b.batch_number} | Stock: {b.quantity})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Adjustment Type *</label>
            <select
              required
              {...adjustForm.register("transaction_type")}
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white focus:border-teal-500"
            >
              <option value="">Select Category</option>
              <option value="Adjustment">Generic Adjustment</option>
              <option value="Expired">Expired Stock Out</option>
              <option value="Damaged">Damaged / Broken Bottle</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Quantity Delta *</label>
            <input
              type="number"
              required
              placeholder="e.g. +5 or -2"
              {...adjustForm.register("quantity_changed")}
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none focus:bg-white"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Reason / Notes *</label>
            <textarea
              required
              {...adjustForm.register("reason")}
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-sm text-slate-800 focus:outline-none"
              rows={2}
            />
          </div>

          <div className="flex justify-end space-x-3 border-t pt-4">
            <Button variant="outline" type="button" onClick={() => setModalOpen(null)}>Cancel</Button>
            <Button type="submit">Commit Adjustment</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
