/**
 * SupplierList.tsx — left panel of the Biodiversity split layout.
 * Driven by live SupplierContext suppliers + SupplierRiskSummary[].
 * Risk level and score are derived from the summary (no mock epic2-data).
 */

import { useState } from 'react';
import { Search, MapPin, AlertTriangle, Shield, TreePine, Layers, Bird } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import clsx from 'clsx';
import { Supplier } from '../../context/SupplierContext';
import { SupplierRiskSummary } from '../../lib/api';

interface SupplierListProps {
  suppliers:  Supplier[];
  summaries:  SupplierRiskSummary[];
  selectedId: string | null;
  onSelect:   (id: string) => void;
  hoveredId:  string | null;
  onHover:    (id: string | null) => void;
}

type RiskFilter = 'all' | 'critical' | 'high' | 'medium' | 'low';

function riskLevel(s: SupplierRiskSummary): RiskFilter {
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

export default function SupplierList({ suppliers, summaries, selectedId, onSelect, hoveredId, onHover }: SupplierListProps) {
  const [search,     setSearch]     = useState('');
  const [filterRisk, setFilterRisk] = useState<RiskFilter>('all');

  // Only show suppliers that have a risk summary (i.e., have been geocoded)
  const withSummary = suppliers
    .map(s => ({ supplier: s, summary: summaries.find(r => r.supplier_id === s.id) }))
    .filter(({ summary }) => summary != null) as { supplier: Supplier; summary: SupplierRiskSummary }[];

  // Also show suppliers that have coordinates but no summary yet
  const withCoords = suppliers.filter(
    s => s.coordinates && !summaries.find(r => r.supplier_id === s.id)
  );

  const counts: Record<RiskFilter, number> = {
    all:      withSummary.length,
    critical: withSummary.filter(({ summary }) => riskLevel(summary) === 'critical').length,
    high:     withSummary.filter(({ summary }) => riskLevel(summary) === 'high').length,
    medium:   withSummary.filter(({ summary }) => riskLevel(summary) === 'medium').length,
    low:      withSummary.filter(({ summary }) => riskLevel(summary) === 'low').length,
  };

  const filtered = withSummary
    .filter(({ supplier, summary }) => {
      const q = search.toLowerCase();
      const matchSearch = supplier.name.toLowerCase().includes(q)
        || (supplier.region ?? '').toLowerCase().includes(q)
        || (summary.ibra_region ?? '').toLowerCase().includes(q);
      const matchRisk = filterRisk === 'all' || riskLevel(summary) === filterRisk;
      return matchSearch && matchRisk;
    })
    .sort((a, b) => riskScore(b.summary) - riskScore(a.summary));

  return (
    <div className="flex flex-col h-full">
      {/* Panel header */}
      <div className="px-4 pt-4 pb-3 border-b border-slate-100 flex-shrink-0 space-y-3">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-emerald-600" />
          <span className="text-sm text-slate-800" style={{ fontWeight: 600 }}>Suppliers</span>
          <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full" style={{ fontWeight: 600 }}>
            {withSummary.length}
          </span>
          {withCoords.length > 0 && (
            <span className="text-xs text-amber-500 bg-amber-50 px-2 py-0.5 rounded-full" style={{ fontWeight: 600 }}>
              +{withCoords.length} pending
            </span>
          )}
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Search suppliers, region, IBRA…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-2 text-sm border border-slate-200 rounded-lg bg-slate-50 focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 outline-none transition-all"
          />
        </div>

        {/* Filter tabs */}
        <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-0.5">
          {(['all', 'critical', 'high', 'medium', 'low'] as RiskFilter[]).map(level => (
            <button
              key={level}
              onClick={() => setFilterRisk(level)}
              className={clsx(
                'flex-1 flex items-center justify-center gap-0.5 px-1 py-1.5 rounded-md text-[10px] transition-all capitalize',
                filterRisk === level ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              )}
              style={{ fontWeight: filterRisk === level ? 600 : 500 }}
            >
              {level === 'all' ? 'All' : level.slice(0, 3)}
              <span className={clsx('text-[9px] px-1 rounded', filterRisk === level ? 'bg-slate-100 text-slate-600' : 'bg-transparent')} style={{ fontWeight: 700 }}>
                {counts[level]}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Card list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        <AnimatePresence>
          {filtered.map(({ supplier, summary }, i) => {
            const level  = riskLevel(summary);
            const score  = riskScore(summary);
            const colors = RISK_COLORS[level];
            const isSelected = selectedId === supplier.id;
            const isHovered  = hoveredId  === supplier.id;

            return (
              <motion.div
                key={supplier.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
              >
                <div
                  onClick={() => onSelect(supplier.id)}
                  onMouseEnter={() => onHover(supplier.id)}
                  onMouseLeave={() => onHover(null)}
                  className={clsx(
                    'rounded-xl border overflow-hidden transition-all duration-200 cursor-pointer bg-white',
                    isSelected ? 'border-emerald-300 shadow-md shadow-emerald-100/60'
                    : isHovered ? 'border-slate-300 shadow-sm'
                    : 'border-slate-200 hover:border-slate-300'
                  )}
                >
                  <div className="px-3 py-2.5 flex items-start gap-2.5">
                    {/* Risk score badge */}
                    <div className={clsx('w-10 h-10 rounded-xl border flex flex-col items-center justify-center flex-shrink-0', colors.light, colors.border, colors.text)}>
                      <span className="text-[13px] leading-none" style={{ fontWeight: 700 }}>{score}</span>
                      <span className="text-[8px] uppercase tracking-wide" style={{ fontWeight: 600 }}>risk</span>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: colors.dot }} />
                        <p className="text-[13px] text-slate-900 truncate" style={{ fontWeight: 600 }}>{supplier.enrichedName ?? supplier.name}</p>
                      </div>
                      <div className="flex items-center gap-1 mt-0.5 text-[11px] text-slate-400">
                        <MapPin className="w-2.5 h-2.5" />
                        <span className="truncate">{summary.ibra_region ?? supplier.region ?? '—'}</span>
                      </div>

                      {/* Mini metrics */}
                      <div className="flex items-center gap-3 mt-1.5">
                        <span className="flex items-center gap-1 text-[10px] text-slate-500">
                          <Shield className="w-2.5 h-2.5 text-slate-400" />{summary.protected_areas_nearby} PA
                        </span>
                        <span className="flex items-center gap-1 text-[10px] text-slate-500">
                          <Bird className="w-2.5 h-2.5 text-slate-400" />{summary.species_nearby} spp
                        </span>
                        <span className="flex items-center gap-1 text-[10px] text-slate-500">
                          <TreePine className="w-2.5 h-2.5 text-slate-400" />{summary.kba_nearby} KBA
                        </span>
                      </div>

                      {/* Risk bar */}
                      <div className="mt-2 h-1 bg-slate-100 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full rounded-full"
                          style={{ backgroundColor: colors.dot }}
                          initial={{ width: 0 }}
                          animate={{ width: `${score}%` }}
                          transition={{ duration: 0.6, ease: 'easeOut' }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {filtered.length === 0 && withSummary.length > 0 && (
          <div className="text-center py-16">
            <Search className="w-8 h-8 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-slate-400">No suppliers match this filter.</p>
          </div>
        )}

        {withSummary.length === 0 && (
          <div className="text-center py-12 px-4">
            <AlertTriangle className="w-8 h-8 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-slate-500" style={{ fontWeight: 600 }}>No risk data yet</p>
            <p className="text-xs text-slate-400 mt-1">Suppliers need geocoded coordinates to compute biodiversity risk.</p>
          </div>
        )}
      </div>
    </div>
  );
}
