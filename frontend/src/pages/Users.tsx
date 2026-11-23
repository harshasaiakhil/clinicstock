import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Users,
  UserPlus,
  KeyRound,
  Edit,
  Power,
  Search,
  Eye,
  EyeOff,
  Copy,
  Check,
  ShieldAlert,
  AlertCircle,
  Building,
  Sparkles,
} from "lucide-react";

import api from "../api";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";

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
  force_password_change: boolean;
  default_branch_id: string;
  default_branch?: Branch;
  created_at?: string;
}

export const UsersPage: React.FC = () => {
  const { user: currentUser } = useAuth();
  const queryClient = useQueryClient();

  // Search & Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [branchFilter, setBranchFilter] = useState<string>("all");

  // Modals state
  const [modalType, setModalType] = useState<
    "create" | "edit" | "reset-password" | "toggle-active" | null
  >(null);
  const [selectedUser, setSelectedUser] = useState<UserProfile | null>(null);

  // Form states for Create User
  const [createForm, setCreateForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    role: "assistant",
    default_branch_id: "",
  });

  // Form states for Edit User
  const [editForm, setEditForm] = useState({
    first_name: "",
    last_name: "",
    role: "assistant",
    default_branch_id: "",
  });

  // Form states for Reset Password
  const [resetForm, setResetForm] = useState({
    new_password: "",
    force_password_change: true,
  });
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetSuccessModal, setResetSuccessModal] = useState<{
    userName: string;
    userEmail: string;
    temporaryPassword: string;
  } | null>(null);
  const [copied, setCopied] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // --- Queries ---
  const {
    data: usersList = [],
    isLoading: usersLoading,
    error: usersError,
  } = useQuery<UserProfile[]>({
    queryKey: ["users"],
    queryFn: async () => (await api.get("/users/")).data,
  });

  const { data: branches = [] } = useQuery<Branch[]>({
    queryKey: ["branches"],
    queryFn: async () => (await api.get("/branches/")).data,
  });

  // --- Mutations ---
  const createUserMutation = useMutation({
    mutationFn: async (data: typeof createForm) => (await api.post("/users/", data)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setModalType(null);
      setFormError(null);
      setCreateForm({
        first_name: "",
        last_name: "",
        email: "",
        password: "",
        role: "assistant",
        default_branch_id: "",
      });
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || "Failed to create staff account.");
    },
  });

  const updateUserMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: typeof editForm }) =>
      (await api.put(`/users/${id}`, data)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setModalType(null);
      setSelectedUser(null);
      setFormError(null);
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || "Failed to update user profile.");
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: string;
      payload: { new_password: string; force_password_change: boolean };
    }) => (await api.post(`/users/${id}/reset-password`, payload)).data,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setModalType(null);
      setFormError(null);
      if (selectedUser) {
        setResetSuccessModal({
          userName: `${selectedUser.first_name} ${selectedUser.last_name}`,
          userEmail: selectedUser.email,
          temporaryPassword: variables.payload.new_password,
        });
      }
      setSelectedUser(null);
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || "Failed to reset password.");
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: async ({ id, isActive }: { id: string; isActive: boolean }) => {
      const endpoint = isActive ? `/users/${id}/deactivate` : `/users/${id}/activate`;
      return (await api.post(endpoint)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setModalType(null);
      setSelectedUser(null);
      setFormError(null);
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || "Failed to update account status.");
    },
  });

  // Helpers
  const generateStrongPassword = () => {
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%";
    let password = "Cs!";
    for (let i = 0; i < 9; i++) {
      password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return password;
  };

  const handleOpenReset = (user: UserProfile) => {
    setSelectedUser(user);
    setResetForm({
      new_password: generateStrongPassword(),
      force_password_change: true,
    });
    setFormError(null);
    setShowResetPassword(false);
    setModalType("reset-password");
  };

  const handleOpenEdit = (user: UserProfile) => {
    setSelectedUser(user);
    setEditForm({
      first_name: user.first_name || "",
      last_name: user.last_name || "",
      role: user.role,
      default_branch_id: user.default_branch_id || (branches[0]?.id ?? ""),
    });
    setFormError(null);
    setModalType("edit");
  };

  const handleOpenToggleActive = (user: UserProfile) => {
    setSelectedUser(user);
    setFormError(null);
    setModalType("toggle-active");
  };

  const handleCopyPassword = () => {
    if (resetSuccessModal?.temporaryPassword) {
      navigator.clipboard.writeText(resetSuccessModal.temporaryPassword);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  // Filtered users
  const filteredUsers = usersList.filter((u) => {
    const fullName = `${u.first_name || ""} ${u.last_name || ""}`.toLowerCase();
    const email = u.email.toLowerCase();
    const q = searchTerm.toLowerCase();
    const matchesSearch = fullName.includes(q) || email.includes(q);
    const matchesRole = roleFilter === "all" || u.role === roleFilter;
    const matchesBranch =
      branchFilter === "all" || u.default_branch_id === branchFilter;
    return matchesSearch && matchesRole && matchesBranch;
  });

  // Statistics
  const totalUsers = usersList.length;
  const doctorCount = usersList.filter((u) => u.role === "doctor").length;
  const assistantCount = usersList.filter((u) => u.role === "assistant").length;
  const activeCount = usersList.filter((u) => u.is_active).length;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight flex items-center gap-2.5">
            <Users className="h-7 w-7 text-teal-600" />
            Doctors & Staff Management
          </h2>
          <p className="text-sm text-slate-500">
            Manage practitioners, clinic assistants, branch assignments, and security credentials
          </p>
        </div>

        <Button
          onClick={() => {
            setCreateForm({
              first_name: "",
              last_name: "",
              email: "",
              password: generateStrongPassword(),
              role: "assistant",
              default_branch_id: branches[0]?.id || "",
            });
            setFormError(null);
            setModalType("create");
          }}
        >
          <UserPlus className="mr-2 h-4 w-4" />
          Add Staff Member
        </Button>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Total Accounts
          </span>
          <div className="mt-2 text-2xl font-bold text-slate-800">{totalUsers}</div>
        </div>
        <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-teal-600">
            Doctors (Admins)
          </span>
          <div className="mt-2 text-2xl font-bold text-teal-700">{doctorCount}</div>
        </div>
        <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Clinic Assistants
          </span>
          <div className="mt-2 text-2xl font-bold text-slate-700">{assistantCount}</div>
        </div>
        <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-emerald-600">
            Active Accounts
          </span>
          <div className="mt-2 text-2xl font-bold text-emerald-700">{activeCount}</div>
        </div>
      </div>

      {/* Search and Filters Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by staff name or email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-xl border border-slate-200 pl-9 pr-4 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Role Filter */}
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 focus:border-teal-500 focus:outline-none"
          >
            <option value="all">All Roles</option>
            <option value="doctor">Doctors</option>
            <option value="assistant">Assistants</option>
          </select>

          {/* Branch Filter */}
          <select
            value={branchFilter}
            onChange={(e) => setBranchFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 focus:border-teal-500 focus:outline-none"
          >
            <option value="all">All Branches</option>
            {branches.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Users Table */}
      <div className="rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
        {usersLoading ? (
          <div className="flex h-48 items-center justify-center">
            <div className="flex flex-col items-center space-y-2">
              <div className="h-8 w-8 animate-spin rounded-full border-3 border-teal-600 border-t-transparent" />
              <span className="text-xs text-slate-400">Loading user directory...</span>
            </div>
          </div>
        ) : usersError ? (
          <div className="p-8 text-center text-rose-600">
            <AlertCircle className="mx-auto h-8 w-8 mb-2" />
            <p className="font-semibold">Failed to load staff accounts</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100 text-sm">
              <thead>
                <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-400 bg-slate-50">
                  <th className="px-6 py-4">Staff Member</th>
                  <th className="px-6 py-4">Email</th>
                  <th className="px-6 py-4">Role</th>
                  <th className="px-6 py-4">Assigned Branch</th>
                  <th className="px-6 py-4 text-center">Status</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                      No staff accounts found matching your filters.
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((u) => {
                    const isSelf = currentUser?.id === u.id;
                    return (
                      <tr key={u.id} className="hover:bg-slate-50/60 transition-colors">
                        {/* Name & Initials */}
                        <td className="px-6 py-4">
                          <div className="flex items-center space-x-3">
                            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-teal-50 text-teal-700 font-bold text-xs border border-teal-100 shrink-0">
                              {(u.first_name?.[0] || "") + (u.last_name?.[0] || "")}
                            </div>
                            <div>
                              <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                                {u.first_name} {u.last_name}
                                {isSelf && (
                                  <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-medium">
                                    You
                                  </span>
                                )}
                              </div>
                              {u.force_password_change && (
                                <span className="inline-flex items-center text-[10px] text-amber-600 font-semibold bg-amber-50 px-1.5 py-0.2 rounded border border-amber-200 mt-0.5">
                                  Password reset required
                                </span>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Email */}
                        <td className="px-6 py-4 text-slate-500 font-medium">
                          {u.email}
                        </td>

                        {/* Role */}
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-bold border uppercase tracking-wide ${
                              u.role === "doctor"
                                ? "bg-teal-50 text-teal-700 border-teal-100"
                                : "bg-blue-50 text-blue-700 border-blue-100"
                            }`}
                          >
                            {u.role === "doctor" ? "Doctor / Admin" : "Assistant"}
                          </span>
                        </td>

                        {/* Default Branch */}
                        <td className="px-6 py-4">
                          <div className="flex items-center space-x-1.5 text-slate-600">
                            <Building className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                            <span className="font-medium">
                              {u.default_branch?.name || "Unassigned"}
                            </span>
                          </div>
                        </td>

                        {/* Status */}
                        <td className="px-6 py-4 text-center">
                          <span
                            className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-bold border uppercase tracking-wider ${
                              u.is_active
                                ? "bg-emerald-50 text-emerald-700 border-emerald-100"
                                : "bg-slate-100 text-slate-400 border-slate-200"
                            }`}
                          >
                            {u.is_active ? "Active" : "Deactivated"}
                          </span>
                        </td>

                        {/* Actions */}
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end space-x-1.5">
                            {/* Reset Password Button */}
                            <button
                              onClick={() => handleOpenReset(u)}
                              title="Reset Password"
                              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-teal-400 hover:text-teal-700 hover:bg-teal-50 transition-colors shadow-2xs cursor-pointer"
                            >
                              <KeyRound className="h-3.5 w-3.5 text-teal-600" />
                              <span>Reset Password</span>
                            </button>

                            {/* Edit Profile Button */}
                            <button
                              onClick={() => handleOpenEdit(u)}
                              title="Edit User"
                              className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors cursor-pointer"
                            >
                              <Edit className="h-3.5 w-3.5" />
                            </button>

                            {/* Activate / Deactivate Toggle */}
                            <button
                              onClick={() => handleOpenToggleActive(u)}
                              disabled={isSelf}
                              title={
                                isSelf
                                  ? "Cannot deactivate your own account"
                                  : u.is_active
                                  ? "Deactivate Account"
                                  : "Activate Account"
                              }
                              className={`p-1.5 rounded-lg border transition-colors cursor-pointer ${
                                isSelf
                                  ? "border-slate-100 text-slate-300 cursor-not-allowed bg-slate-50"
                                  : u.is_active
                                  ? "border-rose-100 text-rose-500 hover:bg-rose-50 hover:text-rose-700"
                                  : "border-emerald-100 text-emerald-600 hover:bg-emerald-50 hover:text-emerald-800"
                              }`}
                            >
                              <Power className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ======================================================== */}
      {/* 1. RESET PASSWORD MODAL                                  */}
      {/* ======================================================== */}
      <Modal
        isOpen={modalType === "reset-password"}
        onClose={() => {
          setModalType(null);
          setSelectedUser(null);
        }}
        title="Reset User Password"
      >
        {selectedUser && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (resetForm.new_password.length < 8) {
                setFormError("Password must be at least 8 characters");
                return;
              }
              resetPasswordMutation.mutate({
                id: selectedUser.id,
                payload: resetForm,
              });
            }}
            className="space-y-4"
          >
            {/* Target User Banner */}
            <div className="rounded-xl bg-teal-50 border border-teal-100 p-3.5">
              <span className="text-xs font-bold text-teal-800 block">
                Resetting password for:
              </span>
              <div className="mt-1 flex items-center justify-between">
                <div>
                  <span className="text-sm font-semibold text-slate-800">
                    {selectedUser.first_name} {selectedUser.last_name}
                  </span>
                  <span className="text-xs text-slate-500 block">
                    {selectedUser.email}
                  </span>
                </div>
                <span className="text-[10px] font-bold bg-white text-teal-700 border border-teal-200 px-2 py-0.5 rounded-full capitalize">
                  {selectedUser.role}
                </span>
              </div>
            </div>

            {formError && (
              <div className="rounded-xl bg-rose-50 border border-rose-100 p-3 text-xs text-rose-700 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            {/* Temporary Password Input */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  New Temporary Password *
                </label>
                <button
                  type="button"
                  onClick={() =>
                    setResetForm((prev) => ({
                      ...prev,
                      new_password: generateStrongPassword(),
                    }))
                  }
                  className="text-xs font-semibold text-teal-600 hover:text-teal-700 flex items-center gap-1 cursor-pointer"
                >
                  <Sparkles className="h-3 w-3" />
                  Generate Random
                </button>
              </div>

              <div className="relative">
                <input
                  type={showResetPassword ? "text" : "password"}
                  required
                  value={resetForm.new_password}
                  onChange={(e) =>
                    setResetForm((prev) => ({
                      ...prev,
                      new_password: e.target.value,
                    }))
                  }
                  className="block w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-mono text-slate-800 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
                <button
                  type="button"
                  onClick={() => setShowResetPassword((prev) => !prev)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 cursor-pointer"
                >
                  {showResetPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              <p className="mt-1 text-[11px] text-slate-400">
                Minimum 8 characters. Must contain letters, numbers, or symbols.
              </p>
            </div>

            {/* Force Password Change Checkbox */}
            <div className="rounded-xl bg-slate-50 border border-slate-100 p-3">
              <label className="flex items-start space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={resetForm.force_password_change}
                  onChange={(e) =>
                    setResetForm((prev) => ({
                      ...prev,
                      force_password_change: e.target.checked,
                    }))
                  }
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                />
                <div className="text-xs">
                  <span className="font-bold text-slate-700 block">
                    Require password change on next login
                  </span>
                  <span className="text-slate-500">
                    Staff member will be prompted to choose their own personal password upon next sign-in.
                  </span>
                </div>
              </label>
            </div>

            {/* Modal Actions */}
            <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100">
              <Button
                variant="outline"
                type="button"
                onClick={() => {
                  setModalType(null);
                  setSelectedUser(null);
                }}
              >
                Cancel
              </Button>
              <Button type="submit" isLoading={resetPasswordMutation.isPending}>
                Set Temporary Password
              </Button>
            </div>
          </form>
        )}
      </Modal>

      {/* ======================================================== */}
      {/* 2. RESET SUCCESS MODAL (Temporary Password Display)     */}
      {/* ======================================================== */}
      <Modal
        isOpen={!!resetSuccessModal}
        onClose={() => setResetSuccessModal(null)}
        title="Password Successfully Reset"
      >
        {resetSuccessModal && (
          <div className="space-y-4">
            <div className="flex items-center space-x-3 rounded-xl bg-emerald-50 border border-emerald-100 p-3 text-emerald-800 text-xs">
              <Check className="h-5 w-5 text-emerald-600 shrink-0" />
              <div>
                <span className="font-bold block">
                  Password updated for {resetSuccessModal.userName}
                </span>
                <span>The new temporary password is ready to share.</span>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 space-y-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
                Temporary Password
              </span>
              <div className="flex items-center justify-between bg-white border border-slate-200 rounded-xl p-3">
                <span className="font-mono text-base font-bold text-teal-800 tracking-wider">
                  {resetSuccessModal.temporaryPassword}
                </span>
                <button
                  onClick={handleCopyPassword}
                  className="flex items-center space-x-1 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-700 px-3 py-1.5 text-xs font-semibold transition-colors cursor-pointer"
                >
                  {copied ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-600" />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
              <p className="text-[11px] text-slate-400">
                Provide this credential to <strong>{resetSuccessModal.userEmail}</strong>.
              </p>
            </div>

            <div className="flex justify-end pt-2">
              <Button onClick={() => setResetSuccessModal(null)}>Done</Button>
            </div>
          </div>
        )}
      </Modal>

      {/* ======================================================== */}
      {/* 3. EDIT USER MODAL                                      */}
      {/* ======================================================== */}
      <Modal
        isOpen={modalType === "edit"}
        onClose={() => {
          setModalType(null);
          setSelectedUser(null);
        }}
        title="Edit Staff Profile"
      >
        {selectedUser && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              updateUserMutation.mutate({
                id: selectedUser.id,
                data: editForm,
              });
            }}
            className="space-y-4"
          >
            {formError && (
              <div className="rounded-xl bg-rose-50 border border-rose-100 p-3 text-xs text-rose-700 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  First Name *
                </label>
                <input
                  type="text"
                  required
                  value={editForm.first_name}
                  onChange={(e) =>
                    setEditForm((prev) => ({ ...prev, first_name: e.target.value }))
                  }
                  className="mt-1 block w-full rounded-xl border border-slate-200 p-2.5 text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Last Name *
                </label>
                <input
                  type="text"
                  required
                  value={editForm.last_name}
                  onChange={(e) =>
                    setEditForm((prev) => ({ ...prev, last_name: e.target.value }))
                  }
                  className="mt-1 block w-full rounded-xl border border-slate-200 p-2.5 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Email Address
              </label>
              <input
                type="email"
                disabled
                value={selectedUser.email}
                className="mt-1 block w-full rounded-xl border border-slate-100 bg-slate-50 p-2.5 text-sm text-slate-400 cursor-not-allowed"
              />
              <span className="text-[11px] text-slate-400 mt-0.5 block">
                Primary login email cannot be changed directly.
              </span>
            </div>

            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                System Role *
              </label>
              <select
                disabled={currentUser?.id === selectedUser.id}
                value={editForm.role}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, role: e.target.value }))
                }
                className="mt-1 block w-full rounded-xl border border-slate-200 p-2.5 text-sm disabled:bg-slate-50 disabled:cursor-not-allowed"
              >
                <option value="doctor">Doctor (Admin / Full Management)</option>
                <option value="assistant">Assistant (Operational / Clinic Stock)</option>
              </select>
              {currentUser?.id === selectedUser.id && (
                <span className="text-[11px] text-amber-600 mt-1 block">
                  Safety lock: You cannot demote your own administrative role.
                </span>
              )}
            </div>

            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Assigned Branch *
              </label>
              <select
                required
                value={editForm.default_branch_id}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, default_branch_id: e.target.value }))
                }
                className="mt-1 block w-full rounded-xl border border-slate-200 p-2.5 text-sm"
              >
                {branches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name} ({b.code})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100">
              <Button
                variant="outline"
                type="button"
                onClick={() => {
                  setModalType(null);
                  setSelectedUser(null);
                }}
              >
                Cancel
              </Button>
              <Button type="submit" isLoading={updateUserMutation.isPending}>
                Save Changes
              </Button>
            </div>
          </form>
        )}
      </Modal>

      {/* ======================================================== */}
      {/* 4. CREATE USER MODAL                                    */}
      {/* ======================================================== */}
      <Modal
        isOpen={modalType === "create"}
        onClose={() => setModalType(null)}
        title="Create New Staff Account"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (createForm.password.length < 8) {
              setFormError("Initial password must be at least 8 characters");
              return;
            }
            createUserMutation.mutate(createForm);
          }}
          className="space-y-4"
        >
          {formError && (
            <div className="rounded-xl bg-rose-50 border border-rose-100 p-3 text-xs text-rose-700 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                First Name *
              </label>
              <input
                type="text"
                required
                value={createForm.first_name}
                onChange={(e) =>
                  setCreateForm((prev) => ({ ...prev, first_name: e.target.value }))
                }
                className="mt-1 block w-full rounded-xl border border-slate-200 p-2.5 text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Last Name *
              </label>
              <input
                type="text"
                required
                value={createForm.last_name}
                onChange={(e) =>
                  setCreateForm((prev) => ({ ...prev, last_name: e.target.value }))
                }
                className="mt-1 block w-full rounded-xl border border-slate-200 p-2.5 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Email Address *
            </label>
            <input
              type="email"
              required
              value={createForm.email}
              onChange={(e) =>
                setCreateForm((prev) => ({ ...prev, email: e.target.value }))
              }
              placeholder="e.g. staff@clinicstock.com"
              className="mt-1 block w-full rounded-xl border border-slate-200 p-2.5 text-sm"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Initial Password *
              </label>
              <button
                type="button"
                onClick={() =>
                  setCreateForm((prev) => ({
                    ...prev,
                    password: generateStrongPassword(),
                  }))
                }
                className="text-xs font-semibold text-teal-600 hover:text-teal-700 flex items-center gap-1 cursor-pointer"
              >
                <Sparkles className="h-3 w-3" />
                Generate Random
              </button>
            </div>
            <input
              type="text"
              required
              value={createForm.password}
              onChange={(e) =>
                setCreateForm((prev) => ({ ...prev, password: e.target.value }))
              }
              className="block w-full rounded-xl border border-slate-200 p-2.5 text-sm font-mono"
            />
          </div>

          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
              System Role *
            </label>
            <select
              value={createForm.role}
              onChange={(e) =>
                setCreateForm((prev) => ({ ...prev, role: e.target.value }))
              }
              className="mt-1 block w-full rounded-xl border border-slate-200 p-2.5 text-sm"
            >
              <option value="doctor">Doctor (Admin / Full Clinic Management)</option>
              <option value="assistant">Assistant (Operational / Clinic Stock)</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Assign Default Branch *
            </label>
            <select
              required
              value={createForm.default_branch_id}
              onChange={(e) =>
                setCreateForm((prev) => ({
                  ...prev,
                  default_branch_id: e.target.value,
                }))
              }
              className="mt-1 block w-full rounded-xl border border-slate-200 p-2.5 text-sm"
            >
              <option value="">Select Branch...</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} ({b.code})
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100">
            <Button variant="outline" type="button" onClick={() => setModalType(null)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createUserMutation.isPending}>
              Create Account
            </Button>
          </div>
        </form>
      </Modal>

      {/* ======================================================== */}
      {/* 5. ACTIVATE / DEACTIVATE CONFIRMATION MODAL               */}
      {/* ======================================================== */}
      <Modal
        isOpen={modalType === "toggle-active"}
        onClose={() => {
          setModalType(null);
          setSelectedUser(null);
        }}
        title={selectedUser?.is_active ? "Deactivate Account" : "Activate Account"}
      >
        {selectedUser && (
          <div className="space-y-4">
            <div
              className={`rounded-xl p-3.5 border flex items-start space-x-3 ${
                selectedUser.is_active
                  ? "bg-rose-50 border-rose-100 text-rose-800"
                  : "bg-emerald-50 border-emerald-100 text-emerald-800"
              }`}
            >
              <ShieldAlert className="h-5 w-5 shrink-0 mt-0.5" />
              <div className="text-xs space-y-1">
                <span className="font-bold block text-sm">
                  {selectedUser.is_active
                    ? `Are you sure you want to suspend ${selectedUser.first_name} ${selectedUser.last_name}?`
                    : `Reactivate ${selectedUser.first_name} ${selectedUser.last_name}?`}
                </span>
                <p>
                  {selectedUser.is_active
                    ? "This user will immediately be blocked from logging into the clinic system. Their historical transaction logs will remain preserved."
                    : "This user will regain access to sign into their assigned branch."}
                </p>
              </div>
            </div>

            {formError && (
              <div className="rounded-xl bg-rose-50 border border-rose-100 p-3 text-xs text-rose-700 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100">
              <Button
                variant="outline"
                type="button"
                onClick={() => {
                  setModalType(null);
                  setSelectedUser(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant={selectedUser.is_active ? "danger" : "primary"}
                isLoading={toggleActiveMutation.isPending}
                onClick={() =>
                  toggleActiveMutation.mutate({
                    id: selectedUser.id,
                    isActive: selectedUser.is_active,
                  })
                }
              >
                {selectedUser.is_active ? "Confirm Deactivation" : "Confirm Activation"}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default UsersPage;
