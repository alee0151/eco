/**
 * UploadExtractPage.tsx  —  Epic 1, Step 1
 *
 * User flow:
 *   1. Drop / select one or more files (CSV · PDF · image)
 *   2. Each file is processed independently → one supplier record per file
 *      (CSV files may produce multiple rows — each becomes its own supplier card)
 *   3. Extracted data is shown in an inline-editable card per supplier
 *   4. User reviews, edits if needed, removes unwanted cards
 *   5. "Finalise & Continue" saves all completed cards into the session
 *      cache (SupplierContext) and navigates to /enrichment
 *
 * No database writes. All supplier data lives in React state for the
 * duration of the browser session only.
 */

import { useState, useRef, useCallback, useId } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useNavigate } from "react-router";
import { useSuppliers } from "../context/SupplierContext";
import { extractApi } from "../lib/api";
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
  Pencil,
  ChevronDown,
  ChevronUp,
  Plus,
} from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";

type FileType = "csv" | "pdf" | "image";
type CardStatus = "queued" | "extracting" | "done" | "error";

/** One editable supplier card — maps 1-to-1 with a source file (or CSV row) */
interface SupplierCard {
  cardId:     string;
  fileName:   string;
  fileType:   FileType;
  status:     CardStatus;
  errorMsg?:  string;
  // Extracted + user-editable fields
  name:       string;
  abn:        string;
  address:    string;
  commodity:  string;
  region:     string;
  confidence: number;   // 0–100
  warnings:   string[];
  // UI state
  expanded:   boolean;  // inline editor open
  selected:   boolean;  // included in final export
}

// ── File type detection ───────────────────────────────────────────────────────
function detectFileType(file: File): { type: FileType } | { type: null; reason: string } {
  const name = file.name.toLowerCase();
  const mime = (file.type || "").toLowerCase();
  if (name.endsWith(".xlsx") || name.endsWith(".xls"))
    return { type: null, reason: "Excel files are not supported. Export as CSV first." };
  if (name.endsWith(".docx") || name.endsWith(".doc"))
    return { type: null, reason: "Word documents are not supported. Use a PDF instead." };
  if (mime === "text/csv" || name.endsWith(".csv")) return { type: "csv" };
  if (mime === "application/pdf" || name.endsWith(".pdf")) return { type: "pdf" };
  if (mime.startsWith("image/") || /\.(png|jpe?g|webp|tiff?)$/i.test(name)) return { type: "image" };
  return { type: null, reason: `Unsupported file "${file.name}". Use CSV, PDF or an image.` };
}

const FILE_ICONS: Record<FileType, React.ElementType> = {
  csv: Table, pdf: FileText, image: ImageIcon,
};

// ── CSV parser ────────────────────────────────────────────────────────────────
function parseCsv(text: string): Omit<SupplierCard, "cardId" | "fileName" | "fileType" | "status" | "expanded">[] {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const splitRow = (line: string): string[] => {
    const cols: string[] = []; let cur = ""; let inQ = false;
    for (const ch of line) {
      if (ch === '"') { inQ = !inQ; continue; }
      if (ch === ',' && !inQ) { cols.push(cur.trim()); cur = ""; continue; }
      cur += ch;
    }
    cols.push(cur.trim()); return cols;
  };
  const headers = splitRow(lines[0]).map(h => h.toLowerCase().replace(/[^a-z]/g, ""));
  const col = (aliases: string[]) => headers.findIndex(h => aliases.some(a => h.includes(a)));
  const nameIdx = col(["name","supplier","company"]);
  const abnIdx  = col(["abn"]);
  const addrIdx = col(["address","street"]);
  const commIdx = col(["commodity","product"]);
  const regIdx  = col(["region","state"]);

  return lines.slice(1).filter(l => l.trim()).map(line => {
    const c   = splitRow(line);
    const get = (i: number) => (i >= 0 ? c[i] ?? "" : "");
    const name = get(nameIdx); if (!name) return null;
    const abn = get(abnIdx); const address = get(addrIdx);
    const commodity = get(commIdx); const region = get(regIdx);
    const warnings: string[] = [];
    if (!abn) warnings.push("ABN not found");
    else if (abn.replace(/\D/g,"").length !== 11) warnings.push("ABN may be incomplete");
    if (!address) warnings.push("Address missing");
    const missing = [name,abn,address,commodity,region].filter(v=>!v).length;
    return { name, abn, address, commodity, region, confidence: Math.max(10, 100 - missing*20), warnings, selected: true };
  }).filter(Boolean) as Omit<SupplierCard,"cardId"|"fileName"|"fileType"|"status"|"expanded">[];
}

// ── Component ─────────────────────────────────────────────────────────────────
export function UploadExtractPage() {
  const navigate = useNavigate();
  const { addSupplier, clearAll } = useSuppliers();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uid = useId();

  const [dragOver, setDragOver] = useState(false);
  const [cards, setCards]       = useState<SupplierCard[]>([]);
  const [finalising, setFinalising] = useState(false);

  // ── Helpers ────────────────────────────────────────────────────────────────
  const updateCard = (cardId: string, patch: Partial<SupplierCard>) =>
    setCards(prev => prev.map(c => c.cardId === cardId ? { ...c, ...patch } : c));

  const removeCard = (cardId: string) =>
    setCards(prev => prev.filter(c => c.cardId !== cardId));

  // ── Per-file extraction ────────────────────────────────────────────────────
  const extractFile = useCallback(async (file: File, cardId: string, fileType: FileType) => {
    updateCard(cardId, { status: "extracting" });
    try {
      if (fileType === "csv") {
        const text = await file.text();
        const parsed = parseCsv(text);
        if (!parsed.length) throw new Error("No supplier rows found. Check CSV headers.");
        // For CSV: first row goes into this card; extra rows get new cards
        const [first, ...rest] = parsed;
        updateCard(cardId, { ...first, status: "done", expanded: false });
        if (rest.length) {
          const extraCards: SupplierCard[] = rest.map((r, i) => ({
            cardId:   `${cardId}-row${i+1}`,
            fileName: file.name,
            fileType: "csv",
            status:   "done",
            expanded: false,
            selected: true,
            ...r,
          }));
          setCards(prev => {
            const idx = prev.findIndex(c => c.cardId === cardId);
            const next = [...prev];
            next.splice(idx + 1, 0, ...extraCards);
            return next;
          });
        }
      } else {
        const result = await extractApi.fromFile(file);
        const stateMatch = result.address.match(/\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\b/i);
        const region = stateMatch ? stateMatch[1].toUpperCase() : "";
        const conf   = result.confidence;
        const avgConf = Math.round(((conf.name + conf.abn + conf.address + conf.commodity) / 4) * 100);
        updateCard(cardId, {
          name: result.name, abn: result.abn, address: result.address,
          commodity: result.commodity, region,
          confidence: avgConf, warnings: result.warnings,
          status: "done", expanded: false,
        });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      let friendly = `Extraction failed: ${msg}`;
      if (msg.includes("503") || msg.includes("Ollama")) friendly = "Ollama is not running — start it and retry.";
      else if (msg.includes("415")) friendly = "File type not accepted by the server.";
      updateCard(cardId, { status: "error", errorMsg: friendly });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Accept files ──────────────────────────────────────────────────────────
  const acceptFiles = useCallback((files: FileList | File[]) => {
    const fileArr = Array.from(files);
    const newCards: SupplierCard[] = [];

    for (const file of fileArr) {
      if (file.size > 10 * 1024 * 1024) {
        toast.error(`${file.name}: too large (max 10 MB).`);
        continue;
      }
      const detected = detectFileType(file);
      if (detected.type === null) { toast.error(detected.reason); continue; }

      const cardId = `${uid}-${Math.random().toString(36).substr(2,6)}`;
      newCards.push({
        cardId, fileName: file.name, fileType: detected.type,
        status: "queued", expanded: false, selected: true,
        name: "", abn: "", address: "", commodity: "", region: "",
        confidence: 0, warnings: [],
      });
      // Start extraction asynchronously — don't await (parallel)
      setTimeout(() => extractFile(file, cardId, detected.type as FileType), 0);
    }

    if (newCards.length) setCards(prev => [...prev, ...newCards]);
  }, [uid, extractFile]);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    if (e.dataTransfer.files.length) acceptFiles(e.dataTransfer.files);
  };

  // ── Finalise ───────────────────────────────────────────────────────────────
  const handleFinalise = () => {
    const ready = cards.filter(c => c.selected && c.status === "done");
    if (!ready.length) { toast.error("No completed suppliers selected."); return; }
    setFinalising(true);
    clearAll();
    for (const c of ready) {
      addSupplier({
        name: c.name, abn: c.abn, address: c.address,
        commodity: c.commodity, region: c.region,
        confidenceScore: c.confidence, status: "pending",
        isValidated: false, fileName: c.fileName,
        fileType: c.fileType, warnings: c.warnings,
      });
    }
    toast.success(`${ready.length} supplier${ready.length > 1 ? "s" : ""} saved to session.`);
    navigate("/enrichment");
  };

  // ── Derived ────────────────────────────────────────────────────────────────
  const doneCount  = cards.filter(c => c.status === "done").length;
  const readyCount = cards.filter(c => c.selected && c.status === "done").length;
  const busyCount  = cards.filter(c => c.status === "extracting" || c.status === "queued").length;

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl text-slate-900" style={{ fontWeight: 700 }}>Upload & Extract</h1>
        <p className="text-sm text-slate-500 mt-1">
          Upload one or more files. Each file maps to one supplier. Review and edit the extracted
          data, then finalise to continue to ABN enrichment.
        </p>
        <p className="text-xs text-slate-400 mt-1">
          Data is kept in memory for this session only — no database writes.
          CSV · PDF · Image (PNG, JPEG, WebP) — max 10 MB each.
        </p>
      </motion.div>

      {/* Drop zone */}
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}
        className={clsx(
          "border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all",
          dragOver ? "border-emerald-400 bg-emerald-50" : "border-slate-200 hover:border-slate-300 bg-white"
        )}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file" multiple
          className="hidden"
          accept=".csv,.pdf,image/*"
          onChange={e => e.target.files?.length && acceptFiles(e.target.files)}
        />
        <motion.div
          animate={dragOver ? { scale: 1.1 } : { scale: 1 }}
          className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-slate-100 flex items-center justify-center"
        >
          <Upload className="w-6 h-6 text-slate-400" />
        </motion.div>
        <p className="text-sm text-slate-700" style={{ fontWeight: 600 }}>
          {cards.length ? "Drop more files or click to add" : "Drop files here or click to browse"}
        </p>
        <p className="text-xs text-slate-400 mt-1">CSV · PDF · Image — max 10 MB each · multiple files allowed</p>
      </motion.div>

      {/* Card list */}
      <AnimatePresence initial={false}>
        {cards.map(card => (
          <SupplierCardRow
            key={card.cardId}
            card={card}
            onUpdate={patch => updateCard(card.cardId, patch)}
            onRemove={() => removeCard(card.cardId)}
            onRetry={() => {
              // Re-run extraction — we don't have the File object anymore,
              // so show a message directing the user to remove and re-add
              toast.info("Remove this card and re-upload the file to retry extraction.");
            }}
          />
        ))}
      </AnimatePresence>

      {/* Footer summary + finalise */}
      {cards.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between bg-white rounded-2xl border border-slate-200 px-5 py-4 shadow-sm"
        >
          <div className="text-sm text-slate-500">
            <span className="text-slate-800" style={{ fontWeight: 600 }}>{doneCount}</span> of{" "}
            <span className="text-slate-800" style={{ fontWeight: 600 }}>{cards.length}</span> processed
            {busyCount > 0 && (
              <span className="ml-2 flex items-center gap-1 text-xs text-emerald-600 inline-flex">
                <Loader2 className="w-3 h-3 animate-spin" />
                {busyCount} extracting…
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-1.5 px-3 py-2 text-xs border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg transition-colors"
              style={{ fontWeight: 500 }}
            >
              <Plus className="w-3.5 h-3.5" /> Add files
            </button>
            <button
              onClick={handleFinalise}
              disabled={finalising || readyCount === 0}
              className="flex items-center gap-2 px-5 py-2.5 text-sm bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl shadow-lg shadow-emerald-200/50 transition-colors"
              style={{ fontWeight: 600 }}
            >
              {finalising
                ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</>
                : <>Finalise {readyCount} supplier{readyCount !== 1 ? "s" : ""} <ArrowRight className="w-4 h-4" /></>}
            </button>
          </div>
        </motion.div>
      )}
    </div>
  );
}

// ── Supplier card row ─────────────────────────────────────────────────────────
interface SupplierCardRowProps {
  card:     SupplierCard;
  onUpdate: (patch: Partial<SupplierCard>) => void;
  onRemove: () => void;
  onRetry:  () => void;
}

function SupplierCardRow({ card, onUpdate, onRemove, onRetry }: SupplierCardRowProps) {
  const FileIcon = FILE_ICONS[card.fileType];

  const statusBadge = {
    queued:     <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-500" style={{fontWeight:600}}>Queued</span>,
    extracting: <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-600" style={{fontWeight:600}}><Loader2 className="w-2.5 h-2.5 animate-spin"/>Extracting</span>,
    done:       <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700" style={{fontWeight:600}}><CheckCircle2 className="w-2.5 h-2.5"/>Done</span>,
    error:      <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-red-50 text-red-600" style={{fontWeight:600}}><AlertCircle className="w-2.5 h-2.5"/>Error</span>,
  }[card.status];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8, height: 0 }}
      className={clsx(
        "bg-white rounded-2xl border shadow-sm overflow-hidden transition-all",
        card.selected ? "border-slate-200" : "border-slate-100 opacity-60"
      )}
    >
      {/* Card header */}
      <div className="flex items-center gap-3 px-4 py-3">
        {/* Select checkbox */}
        <button
          onClick={() => onUpdate({ selected: !card.selected })}
          disabled={card.status !== "done"}
          className={clsx(
            "w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 transition-all",
            card.status !== "done" ? "border-slate-200 bg-slate-50 cursor-not-allowed" :
            card.selected ? "bg-emerald-500 border-emerald-500" : "border-slate-300 hover:border-emerald-400"
          )}
        >
          {card.selected && card.status === "done" && <CheckCircle2 className="w-3 h-3 text-white" />}
        </button>

        {/* File icon */}
        <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center flex-shrink-0">
          <FileIcon className="w-4 h-4 text-emerald-600" />
        </div>

        {/* File name + status */}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-700 truncate" style={{ fontWeight: 500 }}>
            {card.status === "done" && card.name ? card.name : card.fileName}
          </p>
          <p className="text-xs text-slate-400 truncate">
            {card.fileName} · {card.fileType.toUpperCase()}
          </p>
        </div>

        {/* Confidence badge */}
        {card.status === "done" && (
          <span
            className={clsx(
              "text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0",
              card.confidence >= 80 ? "bg-emerald-50 text-emerald-600" :
              card.confidence >= 50 ? "bg-amber-50 text-amber-600" :
                                      "bg-red-50 text-red-500"
            )}
            style={{ fontWeight: 700 }}
          >
            {card.confidence}%
          </span>
        )}

        {/* Status badge */}
        {statusBadge}

        {/* Edit toggle (done only) */}
        {card.status === "done" && (
          <button
            onClick={() => onUpdate({ expanded: !card.expanded })}
            className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
            title={card.expanded ? "Collapse" : "Edit"}
          >
            {card.expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <Pencil className="w-3.5 h-3.5" />}
          </button>
        )}

        {/* Retry on error */}
        {card.status === "error" && (
          <button
            onClick={onRetry}
            className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 transition-colors"
            title="Retry"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        )}

        {/* Remove */}
        <button
          onClick={onRemove}
          className="p-1.5 rounded-lg text-slate-400 hover:bg-red-50 hover:text-red-500 transition-colors"
          title="Remove"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Extracting shimmer */}
      {(card.status === "queued" || card.status === "extracting") && (
        <div className="px-4 py-4 flex items-center gap-3 border-t border-slate-100">
          <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}>
            <Sparkles className="w-4 h-4 text-emerald-400" />
          </motion.div>
          <p className="text-xs text-slate-400">
            {card.status === "queued" ? "Waiting…" :
             card.fileType === "csv" ? "Parsing CSV…" :
             "Running OCR + AI extraction… (20–60 s)"}
          </p>
        </div>
      )}

      {/* Error message */}
      {card.status === "error" && card.errorMsg && (
        <div className="px-4 py-3 bg-red-50 border-t border-red-100 flex items-start gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-red-600">{card.errorMsg}</p>
        </div>
      )}

      {/* Warnings strip (done, not expanded) */}
      {card.status === "done" && !card.expanded && card.warnings.length > 0 && (
        <div className="px-4 pb-3 flex flex-wrap gap-1 border-t border-slate-50 pt-2">
          {card.warnings.map(w => (
            <span key={w} className="flex items-center gap-1 text-[10px] text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded" style={{ fontWeight: 500 }}>
              <AlertCircle className="w-2.5 h-2.5" />{w}
            </span>
          ))}
        </div>
      )}

      {/* Quick summary (done, not expanded) */}
      {card.status === "done" && !card.expanded && (
        <div className="px-4 pb-3 text-xs text-slate-400">
          {card.abn ? `ABN ${card.abn}` : "No ABN"}
          {card.address ? ` · ${card.address}` : ""}
          {card.commodity ? ` · ${card.commodity}` : ""}
        </div>
      )}

      {/* Inline editor (expanded) */}
      <AnimatePresence>
        {card.expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-slate-100 overflow-hidden"
          >
            <div className="px-4 py-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              {([
                { label: "Supplier name",  field: "name",      placeholder: "e.g. Acme Pty Ltd" },
                { label: "ABN",            field: "abn",       placeholder: "11 digit ABN" },
                { label: "Address",        field: "address",   placeholder: "Street, suburb, state" },
                { label: "Commodity",      field: "commodity", placeholder: "e.g. Timber" },
                { label: "Region / State", field: "region",    placeholder: "e.g. VIC" },
              ] as { label: string; field: keyof SupplierCard; placeholder: string }[]).map(({ label, field, placeholder }) => (
                <div key={field} className={field === "address" ? "sm:col-span-2" : ""}>
                  <label className="block text-[11px] text-slate-500 mb-1" style={{ fontWeight: 600 }}>
                    {label}
                  </label>
                  <input
                    type="text"
                    value={String(card[field] ?? "")}
                    onChange={e => onUpdate({ [field]: e.target.value } as Partial<SupplierCard>)}
                    placeholder={placeholder}
                    className="w-full text-sm px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 outline-none transition-all"
                  />
                </div>
              ))}
              {/* Warnings inside editor */}
              {card.warnings.length > 0 && (
                <div className="sm:col-span-2 flex flex-wrap gap-1">
                  {card.warnings.map(w => (
                    <span key={w} className="flex items-center gap-1 text-[10px] text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded" style={{ fontWeight: 500 }}>
                      <AlertCircle className="w-2.5 h-2.5" />{w}
                    </span>
                  ))}
                </div>
              )}
              <div className="sm:col-span-2 flex justify-end">
                <button
                  onClick={() => onUpdate({ expanded: false })}
                  className="flex items-center gap-1.5 px-4 py-2 text-xs bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
                  style={{ fontWeight: 600 }}
                >
                  <CheckCircle2 className="w-3.5 h-3.5" /> Done editing
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
