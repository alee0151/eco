import { useState } from 'react';
import { Search, Filter, MapPin, AlertTriangle, Shield, TreePine, Layers } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import clsx from 'clsx';
import { Epic2Supplier, getRiskColor } from '../../data/epic2-data';

interface SupplierListProps {
  suppliers: Epic2Supplier[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  hoveredId: string | null;
  onHover: (id: string | null) => void;
}

type RiskFilter = 'all' | 'critical' | 'high' | 'medium' | 'low';

export default function SupplierList({ suppliers, selectedId, onSelect, hoveredId, onHover }: SupplierListProps) {
  const [search, setSearch]       = useState('');
  const [filterRisk, setFilterRisk] = useState<RiskFilter>('all');

  const filtered = suppliers
    .filter(s => {
      const matchSearch = s.name.toLowerCase().includes(search.toLowerCase())
        || s.region.toLowerCase().includes(search.toLowerCase());
      const matchRisk = filterRisk === 'all' || s.riskLevel === filterRisk;
      return matchSearch && matchRisk;
    })
    .sort((a, b) => b.riskScore - a.riskScore);

  const counts = {
    all:      suppliers.length,
    critical: suppliers.filter(s => s.riskLevel === 'critical').length,
    high:     suppliers.filter(s => s.riskLevel === 'high').length,
    medium:   suppliers.filter(s => s.riskLevel === 'medium').length,
    low:      suppliers.filter(s => s.riskLevel === 'low').length,
  };

  return (
    <div className="flex flex-col h-full">
      {/* Panel header */}
      <div className="px-4 pt-4 pb-3 border-b border-slate-100 flex-shrink-0 space-y-3">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-emerald-600" />
          <span className="text-sm text-slate-800" style={{ fontWeight: 600 }}>Suppliers</span>
          <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full" style={{ fontWeight: 600 }}>
            {suppliers.length}
          </span>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Search suppliers…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-2 text-sm border border-slate-200 rounded-lg bg-slate-50 focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 outline-none transition-all"
          />
        </div>

        {/* Filter tabs — matches MapPage confidence tabs */}
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
              <span
                className={clsx('text-[9px] px-1 rounded', filterRisk === level ? 'bg-slate-100 text-slate-600' : 'bg-transparent')}
                style={{ fontWeight: 700 }}
              >
                {counts[level]}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Card list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        <AnimatePresence>
          {filtered.map((supplier, i) => {
            const colors = getRiskColor(supplier.riskLevel);
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
                    isSelected
                      ? 'border-emerald-300 shadow-md shadow-emerald-100/60'
                      : isHovered
                      ? 'border-slate-300 shadow-sm'
                      : 'border-slate-200 hover:border-slate-300'
                  )}
                >
                  <div className="px-3 py-2.5 flex items-start gap-2.5">
                    {/* Risk score badge */}
                    <div
                      className={clsx('w-10 h-10 rounded-xl border flex flex-col items-center justify-center flex-shrink-0', colors.light, colors.border, colors.text)}
                    >
                      <span className="text-[13px] leading-none" style={{ fontWeight: 700 }}>{supplier.riskScore}</span>
                      <span className="text-[8px] uppercase tracking-wide" style={{ fontWeight: 600 }}>risk</span>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: colors.dot }} />
                        <p className="text-[13px] text-slate-900 truncate" style={{ fontWeight: 600 }}>{supplier.name}</p>
                      </div>
                      <div className="flex items-center gap-1 mt-0.5 text-[11px] text-slate-400">
                        <MapPin className="w-2.5 h-2.5" />
                        <span className="truncate">{supplier.region}</span>
                      </div>

                      {/* Mini metrics */}
                      <div className="flex items-center gap-3 mt-1.5">
                        <span className="flex items-center gap-1 text-[10px] text-slate-500">
                          <Shield className="w-2.5 h-2.5 text-slate-400" />{supplier.protectedAreaOverlap}%
                        </span>
                        <span className="flex items-center gap-1 text-[10px] text-slate-500">
                          <AlertTriangle className="w-2.5 h-2.5 text-slate-400" />{supplier.threatenedSpeciesCount} spp
                        </span>
                        <span className="flex items-center gap-1 text-[10px] text-slate-500">
                          <TreePine className="w-2.5 h-2.5 text-slate-400" />{supplier.vegetationCondition}%
                        </span>
                      </div>

                      {/* Risk bar */}
                      <div className="mt-2 h-1 bg-slate-100 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full rounded-full"
                          style={{ backgroundColor: colors.dot }}
                          initial={{ width: 0 }}
                          animate={{ width: `${supplier.riskScore}%` }}
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

        {filtered.length === 0 && (
          <div className="text-center py-16">
            <Search className="w-8 h-8 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-slate-400">No suppliers match this filter.</p>
          </div>
        )}
      </div>
    </div>
  );
}
