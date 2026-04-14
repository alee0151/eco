/**
 * BiodiversityPage.tsx  —  Epic 2
 *
 * Loads live biodiversity data from the backend (species, kba, capad, ibra)
 * and computes a risk summary for each approved/validated supplier.
 *
 * Data flow:
 *   1. Load all approved/validated suppliers from SupplierContext (already from DB)
 *   2. For each supplier with coordinates → call /api/biodiversity/risk-summary
 *   3. Fetch real DB counts from /api/biodiversity/counts for stat cards
 *   4. Render risk cards per supplier
 *
 * Fixes applied:
 *   - Stat cards now show real DB counts (was hardcoded 9,000+ / 270+)
 *   - IBRA lookup fix is backend-side (biodiversity.py)
 *   - Per-supplier error isolation — one failed call doesn't blank the list
 *   - CSV export wired up
 *   - Supplier candidate filter broadened to catch all enriched/validated states
 */

import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useSuppliers } from "../context/SupplierContext";
import { riskApi, SupplierRiskSummary } from "../lib/api";
import clsx from "clsx";
import {
  Leaf, MapPin, AlertTriangle, CheckCircle2,
  Shield, Bird, TreePine, Loader2, RefreshCw, Info, Download,
} from "lucide-react";

const BASE: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

// ── Risk level helpers ──────────────────────────────────────────────────────
function riskLevel(s: SupplierRiskSummary): "critical" | "high" | "medium" | "low" {
  const score = s.species_nearby * 2 + s.protected_areas_nearby * 3 + s.kba_nearby * 5;
  if (score >= 30) return "critical";
  if (score >= 15) return "high";
  if (score >= 5)  return "medium";
  return "low";
}

const RISK_COLORS = {
  critical: { bg: "bg-red-50",    border: "border-red-200",    text: "text-red-700",    dot: "bg-red-500"    },
  high:     { bg: "bg-orange-50", border: "border-orange-200", text: "text-orange-700", dot: "bg-orange-500" },
  medium:   { bg: "bg-amber-50",  border: "border-amber-200",  text: "text-amber-700",  dot: "bg-amber-500"  },
  low:      { bg: "bg-emerald-50",border: "border-emerald-200",text: "text-emerald-700",dot: "bg-emerald-500"},
};

// ── DB counts type ────────────────────────────────────────────────────────────
interface BiodiversityCounts {
  capad_active:  number;
  kba_total:     number;
  species_total: number;
}

// ── Risk card ───────────────────────────────────────────────────────────────
function RiskCard({ summary }: { summary: SupplierRiskSummary }) {
  const level = riskLevel(summary);
  const c = RISK_COLORS[level];
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      layout
      className={clsx("rounded-xl border p-4 cursor-pointer", c.bg, c.border)}
      onClick={() => setExpanded((v) => !v)}
    >
      <div className="flex items-start gap-3">
        {/* Risk dot */}
        <div className={clsx("w-2.5 h-2.5 rounded-full mt-1 flex-shrink-0", c.dot)} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm text-slate-900 truncate" style={{ fontWeight: 600 }}>
              {summary.supplier_name}
            </p>
            <span className={clsx("text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wide", c.text, c.bg)} style={{ fontWeight: 700 }}>
              {level}
            </span>
          </div>

          {/* Coordinates */}
          {(summary.lat || summary.lng) && (
            <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1">
              <MapPin className="w-3 h-3" />
              {summary.lat.toFixed(3)}, {summary.lng.toFixed(3)}
              {summary.ibra_region && (
                <span className="ml-1 text-slate-500">· {summary.ibra_region}</span>
              )}
            </p>
          )}

          {/* Stats row */}
          <div className="flex items-center gap-4 mt-2">
            <Stat icon={Bird}     label="Species"        value={summary.species_nearby} />
            <Stat icon={Shield}   label="Protected areas" value={summary.protected_areas_nearby} />
            <Stat icon={TreePine} label="KBAs"            value={summary.kba_nearby} />
          </div>
        </div>
      </div>

      {/* Expanded: threatened species list */}
      <AnimatePresence>
        {expanded && summary.threatened_species_names.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-3 pt-3 border-t border-current/10">
              <p className="text-[11px] text-slate-500 mb-1.5" style={{ fontWeight: 600 }}>Species nearby (sample)</p>
              <div className="flex flex-wrap gap-1.5">
                {summary.threatened_species_names.map((name) => (
                  <span key={name} className="text-[11px] px-2 py-0.5 rounded-full bg-white/70 text-slate-600 border border-current/10">
                    {name}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function Stat({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: number }) {
  return (
    <div className="flex items-center gap-1">
      <Icon className="w-3 h-3 text-slate-400" />
      <span className="text-[11px] text-slate-500">
        <span className="text-slate-700" style={{ fontWeight: 700 }}>{value}</span>
        {" "}{label}
      </span>
    </div>
  );
}

/** Shimmer skeleton pill for stat cards while counts are loading */
function StatSkeleton() {
  return (
    <div className="h-7 w-20 rounded bg-slate-200 animate-pulse" />
  );
}

// ── Main page ────────────────────────────────────────────────────────────────
export function BiodiversityPage() {
  const { suppliers, loading: suppLoading } = useSuppliers();

  const [summaries, setSummaries]       = useState<SupplierRiskSummary[]>([]);
  const [dbCounts, setDbCounts]         = useState<BiodiversityCounts | null>(null);
  const [countsLoading, setCountsLoading] = useState(true);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState<string | null>(null);

  // ── Load real DB counts for stat cards ──────────────────────────────────────
  useEffect(() => {
    setCountsLoading(true);
    fetch(`${BASE}/api/biodiversity/counts`)
      .then((r) => r.ok ? r.json() : Promise.reject(r.status))
      .then((data: BiodiversityCounts) => setDbCounts(data))
      .catch(() => setDbCounts(null))  // graceful degradation — show "—" on failure
      .finally(() => setCountsLoading(false));
  }, []);

  // ── Compute risk summaries ───────────────────────────────────────────────────
  const computeRisk = async () => {
    setLoading(true);
    setError(null);

    // Broaden candidate filter: include any supplier that has been enriched,
    // validated, or approved — as long as they have geocoded coordinates.
    const candidates = suppliers.filter(
      (s) =>
        s.coordinates &&
        (
          s.status === "approved" ||
          s.status === "validated" ||
          s.isValidated ||
          s.status === "pending"   // include pending suppliers with coords too
        )
    );

    if (candidates.length === 0) {
      setLoading(false);
      return;
    }

    // Per-supplier error isolation: a failed call returns null, not an exception.
    // Previously Promise.all would reject the entire batch if one supplier failed.
    const results = await Promise.all(
      candidates.map((s) =>
        riskApi
          .summary({
            supplier_id:   s.id,
            supplier_name: s.enrichedName ?? s.name,
            lat:           s.coordinates!.lat,
            lng:           s.coordinates!.lng,
          })
          .catch((err) => {
            console.warn(`[BiodiversityPage] risk-summary failed for ${s.id}:`, err);
            return null;
          })
      )
    );

    const valid = results.filter(Boolean) as SupplierRiskSummary[];
    setSummaries(valid);

    if (valid.length === 0 && candidates.length > 0) {
      setError("Risk summary calls failed for all suppliers. Is the backend running?");
    }

    setLoading(false);
  };

  useEffect(() => {
    if (!suppLoading && suppliers.length > 0) computeRisk();
  }, [suppLoading, suppliers.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── CSV export ───────────────────────────────────────────────────────────────
  const handleExport = () => {
    if (summaries.length === 0) return;
    const header = ["Supplier ID", "Supplier Name", "Latitude", "Longitude",
                    "IBRA Region", "IBRA Code", "Species Nearby",
                    "Protected Areas", "KBAs Nearby", "Risk Level",
                    "Threatened Species (sample)"].join(",");
    const rows = summaries
      .sort((a, b) => {
        const order = { critical: 0, high: 1, medium: 2, low: 3 };
        return order[riskLevel(a)] - order[riskLevel(b)];
      })
      .map((s) => [
        `"${s.supplier_id}"`,
        `"${s.supplier_name.replace(/"/g, '""')}"`,
        s.lat,
        s.lng,
        `"${s.ibra_region ?? ""}"`,
        `"${s.ibra_code ?? ""}"`,
        s.species_nearby,
        s.protected_areas_nearby,
        s.kba_nearby,
        riskLevel(s),
        `"${s.threatened_species_names.join("; ").replace(/"/g, '""')}"`,
      ].join(","));
    const csv = [header, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `eco-biodiversity-risk-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── Risk distribution ────────────────────────────────────────────────────────
  const counts = { critical: 0, high: 0, medium: 0, low: 0 };
  summaries.forEach((s) => counts[riskLevel(s)]++);

  // ── Format a DB count for display (e.g. 9423 → "9,423") ─────────────────────
  const fmtCount = (n: number) => n.toLocaleString("en-AU");

  return (
    <div className="max-w-4xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl text-slate-900" style={{ fontWeight: 700 }}>Biodiversity Risk</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Live spatial analysis — supplier locations cross-referenced with CAPAD, KBA and species data.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {summaries.length > 0 && (
            <button
              onClick={handleExport}
              className="flex items-center gap-2 px-3 py-2 text-xs border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg transition-colors"
              style={{ fontWeight: 500 }}
              title="Export risk profiles as CSV"
            >
              <Download className="w-3.5 h-3.5" />
              Export CSV
            </button>
          )}
          <button
            onClick={computeRisk}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-xs border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg transition-colors disabled:opacity-50"
            style={{ fontWeight: 500 }}
          >
            <RefreshCw className={clsx("w-3.5 h-3.5", loading && "animate-spin")} />
            Refresh
          </button>
        </div>
      </div>

      {/* DB Stats bar — live counts from /api/biodiversity/counts */}
      <div className="grid grid-cols-3 gap-4">
        {[
          {
            label: "Protected Areas (CAPAD)",
            value: countsLoading ? null : dbCounts ? fmtCount(dbCounts.capad_active)  : "—",
            icon: Shield,   color: "text-teal-600",
          },
          {
            label: "Key Biodiversity Areas",
            value: countsLoading ? null : dbCounts ? fmtCount(dbCounts.kba_total)     : "—",
            icon: TreePine, color: "text-green-600",
          },
          {
            label: "Suppliers Assessed",
            value: summaries.length.toString(),
            icon: MapPin,   color: "text-blue-600",
          },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 p-4">
            <Icon className={clsx("w-5 h-5 mb-2", color)} />
            {value === null
              ? <StatSkeleton />
              : <p className="text-xl text-slate-900" style={{ fontWeight: 700 }}>{value}</p>
            }
            <p className="text-xs text-slate-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Risk distribution pills */}
      {summaries.length > 0 && (
        <div className="flex items-center gap-3 flex-wrap">
          {(Object.entries(counts) as [keyof typeof counts, number][]).map(([level, count]) => (
            count > 0 && (
              <span
                key={level}
                className={clsx(
                  "flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full",
                  RISK_COLORS[level].bg, RISK_COLORS[level].text
                )}
                style={{ fontWeight: 600 }}
              >
                <span className={clsx("w-1.5 h-1.5 rounded-full", RISK_COLORS[level].dot)} />
                {count} {level.charAt(0).toUpperCase() + level.slice(1)}
              </span>
            )
          ))}
        </div>
      )}

      {/* Loading state */}
      {(loading || suppLoading) && (
        <div className="flex items-center justify-center gap-3 py-16">
          <Loader2 className="w-5 h-5 text-emerald-600 animate-spin" />
          <p className="text-sm text-slate-500">
            {suppLoading ? "Loading suppliers…" : "Computing spatial risk…"}
          </p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl p-4">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* No suppliers yet */}
      {!loading && !suppLoading && summaries.length === 0 && !error && (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 flex items-center justify-center">
            <Leaf className="w-6 h-6 text-emerald-500" />
          </div>
          <p className="text-sm text-slate-700" style={{ fontWeight: 600 }}>No suppliers with coordinates yet</p>
          <p className="text-xs text-slate-400 max-w-xs">
            Upload and enrich suppliers in Epic 1 first.
            Once suppliers have map coordinates, biodiversity risk will appear here.
          </p>
        </div>
      )}

      {/* Risk cards */}
      {!loading && !suppLoading && summaries.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <p className="text-sm text-slate-700" style={{ fontWeight: 600 }}>Supplier Risk Profiles</p>
            <Info className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-400">Click a card to see nearby species</span>
          </div>
          <div className="space-y-2.5">
            {summaries
              .sort((a, b) => {
                const order = { critical: 0, high: 1, medium: 2, low: 3 };
                return order[riskLevel(a)] - order[riskLevel(b)];
              })
              .map((s) => <RiskCard key={s.supplier_id} summary={s} />)
            }
          </div>
        </div>
      )}

      {/* Data source note */}
      <div className="flex items-start gap-2 bg-slate-50 rounded-xl p-4 text-xs text-slate-500">
        <Info className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
        <p>
          Risk scores use a ~50 km bounding-box proximity query across your local database.
          Data sources: CAPAD 2022 (DCCEEW), Key Biodiversity Areas (BirdLife), ALA species occurrences.
        </p>
      </div>
    </div>
  );
}
