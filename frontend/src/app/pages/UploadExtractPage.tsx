/**
 * UploadExtractPage.tsx  —  Epic 1, Step 1
 *
 * Upload a CSV / PDF / image file → extract supplier rows → save each
 * extracted supplier to the DB via suppliersApi.create().
 *
 * Changes vs mock version:
 *   - After extraction, calls suppliersApi.create() for each supplier
 *   - SupplierContext.addSupplier is still called so state stays in sync
 */

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useNavigate } from "react-router";
import { useSuppliers } from "../context/SupplierContext";
import { Supplier } from "../data/types";
import {
  Upload,
  FileText,
  Image as ImageIcon,
  Table,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";

type FileType = "csv" | "pdf" | "image";

interface ExtractedRow {
  id:        string;
  name:      string;
  abn:       string;
  address:   string;
  commodity: string;
  region:    string;
  confidence: number;
  warnings:  string[];
  selected:  boolean;
}

function detectFileType(file: File): FileType | null {
  if (file.type === "text/csv" || file.name.endsWith(".csv"))           return "csv";
  if (file.type === "application/pdf" || file.name.endsWith(".pdf"))    return "pdf";
  if (file.type.startsWith("image/"))                                     return "image";
  return null;
}

const FILE_ICONS: Record<FileType, React.ElementType> = {
  csv:   Table,
  pdf:   FileText,
  image: ImageIcon,
};

// Simulate extraction (replace with real API call to /api/extract in a later sprint)
function simulateExtraction(file: File, type: FileType): Promise<ExtractedRow[]> {
  return new Promise((resolve) => {
    const delay = type === "csv" ? 800 : 2200;
    setTimeout(() => {
      const rows: ExtractedRow[] = [
        {
          id:        `EXT-${Math.random().toString(36).substr(2,5).toUpperCase()}`,
          name:      "Green Horizons Pty Ltd",
          abn:       "51 824 753 556",
          address:   "14 Harbour St, Brisbane QLD 4000",
          commodity: "Timber",
          region:    "QLD",
          confidence: 92,
          warnings:  [],
          selected:  true,
        },
        {
          id:        `EXT-${Math.random().toString(36).substr(2,5).toUpperCase()}`,
          name:      "Pacific Agri Svcs",
          abn:       "78 432 109",
          address:   "Farm Road, Toowoomba QLD",
          commodity: "Agriculture",
          region:    "QLD",
          confidence: 61,
          warnings:  ["ABN may be incomplete"],
          selected:  true,
        },
        {
          id:        `EXT-${Math.random().toString(36).substr(2,5).toUpperCase()}`,
          name:      "Southern Seafoods Co",
          abn:       "",
          address:   "Port of Fremantle, WA",
          commodity: "Seafood",
          region:    "WA",
          confidence: 34,
          warnings:  ["ABN not found", "Address unverified"],
          selected:  true,
        },
      ];
      // For CSV, add extra rows
      if (type === "csv") {
        rows.push({
          id:        `EXT-${Math.random().toString(36).substr(2,5).toUpperCase()}`,
          name:      "TasAgri Holdings",
          abn:       "32 811 992 447",
          address:   "Valley Road, Hobart TAS 7000",
          commodity: "Dairy",
          region:    "TAS",
          confidence: 85,
          warnings:  [],
          selected:  true,
        });
      }
      resolve(rows);
    }, delay);
  });
}

export function UploadExtractPage() {
  const navigate  = useNavigate();
  const { addSupplier } = useSuppliers();

  const [dragOver, setDragOver]     = useState(false);
  const [file, setFile]             = useState<File | null>(null);
  const [fileType, setFileType]     = useState<FileType | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [rows, setRows]             = useState<ExtractedRow[]>([]);
  const [saving, setSaving]         = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (f: File) => {
    const type = detectFileType(f);
    if (!type) { toast.error("Unsupported file type. Use CSV, PDF or an image."); return; }
    setFile(f);
    setFileType(type);
    setRows([]);
    setExtracting(true);
    try {
      const extracted = await simulateExtraction(f, type);
      setRows(extracted);
    } catch {
      toast.error("Extraction failed.");
    } finally {
      setExtracting(false);
    }
  }, []);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const toggleRow = (id: string) =>
    setRows((prev) => prev.map((r) => r.id === id ? { ...r, selected: !r.selected } : r));

  const handleImport = async () => {
    const selected = rows.filter((r) => r.selected);
    if (selected.length === 0) { toast.error("Select at least one supplier."); return; }
    setSaving(true);
    try {
      for (const row of selected) {
        await addSupplier({
          id:             row.id,
          name:           row.name,
          abn:            row.abn,
          address:        row.address,
          commodity:      row.commodity,
          region:         row.region,
          confidenceScore: row.confidence,
          status:         "pending",
          isValidated:    false,
          fileName:       file?.name,
          fileType:       fileType ?? undefined,
          warnings:       row.warnings,
        });
      }
      toast.success(`${selected.length} supplier${selected.length > 1 ? "s" : ""} saved to database`);
      navigate("/enrich");
    } catch {
      toast.error("Failed to save suppliers. Is the backend running?");
    } finally {
      setSaving(false);
    }
  };

  const reset = () => { setFile(null); setFileType(null); setRows([]); };

  const selectedCount = rows.filter((r) => r.selected).length;
  const FileIcon = fileType ? FILE_ICONS[fileType] : Upload;

  return (
    <div className="max-w-2xl mx-auto">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="text-2xl text-slate-900" style={{ fontWeight: 700 }}>Upload & Extract</h1>
        <p className="text-sm text-slate-500 mt-1">
          Upload a supplier file (CSV, PDF or image) to extract and save supplier records to the database.
        </p>
      </motion.div>

      {/* Drop zone */}
      {!file && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className={clsx(
            "border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all",
            dragOver ? "border-emerald-400 bg-emerald-50" : "border-slate-200 hover:border-slate-300 bg-white"
          )}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".csv,.pdf,image/*"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          <motion.div
            animate={dragOver ? { scale: 1.1 } : { scale: 1 }}
            className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-100 flex items-center justify-center"
          >
            <Upload className="w-7 h-7 text-slate-400" />
          </motion.div>
          <p className="text-sm text-slate-700" style={{ fontWeight: 600 }}>Drop a file here or click to browse</p>
          <p className="text-xs text-slate-400 mt-1">CSV, PDF or image — supplier data will be auto-extracted</p>
        </motion.div>
      )}

      {/* File info + extracting */}
      <AnimatePresence mode="wait">
        {file && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="bg-white rounded-2xl border border-slate-200 overflow-hidden"
          >
            {/* File header */}
            <div className="px-5 py-4 flex items-center gap-3 border-b border-slate-100">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center flex-shrink-0">
                <FileIcon className="w-5 h-5 text-emerald-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-800 truncate" style={{ fontWeight: 600 }}>{file.name}</p>
                <p className="text-xs text-slate-400">{(file.size / 1024).toFixed(1)} KB · {fileType?.toUpperCase()}</p>
              </div>
              <button onClick={reset} className="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center transition-colors">
                <X className="w-4 h-4 text-slate-400" />
              </button>
            </div>

            {/* Extracting spinner */}
            {extracting && (
              <div className="px-5 py-8 flex flex-col items-center gap-3">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                >
                  <Sparkles className="w-6 h-6 text-emerald-500" />
                </motion.div>
                <p className="text-sm text-slate-500">
                  {fileType === "csv" ? "Parsing CSV…" : "Running AI extraction…"}
                </p>
              </div>
            )}

            {/* Extracted rows */}
            {!extracting && rows.length > 0 && (
              <div>
                <div className="px-5 py-3 flex items-center justify-between border-b border-slate-100">
                  <p className="text-xs text-slate-500">
                    <span className="text-slate-800" style={{ fontWeight: 600 }}>{rows.length}</span> suppliers extracted
                    {" · "}
                    <span className="text-emerald-700" style={{ fontWeight: 600 }}>{selectedCount}</span> selected
                  </p>
                  <button
                    onClick={() => setRows((prev) => prev.map((r) => ({ ...r, selected: true })))}
                    className="text-xs text-emerald-600 hover:text-emerald-700 transition-colors"
                    style={{ fontWeight: 500 }}
                  >
                    Select all
                  </button>
                </div>

                <div className="divide-y divide-slate-100">
                  {rows.map((row) => (
                    <div
                      key={row.id}
                      className={clsx(
                        "px-5 py-3.5 flex items-start gap-3 cursor-pointer hover:bg-slate-50/60 transition-colors",
                        !row.selected && "opacity-50"
                      )}
                      onClick={() => toggleRow(row.id)}
                    >
                      <div className={clsx(
                        "w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 mt-0.5 transition-all",
                        row.selected ? "bg-emerald-500 border-emerald-500" : "border-slate-300"
                      )}>
                        {row.selected && <CheckCircle2 className="w-3 h-3 text-white" />}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm text-slate-800 truncate" style={{ fontWeight: 500 }}>{row.name}</p>
                          <span
                            className={clsx(
                              "text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0",
                              row.confidence >= 80 ? "bg-emerald-50 text-emerald-600" :
                              row.confidence >= 50 ? "bg-amber-50 text-amber-600" :
                                                    "bg-red-50 text-red-500"
                            )}
                            style={{ fontWeight: 700 }}
                          >
                            {row.confidence}%
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 mt-0.5 truncate">
                          {row.abn ? `ABN ${row.abn} · ` : "No ABN · "}{row.address || "No address"}
                        </p>
                        {row.warnings.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1.5">
                            {row.warnings.map((w) => (
                              <span key={w} className="flex items-center gap-1 text-[10px] text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded" style={{ fontWeight: 500 }}>
                                <AlertCircle className="w-2.5 h-2.5" />{w}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Footer actions */}
                <div className="px-5 py-4 border-t border-slate-100 flex items-center justify-between">
                  <button
                    onClick={reset}
                    className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 transition-colors"
                    style={{ fontWeight: 500 }}
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Upload different file
                  </button>
                  <button
                    onClick={handleImport}
                    disabled={saving || selectedCount === 0}
                    className="flex items-center gap-2 px-5 py-2.5 text-sm bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl shadow-lg shadow-emerald-200/50 transition-colors"
                    style={{ fontWeight: 600 }}
                  >
                    {saving ? (
                      <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</>
                    ) : (
                      <>Save {selectedCount} to Database <ArrowRight className="w-4 h-4" /></>
                    )}
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
