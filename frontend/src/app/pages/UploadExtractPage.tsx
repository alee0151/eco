import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "motion/react";
import {
  Upload,
  FileText,
  FileImage,
  FileSpreadsheet,
  CheckCircle2,
  Trash2,
  ArrowRight,
  Plus,
  Brain,
  User,
  Hash,
  MapPin,
  Tag,
  AlertCircle,
  Pencil,
} from "lucide-react";
import { useNavigate } from "react-router";
import { useSuppliers } from "../context/SupplierContext";
import clsx from "clsx";
import Papa from "papaparse";

/* ─── Types ──────────────────────────────────────────────── */
type FieldStatus = "pending" | "inferring" | "done";
type DocStage = "scanning" | "inferring" | "ready";

interface FieldState {
  value: string;
  status: FieldStatus;
}

interface DocItem {
  id: string;
  fileName: string;
  fileType: string;
  stage: DocStage;
  fields: {
    name: FieldState;
    abn: FieldState;
    address: FieldState;
    commodity: FieldState;
  };
}

/* ─── Helpers ─────────────────────────────────────────────── */
const FILE_ICON: Record<string, React.ElementType> = {
  pdf: FileText,
  image: FileImage,
  csv: FileSpreadsheet,
};

const FIELD_META = [
  { key: "name" as const, label: "Supplier Name", icon: User, span: false },
  { key: "abn" as const, label: "ABN", icon: Hash, span: false },
  { key: "address" as const, label: "Address", icon: MapPin, span: true },
  { key: "commodity" as const, label: "Commodity", icon: Tag, span: true },
];

const MOCK_POOL = [
  { name: "GreenLeaf Timber Co", abn: "53 004 085 616", address: "14 Mill Road, Daintree QLD 4873", commodity: "Timber" },
  { name: "Oceanic Fisheries Pty Ltd", abn: "12 345 678 901", address: "7 Harbour View, Fremantle WA 6160", commodity: "Seafood" },
  { name: "Murray Basin Grains", abn: "98 765 432 100", address: "Lot 5, Hay NSW 2711", commodity: "Grain" },
  { name: "TasPure Salmon", abn: "44 123 456 789", address: "Macquarie Harbour, Strahan TAS 7468", commodity: "Salmon" },
  { name: "Barossa Valley Wines", abn: "44 556 677 889", address: "23 Vine Lane, Tanunda SA 5352", commodity: "Wine Grapes" },
  { name: "Kakadu Wild Foods", abn: "66 778 899 001", address: "Jabiru NT 0886", commodity: "Bush Foods" },
  { name: "Pilbara Mining Svcs", abn: "11 223 344 556", address: "Newman WA 6753", commodity: "Iron Ore" },
];

let poolIndex = 0;
const nextMock = (fileName: string) => {
  const lc = fileName.toLowerCase();
  if (lc.includes("timber") || lc.includes("green")) return MOCK_POOL[0];
  if (lc.includes("ocean") || lc.includes("fish")) return MOCK_POOL[1];
  if (lc.includes("grain") || lc.includes("murray")) return MOCK_POOL[2];
  const m = MOCK_POOL[poolIndex % MOCK_POOL.length];
  poolIndex++;
  return m;
};

const emptyFields = (): DocItem["fields"] => ({
  name: { value: "", status: "pending" },
  abn: { value: "", status: "pending" },
  address: { value: "", status: "pending" },
  commodity: { value: "", status: "pending" },
});

/* ─── Scanning animation ─────────────────────────────────── */
function ScanAnimation({ fileName }: { fileName: string }) {
  return (
    <div className="flex gap-5 items-center py-5 px-1">
      {/* Document illustration with scan line */}
      <div className="relative w-24 h-32 flex-shrink-0">
        <div className="w-full h-full bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm flex flex-col gap-1.5 pt-3 px-3">
          <div className="h-1.5 bg-slate-100 rounded-full w-11/12" />
          <div className="h-1.5 bg-slate-100 rounded-full w-9/12" />
          <div className="h-1.5 bg-slate-100 rounded-full w-10/12" />
          <div className="h-[1px] bg-slate-100 w-full my-0.5" />
          <div className="h-1.5 bg-slate-100 rounded-full w-8/12" />
          <div className="h-1.5 bg-slate-100 rounded-full w-10/12" />
          <div className="h-1.5 bg-slate-100 rounded-full w-7/12" />
          <div className="h-1.5 bg-slate-100 rounded-full w-9/12" />
        </div>
        {/* scan line */}
        <motion.div
          animate={{ top: ["8%", "88%", "8%"] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          className="absolute left-1 right-1 h-0.5 rounded-full bg-gradient-to-r from-transparent via-emerald-400 to-transparent z-10 pointer-events-none"
        />
        <motion.div
          animate={{ top: ["8%", "88%", "8%"] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          className="absolute left-1 right-1 h-8 rounded-full bg-gradient-to-b from-transparent via-emerald-400/10 to-transparent z-10 pointer-events-none"
          style={{ transform: "translateY(-50%)" }}
        />
      </div>

      {/* Status text */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-2">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="w-4 h-4 rounded-full border-2 border-emerald-400 border-t-transparent"
          />
          <span className="text-sm text-slate-700" style={{ fontWeight: 500 }}>
            OCR Scanning
          </span>
        </div>
        <p className="text-xs text-slate-400 truncate max-w-[200px]">Reading {fileName}…</p>
        <div className="mt-3 flex flex-col gap-1.5">
          {["Detecting text regions", "Extracting structured data", "Matching field patterns"].map(
            (step, i) => (
              <motion.div
                key={step}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.35 }}
                className="flex items-center gap-2"
              >
                <motion.div
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 1.4, repeat: Infinity, delay: i * 0.25 }}
                  className="w-1.5 h-1.5 rounded-full bg-emerald-400"
                />
                <span className="text-[11px] text-slate-400">{step}</span>
              </motion.div>
            )
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Field cell ─────────────────────────────────────────── */
interface FieldCellProps {
  fieldKey: keyof DocItem["fields"];
  label: string;
  icon: React.ElementType;
  span?: boolean;
  field: FieldState;
  stage: DocStage;
  onUpdate: (key: keyof DocItem["fields"], value: string) => void;
}

function FieldCell({ fieldKey, label, icon: Icon, span, field, stage, onUpdate }: FieldCellProps) {
  const [focused, setFocused] = useState(false);
  const isEditable = stage === "ready";
  const empty = !field.value && field.status === "done";

  return (
    <div className={clsx(span ? "md:col-span-2" : "")}>
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon
          className={clsx(
            "w-3 h-3",
            field.status === "done" ? "text-slate-400" : "text-slate-300"
          )}
        />
        <label
          className="text-[11px] text-slate-500 select-none"
          style={{ fontWeight: 500 }}
        >
          {label}
        </label>
        {field.status === "done" && isEditable && (
          <motion.span
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="ml-auto flex items-center gap-0.5 text-[9px] text-indigo-400 px-1.5 py-0.5 rounded bg-indigo-50"
            style={{ fontWeight: 600 }}
          >
            <Brain className="w-2.5 h-2.5" />
            AI
          </motion.span>
        )}
      </div>

      {/* Pending skeleton */}
      {field.status === "pending" && (
        <div className="h-9 rounded-lg bg-slate-100 animate-pulse" />
      )}

      {/* Inferring shimmer */}
      {field.status === "inferring" && (
        <div className="relative h-9 rounded-lg overflow-hidden bg-indigo-50 border border-indigo-100 flex items-center px-3 gap-2">
          <motion.div
            animate={{ x: ["-100%", "200%"] }}
            transition={{ duration: 0.9, repeat: Infinity, ease: "linear" }}
            className="absolute inset-0 bg-gradient-to-r from-transparent via-indigo-200/60 to-transparent"
          />
          <Brain className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 relative z-10" />
          <span className="text-xs text-indigo-400 relative z-10">Inferring…</span>
        </div>
      )}

      {/* Done — read-only reveal */}
      {field.status === "done" && !isEditable && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 380, damping: 28 }}
          className="h-9 rounded-lg bg-emerald-50/60 border border-emerald-100 flex items-center px-3"
        >
          <span
            className={clsx(
              "text-sm truncate",
              field.value ? "text-slate-700" : "text-slate-300 italic"
            )}
          >
            {field.value || "Not detected"}
          </span>
        </motion.div>
      )}

      {/* Done — editable input */}
      {field.status === "done" && isEditable && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 380, damping: 28 }}
          className="relative group"
        >
          <input
            type="text"
            value={field.value}
            onChange={(e) => onUpdate(fieldKey, e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder={`Enter ${label.toLowerCase()}…`}
            className={clsx(
              "w-full h-9 px-3 pr-8 text-sm rounded-lg border outline-none transition-all",
              empty
                ? "bg-amber-50 border-amber-200 text-slate-700 placeholder:text-amber-400 focus:border-amber-400 focus:ring-2 focus:ring-amber-400/20"
                : focused
                ? "bg-white border-emerald-400 ring-2 ring-emerald-400/20 text-slate-800"
                : "bg-white border-slate-200 hover:border-slate-300 text-slate-700"
            )}
          />
          <Pencil
            className={clsx(
              "absolute right-2.5 top-1/2 -translate-y-1/2 w-3 h-3 transition-opacity pointer-events-none",
              focused ? "opacity-0" : "opacity-0 group-hover:opacity-40"
            )}
          />
          {empty && (
            <AlertCircle className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-amber-400 pointer-events-none" />
          )}
        </motion.div>
      )}
    </div>
  );
}

/* ─── Main page ───────────────────────────────────────────── */
export function UploadExtractPage() {
  const navigate = useNavigate();
  const { addSupplier } = useSuppliers();
  const [items, setItems] = useState<DocItem[]>([]);

  /* ── Inference simulator ── */
  const runInference = useCallback((id: string, mock: typeof MOCK_POOL[0]) => {
    const fieldOrder: Array<keyof DocItem["fields"]> = ["name", "abn", "address", "commodity"];
    const values = {
      name: mock.name,
      abn: mock.abn,
      address: mock.address,
      commodity: mock.commodity,
    };

    // Switch to inferring stage after scan
    setTimeout(() => {
      setItems((prev) =>
        prev.map((it) => (it.id === id ? { ...it, stage: "inferring" as DocStage } : it))
      );

      fieldOrder.forEach((field, idx) => {
        const baseDelay = idx * 380;

        // Start inferring this field
        setTimeout(() => {
          setItems((prev) =>
            prev.map((it) =>
              it.id === id
                ? { ...it, fields: { ...it.fields, [field]: { value: "", status: "inferring" as FieldStatus } } }
                : it
            )
          );
        }, baseDelay);

        // Resolve to done with value
        setTimeout(() => {
          setItems((prev) =>
            prev.map((it) =>
              it.id === id
                ? { ...it, fields: { ...it.fields, [field]: { value: values[field], status: "done" as FieldStatus } } }
                : it
            )
          );
        }, baseDelay + 320);
      });

      // After all fields done, mark ready
      setTimeout(() => {
        setItems((prev) =>
          prev.map((it) => (it.id === id ? { ...it, stage: "ready" as DocStage } : it))
        );
      }, fieldOrder.length * 380 + 380);
    }, 1100);
  }, []);

  /* ── Drop handler ── */
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      acceptedFiles.forEach((file) => {
        const isCsv = file.type === "text/csv" || file.name.endsWith(".csv");

        if (isCsv) {
          Papa.parse(file, {
            header: true,
            complete: (results) => {
              (results.data as any[]).forEach((row) => {
                if (!row.name && !row.supplierName && !row.abn) return;
                const id = Math.random().toString(36).substring(7);
                const csvItem: DocItem = {
                  id,
                  fileName: file.name,
                  fileType: "csv",
                  stage: "ready",
                  fields: {
                    name: { value: row.name || row.supplierName || row.Supplier || "", status: "done" },
                    abn: { value: row.abn || row.ABN || "", status: "done" },
                    address: { value: row.address || row.Address || "", status: "done" },
                    commodity: { value: row.commodity || row.Commodity || "", status: "done" },
                  },
                };
                setItems((prev) => [...prev, csvItem]);
              });
            },
          });
          return;
        }

        const id = Math.random().toString(36).substring(7);
        const mock = nextMock(file.name);

        setItems((prev) => [
          ...prev,
          {
            id,
            fileName: file.name,
            fileType: (file.type || "").includes("pdf") ? "pdf" : "image",
            stage: "scanning",
            fields: emptyFields(),
          },
        ]);

        runInference(id, mock);
      });
    },
    [runInference]
  );

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/*": [".png", ".jpg", ".jpeg", ".webp", ".tiff"],
      "text/csv": [".csv"],
    },
    noClick: false,
    noKeyboard: false,
  });

  const handleFieldUpdate = (id: string, field: keyof DocItem["fields"], value: string) => {
    setItems((prev) =>
      prev.map((it) =>
        it.id === id ? { ...it, fields: { ...it.fields, [field]: { value, status: "done" } } } : it
      )
    );
  };

  const handleRemove = (id: string) => {
    setItems((prev) => prev.filter((it) => it.id !== id));
  };

  const handleContinue = () => {
    items
      .filter((it) => it.stage === "ready")
      .forEach((it) => {
        addSupplier({
          name: it.fields.name.value,
          abn: it.fields.abn.value,
          address: it.fields.address.value,
          commodity: it.fields.commodity.value,
          fileName: it.fileName,
          fileType: it.fileType as any,
          status: "pending",
          isValidated: false,
        });
      });
    navigate("/enrichment");
  };

  const readyCount = items.filter((it) => it.stage === "ready").length;
  const processingCount = items.filter((it) => it.stage !== "ready").length;
  const canContinue = readyCount > 0 && processingCount === 0;

  /* ─── Render ─── */
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl text-slate-900" style={{ fontWeight: 700 }}>
          Upload & Extract
        </h1>
        <p className="text-slate-500 mt-1 text-sm">
          Drop supplier documents — the AI will scan, infer key fields, and let you edit before proceeding.
        </p>
      </div>

      {/* Stats row */}
      <AnimatePresence>
        {items.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="grid grid-cols-3 gap-3"
          >
            {[
              { label: "Uploaded", value: items.length, color: "blue" },
              { label: "Processing", value: processingCount, color: "indigo" },
              { label: "Ready", value: readyCount, color: "emerald" },
            ].map(({ label, value, color }) => (
              <div
                key={label}
                className="bg-white border border-slate-200 rounded-xl p-4 flex items-center gap-3"
              >
                <div
                  className={clsx(
                    "w-9 h-9 rounded-lg flex items-center justify-center text-xs",
                    color === "blue" ? "bg-blue-50 text-blue-700" :
                    color === "indigo" ? "bg-indigo-50 text-indigo-600" :
                    "bg-emerald-50 text-emerald-600"
                  )}
                  style={{ fontWeight: 700 }}
                >
                  {value}
                </div>
                <p className="text-xs text-slate-500">{label}</p>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={clsx(
          "relative border-2 border-dashed rounded-2xl transition-all cursor-pointer overflow-hidden",
          isDragActive
            ? "border-emerald-400 bg-emerald-50/60 scale-[1.01]"
            : items.length === 0
            ? "border-slate-200 hover:border-emerald-300 hover:bg-emerald-50/20 bg-white py-12"
            : "border-slate-200 hover:border-emerald-300 hover:bg-emerald-50/10 bg-white/50 py-5"
        )}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-3">
          <motion.div
            animate={isDragActive ? { scale: 1.15, y: -4 } : { scale: 1, y: 0 }}
            className={clsx(
              "rounded-2xl flex items-center justify-center transition-colors",
              items.length === 0 ? "w-16 h-16" : "w-10 h-10",
              isDragActive ? "bg-emerald-100" : "bg-slate-100"
            )}
          >
            <Upload
              className={clsx(
                "transition-colors",
                items.length === 0 ? "w-7 h-7" : "w-5 h-5",
                isDragActive ? "text-emerald-600" : "text-slate-400"
              )}
            />
          </motion.div>
          <div className="text-center">
            <p
              className={clsx("text-slate-600", items.length === 0 ? "text-sm" : "text-xs")}
              style={{ fontWeight: 500 }}
            >
              {isDragActive
                ? "Drop here to add…"
                : items.length === 0
                ? "Drag & drop supplier documents, or click to browse"
                : "Drop more files or click to add"}
            </p>
            {items.length === 0 && (
              <p className="text-xs text-slate-400 mt-1">PDF, PNG, JPG, or CSV · Up to 10 MB</p>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            {["PDF", "PNG", "JPG", "CSV"].map((fmt) => (
              <span
                key={fmt}
                className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-500"
                style={{ fontWeight: 600 }}
              >
                {fmt}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Document cards */}
      <div className="space-y-4">
        <AnimatePresence mode="popLayout">
          {items.map((item) => {
            const Icon = FILE_ICON[item.fileType] || FileText;
            const isScanning = item.stage === "scanning";
            const isInferring = item.stage === "inferring";
            const isReady = item.stage === "ready";

            return (
              <motion.div
                key={item.id}
                layout
                initial={{ opacity: 0, y: 20, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: -30, height: 0, marginBottom: 0 }}
                transition={{ type: "spring", stiffness: 350, damping: 28 }}
                className={clsx(
                  "bg-white rounded-2xl border overflow-hidden transition-shadow",
                  isReady
                    ? "border-slate-200 shadow-sm"
                    : isInferring
                    ? "border-indigo-200 shadow-sm shadow-indigo-100/50"
                    : "border-slate-200"
                )}
              >
                {/* Card header */}
                <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    {/* File type icon */}
                    <div
                      className={clsx(
                        "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
                        item.fileType === "pdf"
                          ? "bg-red-50 text-red-500"
                          : item.fileType === "csv"
                          ? "bg-green-50 text-green-500"
                          : "bg-purple-50 text-purple-500"
                      )}
                    >
                      <Icon className="w-4 h-4" />
                    </div>

                    {/* File info */}
                    <div className="min-w-0">
                      <p className="text-sm text-slate-800 truncate" style={{ fontWeight: 500 }}>
                        {item.fileName}
                      </p>
                      <p className="text-[11px] text-slate-400 uppercase">{item.fileType}</p>
                    </div>

                    {/* Stage badge */}
                    {isScanning && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-blue-50 text-blue-600 flex-shrink-0" style={{ fontWeight: 500 }}>
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
                          className="w-3 h-3 border-[1.5px] border-blue-400 border-t-transparent rounded-full"
                        />
                        Scanning
                      </span>
                    )}
                    {isInferring && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-indigo-50 text-indigo-600 flex-shrink-0" style={{ fontWeight: 500 }}>
                        <motion.div
                          animate={{ scale: [1, 1.3, 1] }}
                          transition={{ duration: 0.9, repeat: Infinity }}
                          className="w-2.5 h-2.5"
                        >
                          <Brain className="w-2.5 h-2.5" />
                        </motion.div>
                        Inferring
                      </span>
                    )}
                    {isReady && (
                      <motion.span
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ type: "spring", stiffness: 400, damping: 20 }}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-emerald-50 text-emerald-600 flex-shrink-0"
                        style={{ fontWeight: 500 }}
                      >
                        <CheckCircle2 className="w-3 h-3" />
                        Ready
                      </motion.span>
                    )}
                  </div>

                  <button
                    onClick={() => handleRemove(item.id)}
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors flex-shrink-0"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                {/* Card body */}
                <div className="px-5 pb-5">
                  {/* Scanning animation */}
                  {isScanning && <ScanAnimation fileName={item.fileName} />}

                  {/* Inferring + Ready: field grid */}
                  {(isInferring || isReady) && (
                    <motion.div
                      initial={isInferring ? { opacity: 0 } : false}
                      animate={{ opacity: 1 }}
                      className="pt-4 grid grid-cols-1 md:grid-cols-2 gap-x-5 gap-y-4"
                    >
                      {FIELD_META.map((f) => (
                        <FieldCell
                          key={f.key}
                          fieldKey={f.key}
                          label={f.label}
                          icon={f.icon}
                          span={f.span}
                          field={item.fields[f.key]}
                          stage={item.stage}
                          onUpdate={(key, val) => handleFieldUpdate(item.id, key, val)}
                        />
                      ))}
                    </motion.div>
                  )}

                  {/* Ready footer note */}
                  {isReady && (
                    <motion.p
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.3 }}
                      className="mt-3 text-[11px] text-slate-400 flex items-center gap-1"
                    >
                      <Brain className="w-3 h-3 text-indigo-300" />
                      Fields inferred by AI — review and edit as needed
                    </motion.p>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* Bottom actions */}
      <AnimatePresence>
        {items.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center justify-between pt-4 border-t border-slate-200"
          >
            <button
              onClick={() => open()}
              className="flex items-center gap-2 px-4 py-2 text-sm text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              style={{ fontWeight: 500 }}
            >
              <Plus className="w-4 h-4" />
              Add More
            </button>

            <div className="flex items-center gap-3">
              {processingCount > 0 && (
                <p className="text-xs text-slate-400">
                  {processingCount} document{processingCount > 1 ? "s" : ""} still processing…
                </p>
              )}
              <button
                onClick={handleContinue}
                disabled={!canContinue}
                className="flex items-center gap-2 px-5 py-2.5 text-sm bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl transition-colors shadow-sm shadow-emerald-200"
                style={{ fontWeight: 500 }}
              >
                Run ABN Enrichment
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}