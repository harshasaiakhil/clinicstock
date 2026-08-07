import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as zod from "zod";
import {
  Plus,
  Search,
  Upload,
  Edit2,
  FileSpreadsheet,
  FileText,
  ChevronDown,
  ChevronUp,
  MapPin,
  TrendingDown,
  ArrowRight,
  Sliders,
  History,
  Boxes,
} from "lucide-react";

import api from "../api";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";

// --- Types & Schemas ---

interface Category {
  id: string;
  name: string;
}

interface Manufacturer {
  id: string;
  name: string;
}

interface Potency {
  id: string;
  name: string;
}

interface Unit {
  id: string;
  name: string;
  code: string;
}

interface Supplier {
  id: string;
  name: string;
}

interface Branch {
  id: string;
  name: string;
}

interface Medicine {
  id: string;
  name: string;
  generic_name: string | null;
  category_id: string;
  manufacturer_id: string | null;
  potency_id: string;
  unit_id: string;
  quantity: number;
  selling_price: number;
  gst_percentage: number;
  hsn_code: string | null;
  description: string | null;
  barcode: string | null;
  qr_code: string | null;
  is_active: boolean;
  category?: Category;
  manufacturer?: Manufacturer | null;
  potency?: Potency;
  unit?: Unit;
  inventories?: InventorySummary[];
}

interface InventorySummary {
  id: string;
  medicine_id: string;
  branch_id: string;
  total_quantity: number;
  available_quantity: number;
  min_stock_level: number;
  reorder_level: number;
  cupboard: string | null;
  rack: string | null;
  row: string | null;
  column: string | null;
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
  cupboard: string | null;
  rack: string | null;
  row: string | null;
  column: string | null;
  supplier?: Supplier;
  summary?: {
    medicine_id: string;
    branch_id: string;
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
      medicine_id: string;
    };
  };
}

// Unified Zod Schema for Add / Edit form (Medicine info + Optional initial inventory)
const medicineFormSchema = zod.object({
  // Medicine Info
  name: zod.string().min(1, "Name is required").max(100),
  generic_name: zod.string().max(100).nullable().optional().or(zod.literal("")),
  category_id: zod.string().uuid("Invalid category"),
  manufacturer_id: zod.string().uuid("Invalid manufacturer").nullable().optional().or(zod.literal("")),
  potency_id: zod.string().uuid("Invalid potency"),
  unit_id: zod.string().uuid("Invalid unit"),
  selling_price: zod.coerce.number().nonnegative("Price cannot be negative"),
  gst_percentage: zod.coerce.number().nonnegative("GST cannot be negative"),
  hsn_code: zod.string().max(50).nullable().optional().or(zod.literal("")),
  description: zod.string().max(255).nullable().optional().or(zod.literal("")),
  barcode: zod.string().max(100).nullable().optional().or(zod.literal("")),
  qr_code: zod.string().max(100).nullable().optional().or(zod.literal("")),
  is_active: zod.boolean().default(true),

  // Initial Inventory (Optional)
  branch_id: zod.string().uuid("Select branch").nullable().optional().or(zod.literal("")),
  quantity: zod.coerce.number().int().nonnegative("Quantity cannot be negative").optional().or(zod.literal("")),
  batch_number: zod.string().max(100).nullable().optional().or(zod.literal("")),
  expiry_date: zod.string().nullable().optional().or(zod.literal("")),
  cupboard: zod.string().max(100).nullable().optional().or(zod.literal("")),
  rack: zod.string().max(100).nullable().optional().or(zod.literal("")),
  row: zod.string().max(100).nullable().optional().or(zod.literal("")),
  column: zod.string().max(100).nullable().optional().or(zod.literal("")),
});

// Zod schemas for separate transaction operations
const stockInSchema = zod.object({
  medicine_id: zod.string().uuid("Select medicine"),
  branch_id: zod.string().uuid("Select branch"),
  batch_number: zod.string().min(1, "Batch number required").max(100),
  supplier_id: zod.string().uuid("Invalid supplier").nullable().optional().or(zod.literal("")),
  purchase_date: zod.string().nullable().optional().or(zod.literal("")),
  expiry_date: zod.string().nullable().optional().or(zod.literal("")),
  purchase_price: zod.coerce.number().nonnegative("Cannot be negative"),
  selling_price: zod.coerce.number().nonnegative("Cannot be negative"),
  quantity: zod.coerce.number().int().gt(0, "Quantity must be greater than 0"),
  cupboard: zod.string().max(100).nullable().optional().or(zod.literal("")),
  rack: zod.string().max(100).nullable().optional().or(zod.literal("")),
  row: zod.string().max(100).nullable().optional().or(zod.literal("")),
  column: zod.string().max(100).nullable().optional().or(zod.literal("")),
  reason: zod.string().max(255).nullable().optional().or(zod.literal("")),
});

const editBatchSchema = zod.object({
  selling_price: zod.coerce.number().nonnegative("Price cannot be negative"),
  cupboard: zod.string().max(100).nullable().optional().or(zod.literal("")),
  rack: zod.string().max(100).nullable().optional().or(zod.literal("")),
  row: zod.string().max(100).nullable().optional().or(zod.literal("")),
  column: zod.string().max(100).nullable().optional().or(zod.literal("")),
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

export const Medicines: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const isDoctor = user?.role === "doctor";

  // --- Search & Filter States ---
  const [searchTerm, setSearchTerm] = useState("");
  const [locationSearch, setLocationSearch] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterManufacturer, setFilterManufacturer] = useState("");
  const [filterPotency, setFilterPotency] = useState("");
  const [filterUnit, setFilterUnit] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  // --- Row Expansion State ---
  const [expandedMedicineIds, setExpandedMedicineIds] = useState<Record<string, boolean>>({});

  // --- Modals State ---
  const [modalOpen, setModalOpen] = useState<"add-med" | "edit-med" | "stock-in" | "dispense" | "transfer" | "adjust" | "import" | "edit-batch" | null>(null);
  
  // Selection Context for transactions
  const [selectedMed, setSelectedMed] = useState<Medicine | null>(null);
  const [selectedBatch, setSelectedBatch] = useState<InventoryBatch | null>(null);

  // File Upload State
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<any | null>(null);
  const [importLoading, setImportLoading] = useState(false);

  // --- Form setup ---
  const medicineForm = useForm({
    resolver: zodResolver(medicineFormSchema),
    defaultValues: {
      is_active: true,
      gst_percentage: 0,
      quantity: 0,
    } as any,
  });

  const stockInForm = useForm({
    resolver: zodResolver(stockInSchema),
    defaultValues: { purchase_price: 0, selling_price: 0 } as any,
  });

  const editBatchForm = useForm({
    resolver: zodResolver(editBatchSchema),
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

  // --- Fetch Core Master Queries ---
  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ["categories"],
    queryFn: async () => (await api.get("/categories/")).data,
  });

  const { data: manufacturers = [] } = useQuery<Manufacturer[]>({
    queryKey: ["manufacturers"],
    queryFn: async () => (await api.get("/manufacturers/")).data,
  });

  const { data: potencies = [] } = useQuery<Potency[]>({
    queryKey: ["potencies"],
    queryFn: async () => (await api.get("/potencies/")).data,
  });

  const { data: units = [] } = useQuery<Unit[]>({
    queryKey: ["units"],
    queryFn: async () => (await api.get("/medicine-units/")).data,
  });

  const { data: branches = [] } = useQuery<Branch[]>({
    queryKey: ["branches"],
    queryFn: async () => (await api.get("/branches/")).data,
  });

  const { data: suppliers = [] } = useQuery<Supplier[]>({
    queryKey: ["suppliers"],
    queryFn: async () => (await api.get("/suppliers/")).data,
  });

  // --- Fetch Medicines Catalog ---
  const { data: medicines = [], isLoading: loadingMeds, isError: medError } = useQuery<Medicine[]>({
    queryKey: ["medicines", searchTerm, filterCategory, filterManufacturer, filterPotency, filterUnit, filterStatus],
    queryFn: async () => {
      const params: Record<string, any> = { skip: 0, limit: 1000 };
      if (filterCategory) params.category_id = filterCategory;
      if (filterManufacturer) params.manufacturer_id = filterManufacturer;
      if (filterPotency) params.potency_id = filterPotency;
      if (filterUnit) params.unit_id = filterUnit;
      if (filterStatus) params.is_active = filterStatus === "active";

      const res = await api.get("/medicines/", { params });
      return res.data;
    },
  });

  // --- Fetch Inventory Totals & Batches ---
  const { data: summaries = [] } = useQuery<InventorySummary[]>({
    queryKey: ["inventory-summaries"],
    queryFn: async () => (await api.get("/inventory/summaries")).data,
  });

  const { data: batches = [] } = useQuery<InventoryBatch[]>({
    queryKey: ["inventory-batches"],
    queryFn: async () => (await api.get("/inventory/batches")).data,
  });

  const { data: transactions = [] } = useQuery<StockTx[]>({
    queryKey: ["inventory-transactions"],
    queryFn: async () => (await api.get("/inventory/transactions", { params: { limit: 500 } })).data,
  });

  // --- CRUD Mutations ---
  const createMedicineMutation = useMutation({
    mutationFn: async (payload: { medicine: any; inventory: any }) => {
      // 1. Create medicine catalog details
      const medData = payload.medicine;
      if (!medData.manufacturer_id) delete medData.manufacturer_id;
      const med = (await api.post("/medicines/", medData)).data;

      // 2. Automatically Stock In initial inventory details if supplied
      const invData = payload.inventory;
      if (invData && invData.branch_id && invData.quantity > 0) {
        const stockInPayload = {
          medicine_id: med.id,
          branch_id: invData.branch_id,
          batch_number: invData.batch_number,
          supplier_id: null,
          purchase_date: null,
          expiry_date: invData.expiry_date || null,
          purchase_price: 0,
          selling_price: med.selling_price,
          quantity: invData.quantity,
          cupboard: invData.cupboard || null,
          rack: invData.rack || null,
          row: invData.row || null,
          column: invData.column || null,
          reason: "Initial inventory setup",
        };
        await api.post("/inventory/stock-in", stockInPayload);
      }
      return med;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["medicines"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-batches"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-summaries"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-transactions"] });
      setModalOpen(null);
      medicineForm.reset();
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || "Failed to create medicine catalog and stock batch.");
    }
  });

  const updateMedicineMutation = useMutation({
    mutationFn: async (payload: { medicineId: string; batchId?: string | null; medicine: any; inventory: any }) => {
      // 1. Update medicine details
      const medData = payload.medicine;
      if (!medData.manufacturer_id) medData.manufacturer_id = null;
      const med = (await api.put(`/medicines/${payload.medicineId}`, medData)).data;

      // 2. Update or create batch
      const invData = payload.inventory;
      if (payload.batchId) {
        const batchUpdatePayload = {
          selling_price: med.selling_price,
          quantity: invData.quantity,
          batch_number: invData.batch_number,
          expiry_date: invData.expiry_date || null,
          cupboard: invData.cupboard || null,
          rack: invData.rack || null,
          row: invData.row || null,
          column: invData.column || null,
        };
        await api.put(`/inventory/batches/${payload.batchId}`, batchUpdatePayload);
      } else if (invData && invData.branch_id && invData.quantity > 0) {
        const stockInPayload = {
          medicine_id: med.id,
          branch_id: invData.branch_id,
          batch_number: invData.batch_number,
          supplier_id: null,
          purchase_date: null,
          expiry_date: invData.expiry_date || null,
          purchase_price: 0,
          selling_price: med.selling_price,
          quantity: invData.quantity,
          cupboard: invData.cupboard || null,
          rack: invData.rack || null,
          row: invData.row || null,
          column: invData.column || null,
          reason: "Initial inventory setup via Edit",
        };
        await api.post("/inventory/stock-in", stockInPayload);
      }
      return med;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["medicines"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-batches"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-summaries"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-transactions"] });
      setModalOpen(null);
      setSelectedMed(null);
      setSelectedBatch(null);
      medicineForm.reset();
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || "Failed to update medicine details.");
    }
  });

  const updateBatchMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: any }) => {
      return (await api.put(`/inventory/batches/${id}`, data)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory-batches"] });
      queryClient.invalidateQueries({ queryKey: ["medicines"] });
      setModalOpen(null);
      setSelectedBatch(null);
      editBatchForm.reset();
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || "Failed to update batch");
    }
  });

  // --- Inventory Operations Mutations ---
  const actionMutation = useMutation({
    mutationFn: async ({ path, data }: { path: string; data: any }) => {
      if (!data.supplier_id) delete data.supplier_id;
      if (!data.purchase_date) delete data.purchase_date;
      if (!data.expiry_date) delete data.expiry_date;
      return (await api.post(`/inventory/${path}`, data)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory-summaries"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-batches"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["medicines"] });
      setModalOpen(null);
      stockInForm.reset();
      dispenseForm.reset();
      transferForm.reset();
      adjustForm.reset();
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || "Inventory transaction failed. Verify stock levels.");
    },
  });

  // --- Handlers ---
  const handleAddSubmit = (data: any) => {
    const medicinePayload = {
      name: data.name,
      generic_name: data.generic_name,
      category_id: data.category_id,
      manufacturer_id: data.manufacturer_id,
      potency_id: data.potency_id,
      unit_id: data.unit_id,
      quantity: data.quantity || 0,
      selling_price: data.selling_price,
      gst_percentage: data.gst_percentage,
      hsn_code: data.hsn_code,
      description: data.description,
      barcode: data.barcode || null,
      qr_code: data.qr_code || null,
      is_active: data.is_active,
    };

    // If they fill branch_id OR quantity OR batch_number OR expiry_date, they must fill all 4
    const hasBranch = !!data.branch_id;
    const hasQty = data.quantity !== undefined && Number(data.quantity) > 0;
    const hasBatch = !!data.batch_number;
    const hasExpiry = !!data.expiry_date;

    const partialStock = hasBranch || hasQty || hasBatch || hasExpiry;
    if (partialStock) {
      if (!data.branch_id || !data.quantity || !data.batch_number || !data.expiry_date) {
        alert("Validation error: If initial stock is provided, you must fill in Branch, Quantity, Batch Number, and Expiry Date.");
        return;
      }
    }

    const inventoryPayload = hasBranch && hasQty ? {
      branch_id: data.branch_id,
      quantity: data.quantity,
      batch_number: data.batch_number,
      expiry_date: data.expiry_date,
      cupboard: data.cupboard,
      rack: data.rack,
      row: data.row,
      column: data.column,
    } : null;

    createMedicineMutation.mutate({
      medicine: medicinePayload,
      inventory: inventoryPayload,
    });
  };
  
  const handleEditSubmit = (data: any) => {
    if (selectedMed) {
      const medicinePayload = {
        name: data.name,
        generic_name: data.generic_name,
        category_id: data.category_id,
        manufacturer_id: data.manufacturer_id,
        potency_id: data.potency_id,
        unit_id: data.unit_id,
        selling_price: data.selling_price,
        gst_percentage: data.gst_percentage,
        hsn_code: data.hsn_code,
        description: data.description,
        barcode: data.barcode || null,
        qr_code: data.qr_code || null,
        is_active: data.is_active,
      };

      const inventoryPayload = {
        branch_id: data.branch_id,
        quantity: data.quantity,
        batch_number: data.batch_number,
        expiry_date: data.expiry_date,
        cupboard: data.cupboard,
        rack: data.rack,
        row: data.row,
        column: data.column,
      };

      updateMedicineMutation.mutate({
        medicineId: selectedMed.id,
        batchId: selectedBatch?.id,
        medicine: medicinePayload,
        inventory: inventoryPayload,
      });
    }
  };

  const handleStockIn = (data: any) => {
    actionMutation.mutate({ path: "stock-in", data });
  };

  const handleEditBatchSubmit = (data: any) => {
    if (selectedBatch) {
      updateBatchMutation.mutate({ id: selectedBatch.id, data });
    }
  };

  const openEdit = (med: Medicine, batch: InventoryBatch | null) => {
    setSelectedMed(med);
    setSelectedBatch(batch);
    setModalOpen("edit-med");
    medicineForm.reset({
      name: med.name,
      generic_name: med.generic_name || "",
      category_id: med.category_id,
      manufacturer_id: med.manufacturer_id || "",
      potency_id: med.potency_id,
      unit_id: med.unit_id,
      selling_price: med.selling_price,
      gst_percentage: med.gst_percentage,
      hsn_code: med.hsn_code || "",
      description: med.description || "",
      barcode: med.barcode || "",
      qr_code: med.qr_code || "",
      is_active: med.is_active,

      // Batch info
      branch_id: batch?.summary?.branch_id || "",
      quantity: batch?.quantity || 0,
      batch_number: batch?.batch_number || "",
      expiry_date: batch?.expiry_date || "",
      cupboard: batch?.cupboard || "",
      rack: batch?.rack || "",
      row: batch?.row || "",
      column: batch?.column || "",
    });
  };

  const openStockIn = (med: Medicine) => {
    setSelectedMed(med);
    setModalOpen("stock-in");
    stockInForm.reset({
      medicine_id: med.id,
      selling_price: med.selling_price,
      quantity: 10,
    } as any);
  };

  const openEditBatch = (batch: InventoryBatch, med: Medicine) => {
    setSelectedMed(med);
    setSelectedBatch(batch);
    setModalOpen("edit-batch");
    editBatchForm.reset({
      selling_price: batch.selling_price,
      cupboard: batch.cupboard || "",
      rack: batch.rack || "",
      row: batch.row || "",
      column: batch.column || "",
    });
  };

  const openDispense = (batch: InventoryBatch, med: Medicine) => {
    setSelectedMed(med);
    setSelectedBatch(batch);
    setModalOpen("dispense");
    dispenseForm.reset({
      batch_id: batch.id,
      quantity: 1,
    });
  };

  const openTransfer = (batch: InventoryBatch, med: Medicine) => {
    setSelectedMed(med);
    setSelectedBatch(batch);
    setModalOpen("transfer");
    transferForm.reset({
      batch_id: batch.id,
      quantity: 1,
    });
  };

  const openAdjust = (batch: InventoryBatch, med: Medicine) => {
    setSelectedMed(med);
    setSelectedBatch(batch);
    setModalOpen("adjust");
    adjustForm.reset({
      batch_id: batch.id,
      quantity_changed: 0,
    });
  };

  const toggleExpand = (medId: string) => {
    setExpandedMedicineIds((prev) => ({
      ...prev,
      [medId]: !prev[medId],
    }));
  };

  const handleExport = async (format: "csv" | "excel") => {
    try {
      const response = await api.get(`/medicines/export/${format}`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `medicines_export.${format === "csv" ? "csv" : "xlsx"}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (err) {
      console.error("Export failed", err);
    }
  };

  const handleImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!importFile) return;
    setImportLoading(true);
    setImportResult(null);

    const formData = new FormData();
    formData.append("file", importFile);

    try {
      const res = await api.post("/medicines/import", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setImportResult(res.data);
      queryClient.invalidateQueries({ queryKey: ["medicines"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-summaries"] });
    } catch (err) {
      console.error(err);
    } finally {
      setImportLoading(false);
    }
  };

  const formatLocation = (loc: { cupboard?: string | null; rack?: string | null; row?: string | null; column?: string | null } | null) => {
    if (!loc) return "—";
    const parts = [];
    if (loc.cupboard) parts.push(loc.cupboard);
    if (loc.rack) parts.push(loc.rack);
    if (loc.row) parts.push(`Row ${loc.row}`);
    if (loc.column) parts.push(`Col ${loc.column}`);
    return parts.length > 0 ? parts.join(" → ") : "—";
  };

  // --- Unified Data Mapping ---
  interface GridRow {
    key: string;
    medicine: Medicine;
    batch: InventoryBatch | null;
  }

  // Create a unified list where each row maps to a medicine batch.
  // If a medicine has no stock batches at all, we create a single row for that medicine with empty batch values so it's still visible!
  const gridRows: GridRow[] = medicines.flatMap((med): GridRow[] => {
    const medBatches = batches.filter((b) => b.summary?.medicine_id === med.id);
    if (medBatches.length === 0) {
      // Medicine with no stock batches
      return [{
        key: `${med.id}-nostock`,
        medicine: med,
        batch: null,
      }];
    }
    return medBatches.map((b) => ({
      key: `${med.id}-${b.id}`,
      medicine: med,
      batch: b,
    }));
  });

  // --- Frontend search & filter by location ---
  const filteredGridRows = gridRows.filter((r) => {
    // 1. General search: medicine name, generic name, batch number, or location details:
    if (searchTerm) {
      const s = searchTerm.toLowerCase();
      const nameMatch = r.medicine.name.toLowerCase().includes(s);
      const genMatch = r.medicine.generic_name?.toLowerCase().includes(s) || false;
      const batchMatch = r.batch?.batch_number.toLowerCase().includes(s) || false;
      const locMatch = (
        (r.batch?.cupboard?.toLowerCase().includes(s) || false) ||
        (r.batch?.rack?.toLowerCase().includes(s) || false) ||
        (r.batch?.row?.toLowerCase().includes(s) || false) ||
        (r.batch?.column?.toLowerCase().includes(s) || false)
      );
      if (!nameMatch && !genMatch && !batchMatch && !locMatch) return false;
    }

    // 2. Specific location search filter:
    if (locationSearch) {
      const loc = locationSearch.toLowerCase();
      const cupboardMatch = r.batch?.cupboard?.toLowerCase().includes(loc) || false;
      const rackMatch = r.batch?.rack?.toLowerCase().includes(loc) || false;
      const rowMatch = r.batch?.row?.toLowerCase().includes(loc) || false;
      const colMatch = r.batch?.column?.toLowerCase().includes(loc) || false;
      if (!cupboardMatch && !rackMatch && !rowMatch && !colMatch) return false;
    }

    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-800 tracking-tight">Medicines</h2>
          <p className="text-sm text-slate-500">Unified dilutions catalog and active batch storage management</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => handleExport("csv")}>
            <FileText className="mr-2 h-4 w-4 text-slate-500" />
            Export CSV
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleExport("excel")}>
            <FileSpreadsheet className="mr-2 h-4 w-4 text-emerald-600" />
            Export Excel
          </Button>
          {isDoctor && (
            <>
              <Button variant="outline" size="sm" onClick={() => setModalOpen("import")}>
                <Upload className="mr-2 h-4 w-4 text-teal-600" />
                Import List
              </Button>
              <Button size="sm" onClick={() => { medicineForm.reset(); setSelectedMed(null); setSelectedBatch(null); setModalOpen("add-med"); }}>
                <Plus className="mr-2 h-4 w-4 text-white" />
                Add Medicine
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Advanced Filter Bar */}
      <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          <div className="relative flex-1 rounded-xl shadow-sm">
            <div className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none">
              <Search className="h-4 w-4 text-slate-400" />
            </div>
            <input
              type="text"
              placeholder="Search medicine name, generic name, batch number, or location..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="block w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-11 pr-4 text-sm text-slate-800 placeholder-slate-400 focus:border-teal-500 focus:bg-white focus:outline-none"
            />
          </div>

          <div className="relative flex-1 rounded-xl shadow-sm">
            <div className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none">
              <MapPin className="h-4 w-4 text-slate-400" />
            </div>
            <input
              type="text"
              placeholder="Filter by precise location (Cupboard/Rack/Row/Col)..."
              value={locationSearch}
              onChange={(e) => setLocationSearch(e.target.value)}
              className="block w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-11 pr-4 text-sm text-slate-800 placeholder-slate-400 focus:border-teal-500 focus:bg-white focus:outline-none"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-700 font-semibold focus:outline-none focus:bg-white"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>

          <select
            value={filterManufacturer}
            onChange={(e) => setFilterManufacturer(e.target.value)}
            className="rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-700 font-semibold focus:outline-none focus:bg-white"
          >
            <option value="">All Manufacturers</option>
            {manufacturers.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>

          <select
            value={filterPotency}
            onChange={(e) => setFilterPotency(e.target.value)}
            className="rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-700 font-semibold focus:outline-none focus:bg-white"
          >
            <option value="">All Potencies</option>
            {potencies.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>

          <select
            value={filterUnit}
            onChange={(e) => setFilterUnit(e.target.value)}
            className="rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-700 font-semibold focus:outline-none focus:bg-white"
          >
            <option value="">All Units</option>
            {units.map((u) => (
              <option key={u.id} value={u.id}>{u.name} ({u.code})</option>
            ))}
          </select>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-700 font-semibold focus:outline-none focus:bg-white col-span-2 md:col-span-1"
          >
            <option value="">All Statuses</option>
            <option value="active">Active Only</option>
            <option value="inactive">Inactive Only</option>
          </select>
        </div>
      </div>

      {/* Unified Table Grid */}
      <div className="rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
        {loadingMeds ? (
          <div className="flex h-64 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-600 border-t-transparent"></div>
          </div>
        ) : medError ? (
          <div className="flex h-64 items-center justify-center text-slate-500">
            <span>Failed to load unified medicines list. Check connection.</span>
          </div>
        ) : filteredGridRows.length === 0 ? (
          <div className="flex h-64 flex-col items-center justify-center border-2 border-dashed border-slate-100 m-6 rounded-2xl">
            <Boxes className="h-10 w-10 text-slate-300 mb-2" />
            <span className="text-sm font-semibold text-slate-500">No matching medicines cataloged</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100 text-sm">
              <thead>
                <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-400 bg-slate-50">
                  <th className="px-4 py-4 w-10"></th>
                  <th className="px-6 py-4">Medicine Name</th>
                  <th className="px-6 py-4">Category</th>
                  <th className="px-6 py-4">Attributes</th>
                  <th className="px-6 py-4">Branch</th>
                  <th className="px-6 py-4 text-right">Qty</th>
                  <th className="px-6 py-4">Batch Number</th>
                  <th className="px-6 py-4 text-center">Expiry</th>
                  <th className="px-6 py-4">Location (Cupboard→Rack→Row→Col)</th>
                  <th className="px-6 py-4 text-right">Selling Price</th>
                  <th className="px-6 py-4 text-center">Status</th>
                  <th className="px-6 py-4 text-right">Quick actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredGridRows.map((row) => {
                  const isExpanded = !!expandedMedicineIds[row.medicine.id];
                  const hasStock = !!row.batch;
                  const displayPrice = row.batch ? row.batch.selling_price : row.medicine.selling_price;
                  
                  return (
                    <React.Fragment key={row.key}>
                      <tr className={`hover:bg-slate-50/50 ${isExpanded ? "bg-slate-50/20" : ""}`}>
                        <td className="px-4 py-4 text-center">
                          <button
                            onClick={() => toggleExpand(row.medicine.id)}
                            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 cursor-pointer"
                          >
                            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </button>
                        </td>
                        <td className="px-6 py-4">
                          <div>
                            <strong className="block text-slate-800 font-bold">{row.medicine.name}</strong>
                            {row.medicine.generic_name && (
                              <span className="text-xs text-slate-400">{row.medicine.generic_name}</span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-slate-600 font-medium">{row.medicine.category?.name}</td>
                        <td className="px-6 py-4">
                          <div className="flex flex-wrap gap-1">
                            <span className="inline-flex rounded bg-teal-50 border border-teal-100 px-1.5 py-0.5 text-[9px] font-bold text-teal-800">
                              {row.medicine.potency?.name}
                            </span>
                            {row.medicine.manufacturer && (
                              <span className="inline-flex rounded bg-slate-50 border border-slate-200 px-1.5 py-0.5 text-[9px] font-bold text-slate-600">
                                {row.medicine.manufacturer.name}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-slate-600 font-semibold">
                          {row.batch?.summary?.branch?.name || "—"}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <span className={`font-extrabold ${row.batch ? "text-slate-800" : "text-slate-300 font-semibold"}`}>
                            {row.batch ? `${row.batch.quantity} ${row.medicine.unit?.code || "units"}` : "No Stock"}
                          </span>
                        </td>
                        <td className="px-6 py-4 font-mono font-bold text-xs text-slate-500">
                          {row.batch?.batch_number || "—"}
                        </td>
                        <td className="px-6 py-4 text-center">
                          {row.batch?.expiry_date ? (
                            <span className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold ${
                              new Date(row.batch.expiry_date) < new Date()
                                ? "bg-rose-50 text-rose-700 border border-rose-100"
                                : "bg-slate-50 text-slate-700 border border-slate-200"
                            }`}>
                              {row.batch.expiry_date}
                            </span>
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-slate-600 font-medium">
                          {hasStock ? (
                            <span className="inline-flex items-center text-xs font-semibold text-slate-700 bg-slate-50 px-2 py-1 rounded border border-slate-100">
                              <MapPin className="h-3 w-3 text-slate-400 mr-1" />
                              {formatLocation(row.batch)}
                            </span>
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right font-semibold text-slate-700">
                          ₹{displayPrice.toFixed(2)}
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-[9px] font-bold border uppercase tracking-wider ${
                            row.medicine.is_active
                              ? "bg-emerald-50 text-emerald-700 border-emerald-100"
                              : "bg-slate-50 text-slate-400 border-slate-200"
                          }`}>
                            {row.medicine.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right space-x-1 whitespace-nowrap">
                          {isDoctor && (
                            <Button variant="outline" size="sm" className="p-1.5" title="Edit Medicine" onClick={() => openEdit(row.medicine, row.batch)}>
                              <Edit2 className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          <Button variant="outline" size="sm" className="p-1.5" title="Stock Inward" onClick={() => openStockIn(row.medicine)}>
                            <Plus className="h-3.5 w-3.5 text-teal-600" />
                          </Button>
                          {hasStock && (
                            <>
                              <Button variant="outline" size="sm" className="p-1.5" title="Dispense" onClick={() => openDispense(row.batch!, row.medicine)}>
                                <TrendingDown className="h-3.5 w-3.5 text-sky-600" />
                              </Button>
                              {isDoctor && (
                                <>
                                  <Button variant="outline" size="sm" className="p-1.5" title="Transfer" onClick={() => openTransfer(row.batch!, row.medicine)}>
                                    <ArrowRight className="h-3.5 w-3.5 text-purple-600" />
                                  </Button>
                                  <Button variant="outline" size="sm" className="p-1.5" title="Adjust Stock" onClick={() => openAdjust(row.batch!, row.medicine)}>
                                    <Sliders className="h-3.5 w-3.5 text-slate-500" />
                                  </Button>
                                </>
                              )}
                            </>
                          )}
                        </td>
                      </tr>

                      {/* --- DETAIL EXPANDABLE PANEL --- */}
                      {isExpanded && row.key.endsWith("-nostock") === false && (
                        <tr>
                          <td colSpan={12} className="bg-slate-50/50 p-6 border-y border-slate-100">
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                              {/* Left column: other batches & branch summaries */}
                              <div className="lg:col-span-2 space-y-4">
                                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center">
                                  <Boxes className="mr-1.5 h-4 w-4 text-slate-400" />
                                  All active stock batches of this medicine
                                </h4>

                                <div className="rounded-xl border bg-white overflow-hidden shadow-sm">
                                  <table className="min-w-full divide-y divide-slate-100 text-xs">
                                    <thead className="bg-slate-50">
                                      <tr className="text-left text-slate-400 font-semibold uppercase">
                                        <th className="px-4 py-2">Batch No</th>
                                        <th className="px-4 py-2">Branch</th>
                                        <th className="px-4 py-2 text-right">Available Qty</th>
                                        <th className="px-4 py-2 text-center">Expiry</th>
                                        <th className="px-4 py-2">Location details</th>
                                        <th className="px-4 py-2 text-right">Actions</th>
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100">
                                      {batches.filter((b) => b.summary?.medicine_id === row.medicine.id).map((b) => (
                                        <tr key={b.id} className="hover:bg-slate-50/50">
                                          <td className="px-4 py-2.5 font-mono font-bold text-slate-600">{b.batch_number}</td>
                                          <td className="px-4 py-2.5 text-slate-500 font-semibold">{b.summary?.branch?.name}</td>
                                          <td className="px-4 py-2.5 text-right font-extrabold text-slate-800">{b.quantity}</td>
                                          <td className="px-4 py-2.5 text-center">
                                            {b.expiry_date ? (
                                              <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${
                                                new Date(b.expiry_date) < new Date() ? "bg-rose-50 text-rose-700" : "bg-slate-100"
                                              }`}>{b.expiry_date}</span>
                                            ) : "—"}
                                          </td>
                                          <td className="px-4 py-2.5 font-medium text-slate-700">
                                            <span className="inline-flex items-center">
                                              <MapPin className="h-3 w-3 text-slate-400 mr-1" />
                                              {formatLocation(b)}
                                            </span>
                                          </td>
                                          <td className="px-4 py-2.5 text-right">
                                            {isDoctor && (
                                              <Button variant="outline" size="sm" className="px-2 py-1 text-[10px]" onClick={() => openEditBatch(b, row.medicine)}>
                                                Edit Batch
                                              </Button>
                                            )}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>

                                <div className="grid grid-cols-2 gap-3 mt-4">
                                  {/* Branch summaries card totals */}
                                  {branches.map((b) => {
                                    const sumObj = summaries.find((s) => s.medicine_id === row.medicine.id && s.branch_id === b.id);
                                    const qty = sumObj?.available_quantity || 0;
                                    return (
                                      <div key={b.id} className="bg-white border rounded-xl p-3.5 flex flex-col justify-between shadow-sm">
                                        <span className="text-[10px] font-bold text-slate-400 uppercase">{b.name} Branch Stock</span>
                                        <strong className="text-sm font-extrabold text-slate-800 mt-1">{qty} units available</strong>
                                        <span className="text-[10px] text-slate-400 flex items-center mt-2.5">
                                          <MapPin className="mr-1 h-3 w-3 text-slate-300" />
                                          {formatLocation(sumObj || null)}
                                        </span>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>

                              {/* Right column: Audit logs list */}
                              <div className="space-y-4">
                                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center">
                                  <History className="mr-1.5 h-4 w-4 text-slate-400" />
                                  Recent transaction history
                                </h4>

                                <div className="rounded-xl border bg-white p-4 max-h-[220px] overflow-y-auto space-y-3.5 shadow-sm scrollbar-thin">
                                  {transactions.filter((tx) => tx.batch?.summary?.medicine_id === row.medicine.id).length === 0 ? (
                                    <p className="text-xs text-slate-400 italic text-center py-8">No transaction history found for this medicine.</p>
                                  ) : (
                                    transactions.filter((tx) => tx.batch?.summary?.medicine_id === row.medicine.id).map((tx) => (
                                      <div key={tx.id} className="text-xs border-b border-slate-50 pb-2.5 last:border-0 last:pb-0">
                                        <div className="flex justify-between items-center font-semibold">
                                          <span className="text-slate-800">{tx.transaction_type}</span>
                                          <span className={tx.quantity_changed > 0 ? "text-emerald-600" : "text-slate-700"}>
                                            {tx.quantity_changed > 0 ? "+" : ""}{tx.quantity_changed} units
                                          </span>
                                        </div>
                                        <p className="text-[10px] text-slate-400 mt-0.5">
                                          By {tx.user?.first_name ?? "System"} @ {tx.branch?.name ?? "Unknown Branch"} • {new Date(tx.timestamp).toLocaleDateString()}
                                        </p>
                                        {tx.reason && <p className="italic text-slate-500 text-[10px] mt-1">"{tx.reason}"</p>}
                                      </div>
                                    ))
                                  )}
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* --- ADD / EDIT MEDICINE MODAL (Unified Scrollable Layout) --- */}
      <Modal 
        isOpen={modalOpen === "add-med" || modalOpen === "edit-med"} 
        onClose={() => { setModalOpen(null); setSelectedMed(null); setSelectedBatch(null); medicineForm.reset(); }} 
        title={selectedMed ? "Edit Medicine" : "Add Medicine"} 
        size="lg"
      >
        <form onSubmit={medicineForm.handleSubmit(selectedMed ? handleEditSubmit : handleAddSubmit)} className="space-y-6">
          <div className="max-h-[70vh] overflow-y-auto pr-2 space-y-6">
            
            {/* Section 1: Medicine Details */}
            <div className="space-y-4">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider border-b pb-1.5 flex items-center">
                <Boxes className="h-4 w-4 mr-1.5 text-teal-600" /> Medicine Details
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">Medicine Name *</label>
                  <input type="text" placeholder="e.g. Arnica" required {...medicineForm.register("name")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
                  {medicineForm.formState.errors.name && <p className="text-xs text-rose-500 mt-1">{String(medicineForm.formState.errors.name.message)}</p>}
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">Generic Name</label>
                  <input type="text" placeholder="e.g. Arnica Montana" {...medicineForm.register("generic_name")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">Category *</label>
                  <select required {...medicineForm.register("category_id")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm">
                    <option value="">Select Category</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">Manufacturer (Optional)</label>
                  <select {...medicineForm.register("manufacturer_id")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm">
                    <option value="">None (Optional)</option>
                    {manufacturers.map((m) => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">Potency *</label>
                  <select required {...medicineForm.register("potency_id")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm">
                    <option value="">Select Potency</option>
                    {potencies.map((p) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">Pack Unit *</label>
                  <select required {...medicineForm.register("unit_id")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm">
                    <option value="">Select Unit</option>
                    {units.map((u) => (
                      <option key={u.id} value={u.id}>{u.name} ({u.code})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">Selling Price *</label>
                  <input type="number" step="0.01" required {...medicineForm.register("selling_price")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">GST Percentage</label>
                  <input type="number" step="0.1" required {...medicineForm.register("gst_percentage")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">HSN Code</label>
                  <input type="text" placeholder="e.g. 3004" {...medicineForm.register("hsn_code")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">Barcode</label>
                  <input type="text" placeholder="e.g. 123456" {...medicineForm.register("barcode")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">QR Code</label>
                  <input type="text" placeholder="e.g. QR-123" {...medicineForm.register("qr_code")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
                </div>
                <div className="flex items-center space-x-2 pt-6">
                  <input type="checkbox" id="add_active_toggle" {...medicineForm.register("is_active")} className="h-4 w-4 rounded border-slate-300 text-teal-600 cursor-pointer" />
                  <label htmlFor="add_active_toggle" className="text-sm font-semibold text-slate-700 cursor-pointer">Mark entry as Active</label>
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase">Description</label>
                <textarea {...medicineForm.register("description")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" rows={2} />
              </div>
            </div>

            {/* Section 2: Initial Inventory Stock (Optional) */}
            <div className="space-y-4">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider border-b pb-1.5 flex items-center">
                <Sliders className="h-4 w-4 mr-1.5 text-teal-600" /> Initial Inventory Stock (Optional)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">Branch</label>
                  <select 
                    disabled={!!(selectedMed && selectedBatch)} 
                    {...medicineForm.register("branch_id")} 
                    className="mt-1 block w-full rounded-xl border p-2.5 text-sm bg-white disabled:bg-slate-100 disabled:text-slate-400"
                  >
                    <option value="">Select Branch</option>
                    {branches.map((b) => (
                      <option key={b.id} value={b.id}>{b.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">Quantity</label>
                  <input 
                    type="number" 
                    {...medicineForm.register("quantity")} 
                    className="mt-1 block w-full rounded-xl border p-2.5 text-sm" 
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">Batch Number</label>
                  <input 
                    type="text" 
                    placeholder="e.g. B-01" 
                    {...medicineForm.register("batch_number")} 
                    className="mt-1 block w-full rounded-xl border p-2.5 text-sm" 
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase">Expiry Date</label>
                  <input 
                    type="date" 
                    {...medicineForm.register("expiry_date")} 
                    className="mt-1 block w-full rounded-xl border p-2.5 text-sm" 
                  />
                </div>
              </div>

              <div className="grid grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-100">
                <h4 className="text-xs font-bold text-slate-500 uppercase col-span-4 tracking-wider flex items-center mb-1">
                  <MapPin className="h-3.5 w-3.5 text-teal-600 mr-1" /> Storage Location Details
                </h4>
                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase">Cupboard</label>
                  <input type="text" placeholder="e.g. C-1" {...medicineForm.register("cupboard")} className="mt-1 block w-full rounded-lg border bg-white p-2 text-xs focus:outline-none" />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase">Rack</label>
                  <input type="text" placeholder="e.g. R-2" {...medicineForm.register("rack")} className="mt-1 block w-full rounded-lg border bg-white p-2 text-xs focus:outline-none" />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase">Row</label>
                  <input type="text" placeholder="e.g. Row-A" {...medicineForm.register("row")} className="mt-1 block w-full rounded-lg border bg-white p-2 text-xs focus:outline-none" />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase">Column</label>
                  <input type="text" placeholder="e.g. Col-B" {...medicineForm.register("column")} className="mt-1 block w-full rounded-lg border bg-white p-2 text-xs focus:outline-none" />
                </div>
              </div>
            </div>

          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <Button variant="outline" type="button" onClick={() => { setModalOpen(null); setSelectedMed(null); setSelectedBatch(null); medicineForm.reset(); }}>
              Cancel
            </Button>
            <Button type="submit">
              {selectedMed ? "Update Medicine" : "Create Medicine & Initial Stock"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* --- STOCK IN MODAL --- */}
      <Modal isOpen={modalOpen === "stock-in"} onClose={() => setModalOpen(null)} title={`Stock Inwarding: ${selectedMed?.name || ""}`} size="lg">
        <form onSubmit={stockInForm.handleSubmit((data) => handleStockIn(data))} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Target Branch *</label>
              <select required {...stockInForm.register("branch_id")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm">
                <option value="">Select Branch</option>
                {branches.map((b) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Batch Number *</label>
              <input type="text" required placeholder="e.g. BATCH-001" {...stockInForm.register("batch_number")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Supplier</label>
              <select {...stockInForm.register("supplier_id")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm">
                <option value="">Select Supplier</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Quantity *</label>
              <input type="number" required {...stockInForm.register("quantity")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Expiry Date</label>
              <input type="date" {...stockInForm.register("expiry_date")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Purchase Cost price *</label>
              <input type="number" step="0.01" required {...stockInForm.register("purchase_price")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase">Retail Selling price *</label>
              <input type="number" step="0.01" required {...stockInForm.register("selling_price")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
            </div>
          </div>

          <div className="grid grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-100">
            <h4 className="text-xs font-bold text-slate-500 uppercase col-span-4 tracking-wider mb-1 flex items-center">
              <MapPin className="h-3.5 w-3.5 text-teal-600 mr-1" /> Storage Location Details
            </h4>
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase">Cupboard</label>
              <input type="text" placeholder="e.g. C-1" {...stockInForm.register("cupboard")} className="mt-1 block w-full rounded-lg border bg-white p-2 text-xs focus:outline-none" />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase">Rack</label>
              <input type="text" placeholder="e.g. R-2" {...stockInForm.register("rack")} className="mt-1 block w-full rounded-lg border bg-white p-2 text-xs focus:outline-none" />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase">Row</label>
              <input type="text" placeholder="e.g. Row-A" {...stockInForm.register("row")} className="mt-1 block w-full rounded-lg border bg-white p-2 text-xs focus:outline-none" />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase">Column</label>
              <input type="text" placeholder="e.g. Col-B" {...stockInForm.register("column")} className="mt-1 block w-full rounded-lg border bg-white p-2 text-xs focus:outline-none" />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Reason / Notes</label>
            <textarea {...stockInForm.register("reason")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" rows={2} />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <Button variant="outline" type="button" onClick={() => setModalOpen(null)}>Cancel</Button>
            <Button type="submit">Commit Stock In</Button>
          </div>
        </form>
      </Modal>

      {/* --- EDIT BATCH MODAL --- */}
      <Modal isOpen={modalOpen === "edit-batch"} onClose={() => setModalOpen(null)} title={`Edit Batch details: ${selectedBatch?.batch_number || ""}`} size="md">
        <form onSubmit={editBatchForm.handleSubmit(handleEditBatchSubmit)} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Retail Selling Price *</label>
            <input type="number" step="0.01" required {...editBatchForm.register("selling_price")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
          </div>

          <div className="grid grid-cols-2 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-100">
            <h4 className="text-xs font-bold text-slate-500 uppercase col-span-2 tracking-wider mb-1 flex items-center">
              <MapPin className="h-3.5 w-3.5 text-teal-600 mr-1" /> Storage Location Details
            </h4>
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase">Cupboard</label>
              <input type="text" {...editBatchForm.register("cupboard")} className="mt-1 block w-full rounded-lg border bg-white p-2 text-xs focus:outline-none" />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase">Rack</label>
              <input type="text" {...editBatchForm.register("rack")} className="mt-1 block w-full rounded-lg border bg-white p-2 text-xs focus:outline-none" />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase">Row</label>
              <input type="text" {...editBatchForm.register("row")} className="mt-1 block w-full rounded-lg border bg-white p-2 text-xs focus:outline-none" />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase">Column</label>
              <input type="text" {...editBatchForm.register("column")} className="mt-1 block w-full rounded-lg border bg-white p-2 text-xs focus:outline-none" />
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <Button variant="outline" type="button" onClick={() => setModalOpen(null)}>Cancel</Button>
            <Button type="submit">Save Batch Info</Button>
          </div>
        </form>
      </Modal>

      {/* --- DISPENSE MODAL --- */}
      <Modal isOpen={modalOpen === "dispense"} onClose={() => setModalOpen(null)} title={`Dispense stock from: ${selectedBatch?.batch_number || ""}`} size="md">
        <form onSubmit={dispenseForm.handleSubmit((data) => actionMutation.mutate({ path: "dispense", data }))} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase block">Batch Stock Details</label>
            <div className="bg-slate-50 border p-3.5 rounded-xl text-xs space-y-1.5 mt-1">
              <div>Medicine: <strong className="text-slate-800">{selectedMed?.name}</strong></div>
              <div>Available stock: <strong className="text-slate-800">{selectedBatch?.quantity} units</strong></div>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Dispense Quantity *</label>
            <input type="number" required {...dispenseForm.register("quantity")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Reason / Notes</label>
            <textarea {...dispenseForm.register("reason")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" rows={2} />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <Button variant="outline" type="button" onClick={() => setModalOpen(null)}>Cancel</Button>
            <Button type="submit">Confirm dispensation</Button>
          </div>
        </form>
      </Modal>

      {/* --- TRANSFER MODAL --- */}
      <Modal isOpen={modalOpen === "transfer"} onClose={() => setModalOpen(null)} title="Cross-Branch Transfer" size="md">
        <form onSubmit={transferForm.handleSubmit((data) => actionMutation.mutate({ path: "transfer", data }))} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Destination Branch *</label>
            <select required {...transferForm.register("to_branch_id")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm">
              <option value="">Select Target Branch</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Transfer Quantity *</label>
            <input type="number" required {...transferForm.register("quantity")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Reason / Notes</label>
            <textarea {...transferForm.register("reason")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" rows={2} />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <Button variant="outline" type="button" onClick={() => setModalOpen(null)}>Cancel</Button>
            <Button type="submit">Dispatch Transfer</Button>
          </div>
        </form>
      </Modal>

      {/* --- ADJUST MODAL --- */}
      <Modal isOpen={modalOpen === "adjust"} onClose={() => setModalOpen(null)} title="Manual Stock Adjustment" size="md">
        <form onSubmit={adjustForm.handleSubmit((data) => actionMutation.mutate({ path: "adjust", data }))} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Adjustment Type *</label>
            <select required {...adjustForm.register("transaction_type")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm">
              <option value="">Select Adjustment category</option>
              <option value="Adjustment">Generic level adjustment</option>
              <option value="Expired">Expired stock removal</option>
              <option value="Damaged">Damaged / broken container</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Quantity Delta *</label>
            <input type="number" required placeholder="e.g. +5 or -2" {...adjustForm.register("quantity_changed")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase">Reason / Notes *</label>
            <textarea required {...adjustForm.register("reason")} className="mt-1 block w-full rounded-xl border p-2.5 text-sm" rows={2} />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <Button variant="outline" type="button" onClick={() => setModalOpen(null)}>Cancel</Button>
            <Button type="submit">Commit adjustment</Button>
          </div>
        </form>
      </Modal>

      {/* --- IMPORT MODAL --- */}
      <Modal isOpen={modalOpen === "import"} onClose={() => { setModalOpen(null); setImportResult(null); setImportFile(null); }} title="Import Medicines Catalog" size="md">
        <form onSubmit={handleImportSubmit} className="space-y-4">
          <p className="text-xs text-slate-500 leading-relaxed">
            Select a CSV or Excel (.xlsx) file containing columns: <code className="bg-slate-100 p-0.5 rounded text-[10px]">Name, Generic Name, Category, Manufacturer, Potency, Unit, Quantity, Selling Price, GST Percentage, HSN Code, Active, Cupboard, Rack, Row, Column</code>.
          </p>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center cursor-pointer">
            <input
              type="file"
              accept=".csv,.xlsx"
              onChange={(e) => setImportFile(e.target.files?.[0] || null)}
              className="block w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-teal-50 file:text-teal-700 hover:file:bg-teal-100 cursor-pointer"
            />
          </div>

          {importResult && (
            <div className="rounded-xl border bg-slate-50 p-4 space-y-2">
              <h4 className="text-xs font-bold text-slate-700 uppercase">Import Summary</h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>Imported: <strong>{importResult.imported}</strong></div>
                <div>Updated: <strong>{importResult.updated}</strong></div>
                <div>Duplicate rows: <strong>{importResult.duplicate_rows}</strong></div>
                <div className="text-rose-600">Failed: <strong>{importResult.failed}</strong></div>
              </div>
              {importResult.errors.length > 0 && (
                <div className="max-h-24 overflow-y-auto border border-rose-100 bg-rose-50/50 p-2 rounded text-[10px] text-rose-800 space-y-1 mt-2">
                  {importResult.errors.map((e: string, idx: number) => <div key={idx}>{e}</div>)}
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-4">
            <Button variant="outline" type="button" onClick={() => setModalOpen(null)}>Close</Button>
            <Button type="submit" disabled={!importFile} isLoading={importLoading}>Upload and Process</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
