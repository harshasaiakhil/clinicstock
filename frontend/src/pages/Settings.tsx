import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as zod from "zod";
import { Plus, Landmark } from "lucide-react";

import api from "../api";
import { useUser } from "../hooks/useUser";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";

// --- Types ---
interface Branch {
  id: string;
  name: string;
  code: string;
}

interface UserProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  is_active: boolean;
  default_branch_id: string;
  default_branch?: Branch;
}

// --- Validation Schemas ---

const userCreateSchema = zod.object({
  email: zod.string().email("Invalid email"),
  password: zod.string().min(6, "Password must be at least 6 characters"),
  first_name: zod.string().min(1, "First name is required"),
  last_name: zod.string().min(1, "Last name is required"),
  role: zod.string().min(1, "Role is required"),
  default_branch_id: zod.string().uuid("Invalid branch selection"),
});

const branchCreateSchema = zod.object({
  name: zod.string().min(1, "Branch name is required"),
  code: zod.string().min(1, "Code is required").max(10),
});

export const Settings: React.FC = () => {
  const { user: currentUser } = useUser();
  const queryClient = useQueryClient();
  const isDoctor = currentUser?.role === "doctor";

  const [activeSubTab, setActiveSubTab] = useState<"clinic" | "branches" | "users">("clinic");
  
  // Modals
  const [modalOpen, setModalOpen] = useState<"add-user" | "add-branch" | null>(null);

  // Forms
  const userForm = useForm<zod.infer<typeof userCreateSchema>>({ resolver: zodResolver(userCreateSchema) });
  const branchForm = useForm<zod.infer<typeof branchCreateSchema>>({ resolver: zodResolver(branchCreateSchema) });

  // --- Fetch Queries ---
  const { data: branches = [] } = useQuery<Branch[]>({
    queryKey: ["branches"],
    queryFn: async () => (await api.get("/branches/")).data,
  });

  const { data: usersList = [] } = useQuery<UserProfile[]>({
    queryKey: ["users"],
    queryFn: async () => (await api.get("/users/")).data,
    enabled: isDoctor && activeSubTab === "users",
  });

  // --- Mutations ---
  const createUserMutation = useMutation({
    mutationFn: async (data: any) => (await api.post("/users/", data)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setModalOpen(null);
      userForm.reset();
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || "Failed to create user. Email might already exist.");
    },
  });

  const createBranchMutation = useMutation({
    mutationFn: async (data: any) => (await api.post("/branches/", data)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["branches"] });
      setModalOpen(null);
      branchForm.reset();
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || "Failed to create branch.");
    },
  });

  const handleCreateUser = (data: any) => {
    createUserMutation.mutate(data);
  };

  const handleCreateBranch = (data: any) => {
    createBranchMutation.mutate(data);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight">System configuration</h2>
          <p className="text-sm text-slate-500">Configure clinic profile, branch locations, and system accounts</p>
        </div>

        {isDoctor && activeSubTab !== "clinic" && (
          <Button
            size="sm"
            onClick={() => {
              userForm.reset();
              branchForm.reset();
              setModalOpen(activeSubTab === "users" ? "add-user" : "add-branch");
            }}
          >
            <Plus className="mr-2 h-4 w-4 text-white" />
            {activeSubTab === "users" ? "Add User Account" : "Add Branch"}
          </Button>
        )}
      </div>

      {/* Settings Navigation Tabs */}
      <div className="flex space-x-1.5 bg-slate-100 rounded-xl p-1 shrink-0 self-start max-w-max">
        <button
          onClick={() => setActiveSubTab("clinic")}
          className={`rounded-lg px-4 py-2 text-xs font-bold transition-all duration-200 cursor-pointer ${
            activeSubTab === "clinic" ? "bg-white text-slate-800 shadow" : "text-slate-500 hover:text-slate-800"
          }`}
        >
          Clinic Profile
        </button>
        <button
          onClick={() => setActiveSubTab("branches")}
          className={`rounded-lg px-4 py-2 text-xs font-bold transition-all duration-200 cursor-pointer ${
            activeSubTab === "branches" ? "bg-white text-slate-800 shadow" : "text-slate-500 hover:text-slate-800"
          }`}
        >
          Branch Management
        </button>
        {isDoctor && (
          <button
            onClick={() => setActiveSubTab("users")}
            className={`rounded-lg px-4 py-2 text-xs font-bold transition-all duration-200 cursor-pointer ${
              activeSubTab === "users" ? "bg-white text-slate-800 shadow" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            User Accounts
          </button>
        )}
      </div>

      {/* --- SUBTAB PANELS --- */}

      {activeSubTab === "clinic" && (
        <div className="grid gap-6 md:grid-cols-3">
          {/* Card left (details) */}
          <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm md:col-span-2 space-y-4">
            <div className="flex items-center space-x-3 mb-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
                <Landmark className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-800">Clinic Profile details</h3>
                <span className="text-xs text-slate-400">Core clinic branding properties</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm mt-4">
              <div>
                <span className="text-xs text-slate-400 font-bold block">Clinic Name</span>
                <span className="font-semibold text-slate-800 mt-1 block">ClinicStock Homeopathy Care</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 font-bold block">Tax / GSTIN Number</span>
                <span className="font-semibold text-slate-800 mt-1 block">37AAAAA1111A1Z1</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 font-bold block">Primary Email</span>
                <span className="font-semibold text-slate-800 mt-1 block">support@clinicstock.com</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 font-bold block">Support Phone</span>
                <span className="font-semibold text-slate-800 mt-1 block">+91 98765 43210</span>
              </div>
            </div>

            <div className="border-t border-slate-100 pt-4 text-xs text-slate-500 leading-relaxed">
              * The clinic profile details can be edited inside the configuration database. For branding edits, consult your developer.
            </div>
          </div>

          {/* Right card (Active user summary) */}
          <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm md:col-span-1 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-teal-900 text-teal-400 font-semibold shadow-inner">
                {(currentUser?.first_name?.[0] ?? "")}{(currentUser?.last_name?.[0] ?? "")}
              </div>
              <div>
                <span className="block font-bold text-slate-800 text-lg leading-tight">
                  {currentUser?.first_name} {currentUser?.last_name}
                </span>
                <span className="text-xs text-slate-400 font-semibold">{currentUser?.email}</span>
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
                <span className="inline-flex rounded-full bg-teal-50 border border-teal-100 px-2.5 py-0.5 text-[10px] font-bold text-teal-700 capitalize">
                  Role: {currentUser?.role}
                </span>
                <span className="inline-flex rounded-full bg-slate-50 border border-slate-200 px-2.5 py-0.5 text-[10px] font-bold text-slate-600">
                  Branch ID: {currentUser?.default_branch_id.slice(0, 8)}...
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeSubTab === "branches" && (
        <div className="rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100 text-sm">
              <thead>
                <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-400 bg-slate-50">
                  <th className="px-6 py-4">Branch Name</th>
                  <th className="px-6 py-4">Short Code</th>
                  <th className="px-6 py-4">ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {branches.map((b) => (
                  <tr key={b.id} className="hover:bg-slate-50/50">
                    <td className="px-6 py-4 font-semibold text-slate-800">{b.name}</td>
                    <td className="px-6 py-4 text-slate-500 font-bold uppercase">{b.code}</td>
                    <td className="px-6 py-4 text-slate-400 font-mono text-xs">{b.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeSubTab === "users" && isDoctor && (
        <div className="rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100 text-sm">
              <thead>
                <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-400 bg-slate-50">
                  <th className="px-6 py-4">User Details</th>
                  <th className="px-6 py-4">Email</th>
                  <th className="px-6 py-4">Role</th>
                  <th className="px-6 py-4">Default Branch</th>
                  <th className="px-6 py-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {usersList.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/50">
                    <td className="px-6 py-4 font-semibold text-slate-800">
                      {u.first_name ?? ""} {u.last_name ?? ""}
                    </td>
                    <td className="px-6 py-4 text-slate-500">{u.email}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold border uppercase tracking-wider ${
                        u.role === "doctor" ? "bg-teal-50 text-teal-700 border-teal-100" : "bg-slate-50 text-slate-600 border-slate-200"
                      }`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-600 font-medium">
                      {u.default_branch?.name || "—"}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-bold border uppercase tracking-wider ${
                        u.is_active
                          ? "bg-emerald-50 text-emerald-700 border-emerald-100"
                          : "bg-slate-50 text-slate-400 border-slate-200"
                      }`}>
                        {u.is_active ? "Active" : "Suspended"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* --- ADD USER MODAL --- */}
      <Modal isOpen={modalOpen === "add-user"} onClose={() => setModalOpen(null)} title="Create User Account">
        <form onSubmit={userForm.handleSubmit(handleCreateUser)} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">First Name *</label>
              <input type="text" required {...userForm.register("first_name")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Last Name *</label>
              <input type="text" required {...userForm.register("last_name")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Email Address *</label>
            <input type="email" required {...userForm.register("email")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Initial Password *</label>
            <input type="password" required {...userForm.register("password")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">System Role *</label>
            <select required {...userForm.register("role")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm">
              <option value="">Select Role</option>
              <option value="doctor">Doctor (Admin)</option>
              <option value="assistant">Assistant (Operator)</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Assign Default Branch *</label>
            <select required {...userForm.register("default_branch_id")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm">
              <option value="">Select Branch</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <Button variant="outline" type="button" onClick={() => setModalOpen(null)}>Cancel</Button>
            <Button type="submit">Create User Account</Button>
          </div>
        </form>
      </Modal>

      {/* --- ADD BRANCH MODAL --- */}
      <Modal isOpen={modalOpen === "add-branch"} onClose={() => setModalOpen(null)} title="Create New Branch">
        <form onSubmit={branchForm.handleSubmit(handleCreateBranch)} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Branch Name *</label>
            <input type="text" required placeholder="e.g. Gudivada Branch" {...branchForm.register("name")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Short Code *</label>
            <input type="text" required placeholder="e.g. GDV" {...branchForm.register("code")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <Button variant="outline" type="button" onClick={() => setModalOpen(null)}>Cancel</Button>
            <Button type="submit">Create Branch</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
