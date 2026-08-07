import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as zod from "zod";
import { Plus, Edit2, Trash2, Folder } from "lucide-react";

import api from "../api";
import { useUser } from "../hooks/useUser";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";

// --- Schema Definitions ---
const genericSchema = zod.object({
  name: zod.string().min(1, "Name is required").max(100),
  description: zod.string().max(255).optional().or(zod.literal("")),
});

const supplierSchema = zod.object({
  name: zod.string().min(1, "Name is required").max(100),
  contact_person: zod.string().max(100).optional().or(zod.literal("")),
  phone: zod.string().max(20).optional().or(zod.literal("")),
  email: zod.string().email("Invalid email").optional().or(zod.literal("")),
  address: zod.string().max(255).optional().or(zod.literal("")),
});

const unitSchema = zod.object({
  name: zod.string().min(1, "Name is required").max(100),
  code: zod.string().min(1, "Code is required").max(10),
});

export const MasterData: React.FC = () => {
  const { user } = useUser();
  const queryClient = useQueryClient();
  const isDoctor = user?.role === "doctor";

  // --- UI tabs ---
  const [activeTab, setActiveTab] = useState<"categories" | "manufacturers" | "suppliers" | "units" | "potencies">("categories");

  // --- Modals state ---
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<any>(null);

  // Forms setup
  const genericForm = useForm<zod.infer<typeof genericSchema>>({ resolver: zodResolver(genericSchema) });
  const supplierForm = useForm<zod.infer<typeof supplierSchema>>({ resolver: zodResolver(supplierSchema) });
  const unitForm = useForm<zod.infer<typeof unitSchema>>({ resolver: zodResolver(unitSchema) });

  // Map endpoints & query key to active tab
  const getTabConfig = () => {
    switch (activeTab) {
      case "categories":
        return { path: "/categories", key: "categories", form: genericForm };
      case "manufacturers":
        return { path: "/manufacturers", key: "manufacturers", form: genericForm };
      case "suppliers":
        return { path: "/suppliers", key: "suppliers", form: supplierForm };
      case "units":
        return { path: "/medicine-units", key: "units", form: unitForm };
      case "potencies":
        return { path: "/potencies", key: "potencies", form: genericForm };
    }
  };

  const { path, key, form } = getTabConfig();

  // --- Fetch List query ---
  const { data: items = [], isLoading } = useQuery<any[]>({
    queryKey: [key],
    queryFn: async () => (await api.get(`${path}/`)).data,
  });

  // --- Mutations ---
  const createMutation = useMutation({
    mutationFn: async (data: any) => (await api.post(`${path}/`, data)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [key] });
      setIsAddModalOpen(false);
      form.reset();
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: any }) => (await api.put(`${path}/${id}`, data)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [key] });
      setIsEditModalOpen(false);
      setSelectedItem(null);
      form.reset();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => (await api.delete(`${path}/${id}`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [key] });
    },
  });

  // --- Handlers ---
  const handleAddSubmit = (data: any) => {
    createMutation.mutate(data);
  };

  const handleEditSubmit = (data: any) => {
    if (selectedItem) {
      updateMutation.mutate({ id: selectedItem.id, data });
    }
  };

  const openEdit = (item: any) => {
    setSelectedItem(item);
    setIsEditModalOpen(true);
    if (activeTab === "suppliers") {
      supplierForm.reset({
        name: item.name,
        contact_person: item.contact_person || "",
        phone: item.phone || "",
        email: item.email || "",
        address: item.address || "",
      });
    } else if (activeTab === "units") {
      unitForm.reset({
        name: item.name,
        code: item.code,
      });
    } else {
      genericForm.reset({
        name: item.name,
        description: item.description || "",
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight">Master data Settings</h2>
          <p className="text-sm text-slate-500">Configure catalog options and key entities values</p>
        </div>

        {isDoctor && (
          <Button size="sm" onClick={() => { form.reset(); setIsAddModalOpen(true); }}>
            <Plus className="mr-2 h-4 w-4 text-white" />
            Add New Record
          </Button>
        )}
      </div>

      {/* Navigation tabs */}
      <div className="flex flex-wrap gap-2 bg-slate-100 rounded-xl p-1 shrink-0 self-start max-w-max">
        {(["categories", "manufacturers", "suppliers", "units", "potencies"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => { setActiveTab(tab); }}
            className={`rounded-lg px-4 py-2 text-xs font-bold transition-all duration-200 cursor-pointer capitalize ${
              activeTab === tab ? "bg-white text-slate-800 shadow" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Main List Table */}
      <div className="rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-600 border-t-transparent"></div>
          </div>
        ) : items.length === 0 ? (
          <div className="flex h-64 flex-col items-center justify-center border-2 border-dashed border-slate-100 m-6 rounded-2xl">
            <Folder className="h-10 w-10 text-slate-300 mb-2" />
            <span className="text-sm text-slate-500 font-semibold">No records found</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100">
              <thead>
                <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-400 bg-slate-50">
                  <th className="px-6 py-4">Name</th>
                  {activeTab === "units" && <th className="px-6 py-4">Code</th>}
                  {activeTab === "suppliers" && (
                    <>
                      <th className="px-6 py-4">Contact</th>
                      <th className="px-6 py-4">Phone</th>
                      <th className="px-6 py-4">Email</th>
                    </>
                  )}
                  {activeTab !== "units" && activeTab !== "suppliers" && <th className="px-6 py-4">Description</th>}
                  {isDoctor && <th className="px-6 py-4 text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/50">
                    <td className="px-6 py-4 font-semibold text-slate-800">{item.name}</td>
                    {activeTab === "units" && <td className="px-6 py-4 text-slate-500 font-bold">{item.code}</td>}
                    {activeTab === "suppliers" && (
                      <>
                        <td className="px-6 py-4 text-slate-600">{item.contact_person || "—"}</td>
                        <td className="px-6 py-4 text-slate-500">{item.phone || "—"}</td>
                        <td className="px-6 py-4 text-slate-500">{item.email || "—"}</td>
                      </>
                    )}
                    {activeTab !== "units" && activeTab !== "suppliers" && (
                      <td className="px-6 py-4 text-slate-400">{item.description || "—"}</td>
                    )}
                    {isDoctor && (
                      <td className="px-6 py-4 text-right space-x-1 whitespace-nowrap">
                        <Button variant="outline" size="sm" className="p-2" onClick={() => openEdit(item)}>
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="p-2 text-rose-600 hover:bg-rose-50"
                          onClick={() => {
                            if (window.confirm("Are you sure you want to delete this record?")) {
                              deleteMutation.mutate(item.id);
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* --- ADD MODAL --- */}
      <Modal isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)} title={`Add ${activeTab.slice(0, -1)}`}>
        {activeTab === "suppliers" ? (
          <form onSubmit={supplierForm.handleSubmit(handleAddSubmit)} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Supplier Name *</label>
              <input type="text" required {...supplierForm.register("name")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Contact Person</label>
              <input type="text" {...supplierForm.register("contact_person")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Phone Number</label>
              <input type="text" {...supplierForm.register("phone")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Email Address</label>
              <input type="email" {...supplierForm.register("email")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Address</label>
              <textarea {...supplierForm.register("address")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" rows={2} />
            </div>
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <Button variant="outline" type="button" onClick={() => setIsAddModalOpen(false)}>Cancel</Button>
              <Button type="submit">Create Record</Button>
            </div>
          </form>
        ) : activeTab === "units" ? (
          <form onSubmit={unitForm.handleSubmit(handleAddSubmit)} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Unit Name *</label>
              <input type="text" required {...unitForm.register("name")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Unit Code (short) *</label>
              <input type="text" required placeholder="e.g. BTL" {...unitForm.register("code")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <Button variant="outline" type="button" onClick={() => setIsAddModalOpen(false)}>Cancel</Button>
              <Button type="submit">Create Record</Button>
            </div>
          </form>
        ) : (
          <form onSubmit={genericForm.handleSubmit(handleAddSubmit)} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Name *</label>
              <input type="text" required {...genericForm.register("name")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Description</label>
              <textarea {...genericForm.register("description")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" rows={3} />
            </div>
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <Button variant="outline" type="button" onClick={() => setIsAddModalOpen(false)}>Cancel</Button>
              <Button type="submit">Create Record</Button>
            </div>
          </form>
        )}
      </Modal>

      {/* --- EDIT MODAL --- */}
      <Modal isOpen={isEditModalOpen} onClose={() => setIsEditModalOpen(false)} title={`Edit ${activeTab.slice(0, -1)}`}>
        {activeTab === "suppliers" ? (
          <form onSubmit={supplierForm.handleSubmit(handleEditSubmit)} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Supplier Name *</label>
              <input type="text" required {...supplierForm.register("name")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Contact Person</label>
              <input type="text" {...supplierForm.register("contact_person")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Phone Number</label>
              <input type="text" {...supplierForm.register("phone")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Email Address</label>
              <input type="email" {...supplierForm.register("email")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Address</label>
              <textarea {...supplierForm.register("address")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" rows={2} />
            </div>
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <Button variant="outline" type="button" onClick={() => setIsEditModalOpen(false)}>Cancel</Button>
              <Button type="submit">Save Changes</Button>
            </div>
          </form>
        ) : activeTab === "units" ? (
          <form onSubmit={unitForm.handleSubmit(handleEditSubmit)} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Unit Name *</label>
              <input type="text" required {...unitForm.register("name")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Unit Code (short) *</label>
              <input type="text" required placeholder="e.g. BTL" {...unitForm.register("code")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <Button variant="outline" type="button" onClick={() => setIsEditModalOpen(false)}>Cancel</Button>
              <Button type="submit">Save Changes</Button>
            </div>
          </form>
        ) : (
          <form onSubmit={genericForm.handleSubmit(handleEditSubmit)} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Name *</label>
              <input type="text" required {...genericForm.register("name")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Description</label>
              <textarea {...genericForm.register("description")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" rows={3} />
            </div>
            <div className="flex justify-end space-x-3 pt-4 border-t">
              <Button variant="outline" type="button" onClick={() => setIsEditModalOpen(false)}>Cancel</Button>
              <Button type="submit">Save Changes</Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
};


