import { useEffect, useState, useRef } from "react";
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
} from "lucide-react";
import clsx from "clsx";

type StepStatus = "waiting" | "connecting" | "validating" | "enriching" | "done" | "failed";

interface SupplierProgress {
  id: string;
  name: string;
  abn: string;
  status: StepStatus;
  progress: number;
  statusLabel: string;
}

const LABELS: Record<StepStatus, string> = {
  waiting: "In queue",
  connecting: "Connecting to ABR...",
  validating: "Validating ABN...",
  enriching: "Enriching data...",
  done: "Enriched",
  failed: "Not found",
};

export function EnrichmentPage() {
  const navigate = useNavigate();
  const { suppliers, updateSupplier } = useSuppliers();
  const [progress, setProgress] = useState<SupplierProgress[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [countdown, setCountdown] = useState(6);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

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

    const update = (id: string, status: StepStatus, prog: number) => {
      setProgress((prev) =>
        prev.map((p) =>
          p.id === id ? { ...p, status, progress: prog, statusLabel: LABELS[status] } : p
        )
      );
    };

    pending.forEach((supplier, i) => {
      const d = i * 900;

      setTimeout(() => update(supplier.id, "connecting", 25), d + 200);
      setTimeout(() => update(supplier.id, "validating", 50), d + 600);
      setTimeout(() => update(supplier.id, "enriching", 75), d + 1100);

      setTimeout(() => {
        const abnOk = (supplier.abn || "").length >= 9;
        const failed = !supplier.abn || supplier.abn.length < 3;

        const enrichedName = !failed
          ? (supplier.name || "").replace(/\b(Co|Svcs)\b/g, (m) =>
              m === "Co" ? "Co Pty Ltd" : "Services Pty Ltd"
            )
          : undefined;
        const enrichedAddress = !failed
          ? (supplier.address || "").includes("QLD")
            ? supplier.address + ", Australia"
            : supplier.address
          : undefined;

        updateSupplier(supplier.id, {
          isValidated: true,
          enrichedName,
          enrichedAddress,
          abnFound: !failed,
          abrStatus: failed ? "" : "Active",
          nameDiscrepancy: enrichedName !== supplier.name,
          addressDiscrepancy: enrichedAddress !== supplier.address,
          confidenceScore: failed ? 15 : abnOk ? 90 : 50,
        });

        update(supplier.id, failed ? "failed" : "done", 100);
      }, d + 1600);
    });

    setTimeout(
      () => setIsComplete(true),
      pending.length * 900 + 2000
    );
  }, [suppliers, updateSupplier]);

  // countdown + auto redirect
  useEffect(() => {
    if (!isComplete) return;
    const t = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) {
          clearInterval(t);
          navigate("/review");
          return 0;
        }
        return c - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [isComplete, navigate]);

  const doneCount = progress.filter((p) => p.status === "done" || p.status === "failed").length;
  const successCount = progress.filter((p) => p.status === "done").length;
  const failCount = progress.filter((p) => p.status === "failed").length;
  const overallPct = progress.length ? Math.round(progress.reduce((a, p) => a + p.progress, 0) / progress.length) : 0;

  const pipelineSteps = [
    { icon: Search, label: "Lookup", threshold: 0 },
    { icon: Globe, label: "Connect", threshold: 25 },
    { icon: Shield, label: "Validate", threshold: 50 },
    { icon: Database, label: "Enrich", threshold: 75 },
    { icon: Zap, label: "Complete", threshold: 100 },
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
          {isComplete ? "Enrichment Complete" : "Enriching Supplier Data"}
        </h1>
        <p className="text-slate-500 mt-2 max-w-md mx-auto text-sm">
          {isComplete
            ? `${successCount} of ${progress.length} suppliers validated successfully.${failCount > 0 ? ` ${failCount} need manual review.` : ""}`
            : "Connecting to the Australian Business Register to validate ABNs and enrich supplier data..."}
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
          <span className="text-sm text-emerald-600" style={{ fontWeight: 700 }}>
            {doneCount}/{progress.length}
          </span>
        </div>

        {/* Progress bar */}
        <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden mb-6">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400"
            animate={{ width: `${overallPct}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>

        {/* Pipeline visualization */}
        <div className="flex items-center justify-between relative">
          {/* Connection line */}
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
                  animate={{
                    scale: active ? 1 : 0.85,
                    backgroundColor: active ? "rgb(16 185 129)" : "rgb(241 245 249)",
                  }}
                  className="w-8 h-8 rounded-full flex items-center justify-center"
                >
                  <step.icon
                    className={clsx(
                      "w-3.5 h-3.5 transition-colors",
                      active ? "text-white" : "text-slate-400"
                    )}
                  />
                </motion.div>
                <span
                  className={clsx(
                    "text-[10px]",
                    active ? "text-emerald-600" : "text-slate-400"
                  )}
                  style={{ fontWeight: 600 }}
                >
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
                sp.status === "done"
                  ? "border-emerald-200"
                  : sp.status === "failed"
                  ? "border-red-200"
                  : "border-slate-200"
              )}
            >
              {/* Icon */}
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
                ) : sp.status === "waiting" ? (
                  <div className="w-9 h-9 rounded-lg bg-slate-50 flex items-center justify-center">
                    <Clock className="w-5 h-5 text-slate-300" />
                  </div>
                ) : (
                  <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center">
                    <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm text-slate-800 truncate" style={{ fontWeight: 500 }}>
                    {sp.name}
                  </p>
                  <span
                    className={clsx(
                      "text-[11px] px-2 py-0.5 rounded-full flex-shrink-0",
                      sp.status === "done"
                        ? "bg-emerald-50 text-emerald-600"
                        : sp.status === "failed"
                        ? "bg-red-50 text-red-600"
                        : sp.status === "waiting"
                        ? "bg-slate-50 text-slate-400"
                        : "bg-blue-50 text-blue-600"
                    )}
                    style={{ fontWeight: 600 }}
                  >
                    {sp.statusLabel}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  ABN: {sp.abn || "Not provided"}
                </p>
                {/* Mini progress */}
                <div className="mt-2 h-1 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div
                    className={clsx(
                      "h-full rounded-full",
                      sp.status === "failed" ? "bg-red-300" : "bg-emerald-400"
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
            {/* Summary pills */}
            <div className="flex items-center gap-3 mb-2">
              {successCount > 0 && (
                <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-700" style={{ fontWeight: 600 }}>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {successCount} Validated
                </span>
              )}
              {failCount > 0 && (
                <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-red-50 text-red-600" style={{ fontWeight: 600 }}>
                  <XCircle className="w-3.5 h-3.5" />
                  {failCount} Need Review
                </span>
              )}
            </div>

            <button
              onClick={() => navigate("/review")}
              className="flex items-center gap-2 px-6 py-3 text-sm bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-lg shadow-emerald-200/50 transition-colors"
              style={{ fontWeight: 600 }}
            >
              View Results
              <ArrowRight className="w-4 h-4" />
            </button>
            <p className="text-xs text-slate-400">
              Redirecting in {countdown}s...
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}