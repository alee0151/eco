/**
 * RiskProfile.tsx — right panel of the Biodiversity split layout.
 *
 * Two modes:
 *
 * 1. RISK MODE (supplier + summary both present)
 *    Live SupplierRiskSummary from /api/biodiversity/risk-summary.
 *    Displays: risk score ring, proximity metrics, threatened species chips,
 *    IBRA region, and assessment notes.
 *
 * 2. APPROVED SUPPLIER MODE (supplier present, summary null)
 *    Shows all session-context data already available for the supplier —
 *    name, ABN, enriched address, commodity, region, confidence score,
 *    ABR status, and discrepancy flags — so the right panel is immediately
 *    useful while geocoding / risk computation is still pending.
 *
 * 3. EMPTY STATE (no supplier selected)
 *    Prompt to select a supplier with feature list.
 */

import { motion, AnimatePresence } from 'motion/react';
import {
  Shield, TreePine, AlertTriangle, Leaf, X, Info,
  MapPin, Bird, ChevronRight, Clock, Building2,
  Package, Hash, CheckCircle2, AlertCircle,
} from 'lucide-react';
import clsx from 'clsx';
import { Supplier } from '../../context/SupplierContext';
import { SupplierRiskSummary } from '../../lib/api';

interface RiskProfileProps {
  supplier: Supplier | null;
  summary:  SupplierRiskSummary | null;
  onClose:  () => void;
}

function riskLevel(s: SupplierRiskSummary): 'critical' | 'high' | 'medium' | 'low' {
  const score = s.species_nearby * 2 + s.protected_areas_nearby * 3 + s.kba_nearby * 5;
  if (score >= 30) return 'critical';
  if (score >= 15) return 'high';
  if (score >= 5)  return 'medium';
  return 'low';
}

function riskScore(s: SupplierRiskSummary): number {
  return Math.min(100, s.species_nearby * 2 + s.protected_areas_nearby * 3 + s.kba_nearby * 5);
}

const RISK_COLORS: Record<string, { light: string; border: string; text: string; dot: string }> = {
  critical: { light: 'bg-red-50',     border: 'border-red-200',    text: 'text-red-700',    dot: '#ef4444' },
  high:     { light: 'bg-orange-50',  border: 'border-orange-200', text: 'text-orange-700', dot: '#f97316' },
  medium:   { light: 'bg-amber-50',   border: 'border-amber-200',  text: 'text-amber-700',  dot: '#f59e0b' },
  low:      { light: 'bg-emerald-50', border: 'border-emerald-200',text: 'text-emerald-700',dot: '#10b981' },
};

const STATUS_STYLES: Record<string, { pill: string; label: string }> = {
  approved:  { pill: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Approved'  },
  validated: { pill: 'bg-blue-50    text-blue-700    border-blue-200',    label: 'Validated' },
  pending:   { pill: 'bg-amber-50   text-amber-700   border-amber-200',   label: 'Pending'   },
  rejected:  { pill: 'bg-red-50     text-red-700     border-red-200',     label: 'Rejected'  },
};

function MetricCard({ icon: Icon, label, value, unit, danger }: {
  icon: React.ElementType; label: string; value: number | string; unit?: string; danger?: boolean;
}) {
  return (
    <div className={clsx('rounded-xl border p-3', danger ? 'bg-red-50/60 border-red-100' : 'bg-slate-50 border-slate-100')}>
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon size={12} className={danger ? 'text-red-500' : 'text-slate-400'} />
        <span className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-xl" style={{ fontWeight: 700, color: danger ? '#ef4444' : '#0f172a' }}>{value}</span>
        {unit && <span className="text-[11px] text-slate-400">{unit}</span>}
      </div>
    </div>
  );
}

/** ── Approved Supplier Detail Panel ──────────────────────────────────── */
function ApprovedSupplierDetail({ supplier, onClose }: { supplier: Supplier; onClose: () => void }) {
  const displayName = supplier.enrichedName ?? supplier.name;
  const displayAddr = supplier.enrichedAddress ?? supplier.address;
  const confidence  = supplier.confidenceScore ?? 0;
  const statusStyle = STATUS_STYLES[supplier.status] ?? STATUS_STYLES.pending;

  const ringColor =
    confidence >= 80 ? '#10b981' :
    confidence >= 50 ? '#f59e0b' : '#ef4444';

  const circumference = 2 * Math.PI * 20; // r=20
  const dashOffset    = circumference * (1 - confidence / 100);

  return (
    <motion.div
      key={supplier.id + '-detail'}
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 16 }}
      transition={{ duration: 0.22 }}
      className="h-full flex flex-col"
    >
      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-slate-100 flex-shrink-0">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] text-slate-400 font-mono">{supplier.id}</span>
              <span
                className={clsx('px-2 py-0.5 rounded-full text-[10px] border capitalize', statusStyle.pill)}
                style={{ fontWeight: 600 }}
              >
                {statusStyle.label}
              </span>
            </div>
            <h2 className="text-[15px] text-slate-900 leading-tight" style={{ fontWeight: 700 }}>
              {displayName}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors ml-2 flex-shrink-0"
          >
            <X size={14} />
          </button>
        </div>

        {/* Geocoding-pending notice */}
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-50 border border-amber-100">
          <Clock size={12} className="text-amber-500 flex-shrink-0" />
          <p className="text-[11px] text-amber-700" style={{ fontWeight: 500 }}>
            Awaiting location data — biodiversity risk will compute once geocoded.
          </p>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">

        {/* Confidence ring */}
        <div className="flex items-center gap-4 p-3 rounded-xl border border-slate-100 bg-slate-50">
          <svg width="52" height="52" viewBox="0 0 52 52" className="flex-shrink-0">
            <circle cx="26" cy="26" r="20" fill="none" stroke="#e2e8f0" strokeWidth="4" />
            <circle
              cx="26" cy="26" r="20"
              fill="none"
              stroke={ringColor}
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              style={{ transformOrigin: '26px 26px', transform: 'rotate(-90deg)', transition: 'stroke-dashoffset 0.6s ease' }}
            />
            <text x="26" y="26" dominantBaseline="middle" textAnchor="middle" fontSize="11" fontWeight="700" fill={ringColor}>
              {confidence}
            </text>
          </svg>
          <div>
            <p className="text-[13px] text-slate-800" style={{ fontWeight: 600 }}>Confidence Score</p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              {confidence >= 80 ? 'High confidence — ABN & address validated'
                : confidence >= 50 ? 'Moderate — some discrepancies flagged'
                : 'Low — manual review recommended'}
            </p>
          </div>
        </div>

        {/* Key fields */}
        <div className="space-y-2">
          {supplier.abn && (
            <div className="flex items-start gap-2">
              <Hash size={13} className="text-slate-300 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-wider">ABN</p>
                <p className="text-[13px] text-slate-800 font-mono" style={{ fontWeight: 500 }}>{supplier.abn}</p>
              </div>
            </div>
          )}

          {displayAddr && (
            <div className="flex items-start gap-2">
              <MapPin size={13} className="text-slate-300 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-wider">Address</p>
                <p className="text-[13px] text-slate-800" style={{ fontWeight: 500 }}>{displayAddr}</p>
                {supplier.addressDiscrepancy && (
                  <span className="inline-flex items-center gap-1 text-[10px] text-orange-600 mt-0.5">
                    <AlertCircle size={10} /> Address discrepancy flagged
                  </span>
                )}
              </div>
            </div>
          )}

          {supplier.commodity && (
            <div className="flex items-start gap-2">
              <Package size={13} className="text-slate-300 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-wider">Commodity</p>
                <p className="text-[13px] text-slate-800" style={{ fontWeight: 500 }}>{supplier.commodity}</p>
              </div>
            </div>
          )}

          {supplier.region && (
            <div className="flex items-start gap-2">
              <Building2 size={13} className="text-slate-300 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-wider">Region</p>
                <p className="text-[13px] text-slate-800" style={{ fontWeight: 500 }}>{supplier.region}</p>
              </div>
            </div>
          )}

          {supplier.abrStatus && (
            <div className="flex items-start gap-2">
              <CheckCircle2 size={13} className="text-slate-300 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-wider">ABR Status</p>
                <p className="text-[13px] text-slate-800" style={{ fontWeight: 500 }}>{supplier.abrStatus}</p>
              </div>
            </div>
          )}
        </div>

        {/* Discrepancy warnings */}
        {(supplier.nameDiscrepancy || supplier.warnings?.length) && (
          <div className="rounded-xl border border-orange-100 bg-orange-50/60 p-3 space-y-1">
            <p className="text-[10px] text-orange-700 uppercase tracking-wider" style={{ fontWeight: 600 }}>Flags</p>
            {supplier.nameDiscrepancy && (
              <p className="text-[12px] text-orange-700 flex items-center gap-1.5">
                <AlertTriangle size={11} /> Name discrepancy between file and ABR
              </p>
            )}
            {supplier.warnings?.map((w, i) => (
              <p key={i} className="text-[12px] text-orange-700 flex items-center gap-1.5">
                <Info size={11} /> {w}
              </p>
            ))}
          </div>
        )}

        {/* What will be shown once geocoded */}
        <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2" style={{ fontWeight: 600 }}>
            Once location resolved
          </p>
          {['Protected Areas (CAPAD)', 'Key Biodiversity Areas', 'Species Occurrences', 'IBRA Bioregion', 'Risk Score'].map(item => (
            <div key={item} className="flex items-center gap-2 py-0.5 text-[11px] text-slate-400">
              <ChevronRight size={11} className="text-slate-300" />
              {item}
            </div>
          ))}
        </div>

      </div>
    </motion.div>
  );
}

/** ── Main export ─────────────────────────────────────────────────────── */
export default function RiskProfile({ supplier, summary, onClose }: RiskProfileProps) {
  // No supplier selected
  if (!supplier) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center">
        <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
          <Leaf size={24} className="text-slate-300" />
        </div>
        <p className="text-sm text-slate-700" style={{ fontWeight: 600 }}>No Supplier Selected</p>
        <p className="text-[13px] text-slate-400 max-w-[200px] mt-1">
          Select a supplier from the list or map to view their biodiversity risk profile.
        </p>
        <div className="mt-6 flex flex-col gap-2 w-full max-w-[200px]">
          {['Protected Areas (CAPAD)', 'Key Biodiversity Areas', 'Species Occurrences', 'IBRA Bioregion'].map(item => (
            <div key={item} className="flex items-center gap-2 text-[11px] text-slate-400">
              <ChevronRight className="w-3 h-3 text-slate-300" />
              {item}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Supplier selected but no summary yet → show approved supplier detail
  if (!summary) {
    return (
      <AnimatePresence mode="wait">
        <ApprovedSupplierDetail key={supplier.id} supplier={supplier} onClose={onClose} />
      </AnimatePresence>
    );
  }

  // Full risk mode
  const level  = riskLevel(summary);
  const score  = riskScore(summary);
  const colors = RISK_COLORS[level];

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={supplier.id}
        initial={{ opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 16 }}
        transition={{ duration: 0.22 }}
        className="h-full flex flex-col"
      >
        {/* Panel header */}
        <div className="px-4 pt-4 pb-3 border-b border-slate-100 flex-shrink-0">
          <div className="flex items-start justify-between mb-2">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] text-slate-400 font-mono">{supplier.id}</span>
                <span className={clsx('px-2 py-0.5 rounded-full text-[10px] capitalize', colors.light, colors.text)} style={{ fontWeight: 600 }}>
                  {level} risk
                </span>
              </div>
              <h2 className="text-[15px] text-slate-900 leading-tight" style={{ fontWeight: 700 }}>
                {supplier.enrichedName ?? supplier.name}
              </h2>
              {summary.ibra_region && (
                <div className="flex items-center gap-1 mt-1">
                  <MapPin size={11} className="text-slate-400" />
                  <span className="text-[12px] text-slate-500">
                    {summary.ibra_region}{summary.ibra_code ? ` (${summary.ibra_code})` : ''}
                  </span>
                </div>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors ml-2 flex-shrink-0"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">

          {/* Risk score ring */}
          <div className={clsx('rounded-xl border p-4 flex items-center gap-4', colors.light, colors.border)}>
            <div className="relative w-16 h-16 flex-shrink-0">
              <svg viewBox="0 0 64 64" className="w-full h-full -rotate-90">
                <circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" strokeWidth="6" className="text-slate-200" />
                <circle
                  cx="32" cy="32" r="26"
                  fill="none"
                  stroke={colors.dot}
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 26}`}
                  strokeDashoffset={`${2 * Math.PI * 26 * (1 - score / 100)}`}
                  style={{ transition: 'stroke-dashoffset 0.8s ease' }}
                />
              </svg>
              <span
                className="absolute inset-0 flex items-center justify-center text-[17px]"
                style={{ fontWeight: 800, color: colors.dot }}
              >
                {score}
              </span>
            </div>
            <div>
              <p className={clsx('text-sm capitalize', colors.text)} style={{ fontWeight: 700 }}>{level} Risk</p>
              <p className="text-[12px] text-slate-500 mt-0.5 max-w-[160px]">
                Based on proximity to protected areas, KBAs and threatened species.
              </p>
            </div>
          </div>

          {/* Proximity metrics */}
          <div className="grid grid-cols-3 gap-2">
            <MetricCard icon={Shield}   label="Protected" value={summary.protected_areas_nearby} unit="PA"  danger={summary.protected_areas_nearby > 2} />
            <MetricCard icon={Bird}     label="Species"   value={summary.species_nearby}          unit="spp" danger={summary.species_nearby > 5} />
            <MetricCard icon={TreePine} label="KBAs"      value={summary.kba_nearby}               unit="KBA" danger={summary.kba_nearby > 0} />
          </div>

          {/* Threatened species chips */}
          {summary.threatened_species_names?.length > 0 && (
            <div>
              <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2" style={{ fontWeight: 600 }}>Threatened Species Nearby</p>
              <div className="flex flex-wrap gap-1.5">
                {summary.threatened_species_names.slice(0, 6).map(sp => (
                  <span key={sp} className="text-[10px] px-2 py-1 rounded-full bg-purple-50 border border-purple-100 text-purple-700" style={{ fontWeight: 500 }}>
                    {sp}
                  </span>
                ))}
                {summary.threatened_species_names.length > 6 && (
                  <span className="text-[10px] px-2 py-1 rounded-full bg-slate-100 text-slate-500" style={{ fontWeight: 500 }}>
                    +{summary.threatened_species_names.length - 6} more
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Assessment notes */}
          {summary.assessment_notes && (
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
              <div className="flex items-center gap-1.5 mb-1.5">
                <Info size={11} className="text-slate-400" />
                <p className="text-[10px] text-slate-500 uppercase tracking-wider" style={{ fontWeight: 600 }}>Assessment Notes</p>
              </div>
              <p className="text-[12px] text-slate-600 leading-relaxed">{summary.assessment_notes}</p>
            </div>
          )}

          {/* Supplier meta footer */}
          <div className="rounded-xl border border-slate-100 p-3 space-y-1.5">
            <p className="text-[10px] text-slate-400 uppercase tracking-wider" style={{ fontWeight: 600 }}>Supplier Info</p>
            {(supplier.enrichedAddress ?? supplier.address) && (
              <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                <MapPin size={11} className="text-slate-300" />
                {supplier.enrichedAddress ?? supplier.address}
              </div>
            )}
            {supplier.commodity && (
              <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                <AlertTriangle size={11} className="text-slate-300" />
                {supplier.commodity}
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
