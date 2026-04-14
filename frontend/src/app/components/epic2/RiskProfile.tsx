/**
 * RiskProfile.tsx — right panel of the Biodiversity split layout.
 *
 * Driven by live SupplierRiskSummary from /api/biodiversity/risk-summary.
 * Displays: risk score ring, proximity metrics, threatened species chips,
 * IBRA region, and assessment notes.
 */

import { motion, AnimatePresence } from 'motion/react';
import {
  Shield, TreePine, AlertTriangle, Leaf, X, Info,
  MapPin, Bird, ChevronRight,
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

export default function RiskProfile({ supplier, summary, onClose }: RiskProfileProps) {
  if (!supplier || !summary) {
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
          {["Protected Areas (CAPAD)","Key Biodiversity Areas","Species Occurrences","IBRA Bioregion"].map(item => (
            <div key={item} className="flex items-center gap-2 text-[11px] text-slate-400">
              <ChevronRight className="w-3 h-3 text-slate-300" />
              {item}
            </div>
          ))}
        </div>
      </div>
    );
  }

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
              <h2 className="text-sm text-slate-900" style={{ fontWeight: 700 }}>
                {supplier.enrichedName ?? supplier.name}
              </h2>
            </div>
            <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 transition-colors">
              <X size={14} />
            </button>
          </div>

          <div className="flex items-center gap-3 text-[11px] text-slate-500">
            {supplier.region && (
              <span className="flex items-center gap-1"><MapPin size={11} />{supplier.region}</span>
            )}
            {summary.ibra_region && (
              <span className="flex items-center gap-1 text-emerald-600">
                <Leaf size={11} />{summary.ibra_region}
                {summary.ibra_code && <span className="text-slate-400">({summary.ibra_code})</span>}
              </span>
            )}
          </div>

          {/* Risk score ring */}
          <div className="mt-3 flex items-center gap-4">
            <div className="relative w-14 h-14 shrink-0">
              <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none" stroke="#e2e8f0" strokeWidth="3"
                />
                <motion.path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none" stroke={colors.dot} strokeWidth="3" strokeLinecap="round"
                  initial={{ strokeDasharray: '0 100' }}
                  animate={{ strokeDasharray: `${score} ${100 - score}` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-[16px]" style={{ fontWeight: 700, color: colors.dot }}>{score}</span>
              </div>
            </div>
            <div className="flex-1 space-y-2">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-[11px] text-slate-500">Species exposure</span>
                  <span className="text-[11px] text-slate-700" style={{ fontWeight: 600 }}>{summary.species_nearby}</span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-purple-500"
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, summary.species_nearby)}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-[11px] text-slate-500">Protected area proximity</span>
                  <span className="text-[11px] text-slate-700" style={{ fontWeight: 600 }}>{summary.protected_areas_nearby}</span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-teal-500"
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, summary.protected_areas_nearby * 5)}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">

          {/* Metrics grid */}
          <div className="grid grid-cols-2 gap-2">
            <MetricCard icon={Shield}        label="Protected Areas" value={summary.protected_areas_nearby} unit="nearby" danger={summary.protected_areas_nearby > 5} />
            <MetricCard icon={AlertTriangle} label="Species Nearby"  value={summary.species_nearby}         unit="records" danger={summary.species_nearby > 10} />
            <MetricCard icon={TreePine}      label="KBAs Nearby"     value={summary.kba_nearby}             unit="KBAs"   danger={summary.kba_nearby > 2} />
            <MetricCard icon={Bird}          label="Threatened Spp"  value={summary.threatened_species_names.length} unit="named" />
          </div>

          {/* Coordinates */}
          {(summary.lat || summary.lng) && (
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <div className="flex items-center gap-1.5 mb-1">
                <MapPin size={11} className="text-slate-400" />
                <span className="text-[11px] text-slate-500 uppercase tracking-wider">Location</span>
              </div>
              <p className="text-[12px] text-slate-700 font-mono">
                {summary.lat.toFixed(4)}, {summary.lng.toFixed(4)}
              </p>
              {supplier.address && (
                <p className="text-[11px] text-slate-400 mt-1">{supplier.enrichedAddress ?? supplier.address}</p>
              )}
            </div>
          )}

          {/* Threatened species list */}
          {summary.threatened_species_names.length > 0 && (
            <div>
              <h4 className="text-[11px] text-slate-500 uppercase tracking-wider mb-2">Threatened Species Nearby</h4>
              <div className="flex flex-wrap gap-1.5">
                {summary.threatened_species_names.map((name, i) => (
                  <motion.span
                    key={name}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.04 }}
                    className="text-[11px] px-2 py-1 rounded-lg bg-purple-50 text-purple-700 border border-purple-100"
                    style={{ fontWeight: 500 }}
                  >
                    {name}
                  </motion.span>
                ))}
              </div>
            </div>
          )}

          {/* Supplier details */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-2">
            <div className="flex items-center gap-1.5">
              <Info size={11} className="text-slate-400" />
              <span className="text-[11px] text-slate-500 uppercase tracking-wider">Supplier Details</span>
            </div>
            {supplier.abn && (
              <p className="text-[12px] text-slate-600">ABN: <span style={{ fontWeight: 600 }}>{supplier.abn}</span></p>
            )}
            {supplier.commodity && (
              <p className="text-[12px] text-slate-600">Commodity: <span style={{ fontWeight: 600 }}>{supplier.commodity}</span></p>
            )}
            {supplier.status && (
              <p className="text-[12px] text-slate-600">Status: <span className="capitalize" style={{ fontWeight: 600 }}>{supplier.status}</span></p>
            )}
            {supplier.confidenceScore !== undefined && supplier.confidenceScore !== null && (
              <p className="text-[12px] text-slate-600">Confidence: <span style={{ fontWeight: 600 }}>{Math.round(supplier.confidenceScore * 100)}%</span></p>
            )}
          </div>

          {/* Data note */}
          <div className="flex items-start gap-2 text-[10px] text-slate-400">
            <Info size={10} className="shrink-0 mt-0.5" />
            <p>Risk computed via ~50 km bounding-box query. Sources: CAPAD 2022, BirdLife KBAs, ALA species occurrences.</p>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
