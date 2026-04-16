import { useEffect, useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useNavigate } from "react-router";
import { useSuppliers } from "../context/SupplierContext";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  ArrowRight,
  Database,
  Globe,
  Search,
  Shield,
  Zap,
  Clock,
  AlertTriangle,
} from "lucide-react";
import clsx from "clsx";
import { enrichApi } from "../lib/api";
import { geocodeSupplier } from "../lib/geocode";

type StepStatus =
  | "waiting"
  | "connecting"
  | "validating"
  | "enriching"
  | "geocoding"
  | "done"
  | "failed"
  | "error";

interface SupplierProgress {
  id: string;
  name: string;
  abn: string;
  status: StepStatus;
  progress: number;
  statusLabel: string;
  errorMsg?: string;
}

const LABELS: Record<StepStatus, string> = {
  waiting:    "In queue",
  connecting: "Connecting to ABR...",
  validating: "Validating ABN...",
  enriching:  "Enriching data...",
  geocoding:  "Geocoding address...",
  done:       "Enriched & Located",
  failed:     "ABN not found",
  error:      "Service unavailable",
};

/**
 * Validates an ABN against the Australian Business Register format:
 * - Strip all spaces and hyphens
 * - Must be exactly 11 digits
 */
function isValidAbnFormat(abn: string): boolean {
  const digits = abn.replace(/[\s\-]/g, "");
  return /^\d{11}$/.test(digits);
}

export function EnrichmentPage() {
  const navigate = useNavigate();
  const { suppliers, updateSupplier } = useSuppliers();
  const [progress, setProgress] = useState<SupplierProgress[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [countdown, setCountdown] = useState(6);
  const started = useRef(false);

  const updateRow = useCallback(
    (id: string, patch: Partial<SupplierProgress>) => {
      setProgress((prev) =>
        prev.map((p) =>
          p.id === id
            ? {
                ...p,
                ...patch,
                statusLabel: patch.status ? LABELS[patch.status] : p.statusLabel,
              }
            : p
        )
      );
    },
    []
  );

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    // Snapshot suppliers once at effect start — intentional exclusion from deps
    const pending = suppliers.filter((s) => !s.isValidated);

    if (pending.length === 0) {
      setIsComplete(true);
      return;
    }

    setProgress(
      pending.map((s) => ({
        id: s.id,
        name: s.name || "Unknown",
        abn: s.abn || "",
        status: "waiting",
        progress: 0,
        statusLabel: LABELS.waiting,
      }))
    );

    /**
     * Enrich a single supplier via POST /api/enrich, then immediately
     * geocode the resulting address.
     *
     * FIX 1: geocodeSupplier is now called after ABR enrichment and the
     *        resulting coordinates are written back via updateSupplier.
     * FIX 2: geocodeSupplier receives enrichedAddress (post-ABR) as the
     *        primary input, falling back to rawAddress then supplierName.
     */
    const enrichOne = async (
      supplier: (typeof pending)[number],
      staggerMs: number
    ) => {
      const supplierId = supplier.id;
      await new Promise((r) => setTimeout(r, staggerMs));

      // Step 1 — connecting
      updateRow(supplierId, { status: "connecting", progress: 20 });
      await new Promise((r) => setTimeout(r, 400));

      // Step 2 — client-side format check
      updateRow(supplierId, { status: "validating", progress: 40 });
      await new Promise((r) => setTimeout(r, 300));

      if (!supplier.abn || !isValidAbnFormat(supplier.abn)) {
        // Invalid ABN — skip ABR call but still attempt geocoding
        updateSupplier(supplierId, {
          isValidated:    true,
          abnFound:       false,
          abrStatus:      "",
          confidenceScore: 10,
        });

        // Geocode with raw address only (no enrichedAddress available)
        updateRow(supplierId, { status: "geocoding", progress: 70 });
        await runGeocode(supplierId, undefined, supplier.address, supplier.name);

        updateRow(supplierId, { status: "failed", progress: 100 });
        return;
      }

      // Step 3 — enrich via ABR backend
      updateRow(supplierId, { status: "enriching", progress: 60 });

      let enrichedAddress: string | undefined;
      let enrichedName: string | undefined;

      try {
        const enriched = await enrichApi.enrich(
          supplier.abn,
          supplier.name    ?? "",
          supplier.address ?? "",
        );

        enrichedAddress = enriched.enriched_address ?? undefined;
        enrichedName    = enriched.enriched_name    ?? undefined;

        // Persist ABR enrichment data (synchronous in-memory)
        updateSupplier(supplierId, {
          isValidated:        true,
          enrichedName,
          enrichedAddress,
          abrStatus:          enriched.abr_status          ?? undefined,
          abnFound:           enriched.abn_found           ?? undefined,
          nameDiscrepancy:    enriched.name_discrepancy    ?? undefined,
          addressDiscrepancy: enriched.address_discrepancy ?? undefined,
          confidenceScore:    enriched.confidence_score    ?? undefined,
        });

        updateRow(supplierId, {
          status: enriched.abn_found ? "geocoding" : "failed",
          progress: 75,
        });

        if (!enriched.abn_found) {
          // ABN not found — still geocode with raw address as best effort
          await runGeocode(supplierId, undefined, supplier.address, supplier.name);
          updateRow(supplierId, { status: "failed", progress: 100 });
          return;
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        const isUnavailable =
          msg.includes("404") || msg.includes("500") || msg.includes("fetch");

        updateSupplier(supplierId, {
          isValidated:    true,
          confidenceScore: 0,
        });

        // Still attempt geocoding on network/service error so the map
        // has the best possible coordinates from the raw address.
        updateRow(supplierId, { status: "geocoding", progress: 75 });
        await runGeocode(supplierId, undefined, supplier.address, supplier.name);

        updateRow(supplierId, {
          status:   isUnavailable ? "error" : "failed",
          progress: 100,
          errorMsg: isUnavailable
            ? "ABR service unavailable — check backend"
            : msg,
        });
        return;
      }

      // Step 4 — geocode the ABR-validated address
      // FIX: enrichedAddress is passed as the primary input so Nominatim
      // receives the full validated street address rather than an
      // abbreviated or ambiguous raw CSV value.
      updateRow(supplierId, { status: "geocoding", progress: 80 });
      await runGeocode(
        supplierId,
        enrichedAddress,   // ← FIX 2: prefer enriched (post-ABR) address
        supplier.address,  // fallback: original CSV
        enrichedName ?? supplier.name,
      );

      updateRow(supplierId, { status: "done", progress: 100 });
    };

    /**
     * Run geocoding for one supplier and write coordinates back to context.
     *
     * FIX 1: This function did not previously exist — coordinates were never
     *        written back to supplier state, so s.coordinates was always
     *        undefined, causing supplierBbox() in MapView to return null and
     *        all map layer fetches to silently bail out.
     */
    const runGeocode = async (
      supplierId: string,
      enrichedAddr: string | undefined,
      rawAddr: string,
      name: string,
    ) => {
      try {
        const geo = await geocodeSupplier(enrichedAddr, rawAddr, name);
        if (geo) {
          updateSupplier(supplierId, {
            coordinates:     { lat: geo.lat, lng: geo.lng },
            resolutionLevel: geo.resolutionLevel,
            inferenceMethod: geo.inferenceMethod,
            // surface a warning badge if only coarse resolution was achieved
            ...(geo.resolutionLevel !== 'facility' && geo.resolutionLevel !== 'regional'
              ? { warnings: [`Geocode resolution: ${geo.resolutionLevel} via ${geo.inferenceMethod}`] }
              : {}),
          });
        }
      } catch {
        // Non-fatal: supplier will appear in ApprovedSupplierCard with
        // "Awaiting location data" badge rather than crashing the enrichment.
      }
    };

    // Fire all enrichments in parallel, staggered by 700 ms each.
    const allPromises = pending.map((s, i) => enrichOne(s, i * 700));
    Promise.allSettled(allPromises).then(() => setIsComplete(true));

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [updateSupplier, updateRow]);

  // countdown + auto-redirect
  useEffect(() => {
    if (!isComplete) return;
    const t = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) { clearInterval(t); navigate("/review"); return 0; }
        return c - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [isComplete, navigate]);

  const doneCount    = progress.filter(p => p.status === "done" || p.status === "failed" || p.status === "error").length;
  const successCount = progress.filter(p => p.status === "done").length;
  const failCount    = progress.filter(p => p.status === "failed").length;
  const errorCount   = progress.filter(p => p.status === "error").length;
  const overallPct   = progress.length
    ? Math.round(progress.reduce((a, p) => a + p.progress, 0) / progress.length)
    : 0;

  const pipelineSteps = [
    { icon: Search,   label: "Lookup",   threshold: 0   },
    { icon: Globe,    label: "Connect",  threshold: 20  },
    { icon: Shield,   label: "Validate", threshold: 40  },
    { icon: Database, label: "Enrich",   threshold: 60  },
    { icon: Globe,    label: "Geocode",  threshold: 80  },
    { icon: Zap,      label: "Complete", threshold: 100 },
  ];

  return (
    <div className="max-w-3xl mx-auto">
      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-10"
      >
        <motion.div
          initial={{ scale: 0, rotate: -30 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: "spring", stiffness: 200, delay: 0.1 }}
          className="w-20 h-20 mx-auto mb-5 rounded-2xl flex items-center justify-center bg-gradient-to-br from-emerald-400 to-emerald-600 shadow-lg shadow-emerald-200"
        >
          {isComplete ? (
            <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 300 }}>
              <CheckCircle2 className="w-10 h-10 text-white" />
            </motion.div>
          ) : (
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 3, repeat: Infinity, ease: "linear" }}>
              <Database className="w-10 h-10 text-white" />
            </motion.div>
          )}
        </motion.div>

        <h1 className="text-2xl text-slate-900" style={{ fontWeight: 700 }}>
          {isComplete ? "Enrichment & Geocoding Complete" : "Enriching & Locating Suppliers"}
        </h1>
        <p className="text-slate-500 mt-2 max-w-md mx-auto text-sm">
          {isComplete
            ? `${successCount} of ${progress.length} suppliers validated and geocoded.${
                failCount  > 0 ? ` ${failCount} ABN not found.`      : ""}
              ${errorCount > 0 ? ` ${errorCount} service errors.`    : ""}`
            : "Validating ABNs via the Australian Business Register, then geocoding each supplier address to Australia..."}
        </p>
      </motion.div>

      {/* Overall Progress Card */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="bg-white rounded-2xl border border-slate-200 p-6 mb-6"
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-slate-600" style={{ fontWeight: 500 }}>Processing</span>
          <span className="text-sm text-emerald-600" style={{ fontWeight: 700 }}>{doneCount}/{progress.length}</span>
        </div>

        <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden mb-6">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400"
            animate={{ width: `${overallPct}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>

        {/* Pipeline visualization — now includes Geocode step */}
        <div className="flex items-center justify-between relative">
          <div className="absolute top-4 left-6 right-6 h-[2px] bg-slate-100 z-0" />
          <motion.div
            className="absolute top-4 left-6 h-[2px] bg-emerald-400 z-0"
            animate={{ width: `${Math.min(overallPct, 100) * 0.88}%` }}
            transition={{ duration: 0.5 }}
          />
          {pipelineSteps.map((step) => {
            const active = overallPct >= step.threshold;
            return (
              <div key={step.label} className="flex flex-col items-center gap-2 relative z-10">
                <motion.div
                  animate={{ scale: active ? 1 : 0.85, backgroundColor: active ? "rgb(16 185 129)" : "rgb(241 245 249)" }}
                  className="w-8 h-8 rounded-full flex items-center justify-center"
                >
                  <step.icon className={clsx("w-3.5 h-3.5 transition-colors", active ? "text-white" : "text-slate-400")} />
                </motion.div>
                <span className={clsx("text-[10px]", active ? "text-emerald-600" : "text-slate-400")} style={{ fontWeight: 600 }}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </motion.div>

      {/* Supplier List */}
      <div className="space-y-2.5 mb-8">
        <AnimatePresence>
          {progress.map((sp, i) => (
            <motion.div
              key={sp.id}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.06 }}
              className={clsx(
                "bg-white rounded-xl border px-5 py-4 flex items-center gap-4 transition-all",
                sp.status === "done"    ? "border-emerald-200" :
                sp.status === "failed"  ? "border-red-200"    :
                sp.status === "error"   ? "border-amber-200"  :
                sp.status === "geocoding" ? "border-blue-200" :
                "border-slate-200"
              )}
            >
              <div className="flex-shrink-0">
                {sp.status === "done" ? (
                  <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 400 }}>
                    <div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                    </div>
                  </motion.div>
                ) : sp.status === "failed" ? (
                  <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 400 }}>
                    <div className="w-9 h-9 rounded-lg bg-red-50 flex items-center justify-center">
                      <XCircle className="w-5 h-5 text-red-500" />
                    </div>
                  </motion.div>
                ) : sp.status === "error" ? (
                  <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 400 }}>
                    <div className="w-9 h-9 rounded-lg bg-amber-50 flex items-center justify-center">
                      <AlertTriangle className="w-5 h-5 text-amber-500" />
                    </div>
                  </motion.div>
                ) : sp.status === "waiting" ? (
                  <div className="w-9 h-9 rounded-lg bg-slate-50 flex items-center justify-center">
                    <Clock className="w-5 h-5 text-slate-300" />
                  </div>
                ) : sp.status === "geocoding" ? (
                  <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center">
                    <Globe className="w-5 h-5 text-blue-400 animate-pulse" />
                  </div>
                ) : (
                  <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center">
                    <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                  </div>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm text-slate-800 truncate" style={{ fontWeight: 500 }}>{sp.name}</p>
                  <span
                    className={clsx(
                      "text-[11px] px-2 py-0.5 rounded-full flex-shrink-0",
                      sp.status === "done"      ? "bg-emerald-50 text-emerald-600" :
                      sp.status === "failed"    ? "bg-red-50 text-red-600"         :
                      sp.status === "error"     ? "bg-amber-50 text-amber-600"     :
                      sp.status === "geocoding" ? "bg-blue-50 text-blue-600"       :
                      sp.status === "waiting"   ? "bg-slate-50 text-slate-400"     :
                      "bg-blue-50 text-blue-600"
                    )}
                    style={{ fontWeight: 600 }}
                  >
                    {sp.statusLabel}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">ABN: {sp.abn || "Not provided"}</p>
                {sp.errorMsg && <p className="text-xs text-amber-500 mt-0.5 truncate">{sp.errorMsg}</p>}
                <div className="mt-2 h-1 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div
                    className={clsx(
                      "h-full rounded-full",
                      sp.status === "failed"  ? "bg-red-300"    :
                      sp.status === "error"   ? "bg-amber-300"  :
                      "bg-emerald-400"
                    )}
                    animate={{ width: `${sp.progress}%` }}
                    transition={{ duration: 0.35 }}
                  />
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Done state */}
      <AnimatePresence>
        {isComplete && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center gap-3"
          >
            <div className="flex items-center gap-3 mb-2 flex-wrap justify-center">
              {successCount > 0 && (
                <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-700" style={{ fontWeight: 600 }}>
                  <CheckCircle2 className="w-3.5 h-3.5" />{successCount} Validated & Geocoded
                </span>
              )}
              {failCount > 0 && (
                <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-red-50 text-red-600" style={{ fontWeight: 600 }}>
                  <XCircle className="w-3.5 h-3.5" />{failCount} ABN Not Found
                </span>
              )}
              {errorCount > 0 && (
                <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-amber-50 text-amber-600" style={{ fontWeight: 600 }}>
                  <AlertTriangle className="w-3.5 h-3.5" />{errorCount} Service Error
                </span>
              )}
            </div>
            <button
              onClick={() => navigate("/review")}
              className="flex items-center gap-2 px-6 py-3 text-sm bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-lg shadow-emerald-200/50 transition-colors"
              style={{ fontWeight: 600 }}
            >
              View Results <ArrowRight className="w-4 h-4" />
            </button>
            <p className="text-xs text-slate-400">Redirecting in {countdown}s...</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
