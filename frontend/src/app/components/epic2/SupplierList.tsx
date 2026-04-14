import { useState } from 'react';
import { Search, Filter, MapPin, AlertTriangle, Shield, TreePine } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Epic2Supplier, getRiskColor } from '../../data/epic2-data';

interface SupplierListProps {
  suppliers: Epic2Supplier[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  hoveredId: string | null;
  onHover: (id: string | null) => void;
}

export default function SupplierList({ suppliers, selectedId, onSelect, hoveredId, onHover }: SupplierListProps) {
  const [search, setSearch] = useState('');
  const [filterRisk, setFilterRisk] = useState<string>('all');
  const [showFilter, setShowFilter] = useState(false);

  const filtered = suppliers.filter(s => {
    const matchSearch = s.name.toLowerCase().includes(search.toLowerCase()) || s.region.toLowerCase().includes(search.toLowerCase());
    const matchRisk = filterRisk === 'all' || s.riskLevel === filterRisk;
    return matchSearch && matchRisk;
  });

  const sortedSuppliers = [...filtered].sort((a, b) => b.riskScore - a.riskScore);

  const riskCounts = {
    all:      suppliers.length,
    critical: suppliers.filter(s => s.riskLevel === 'critical').length,
    high:     suppliers.filter(s => s.riskLevel === 'high').length,
    medium:   suppliers.filter(s => s.riskLevel === 'medium').length,
    low:      suppliers.filter(s => s.riskLevel === 'low').length,
  };

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 bg-white">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Suppliers</h2>
            <p className="text-[13px] text-slate-500 mt-0.5">{suppliers.length} locations monitored</p>
          </div>
          <button
            onClick={() => setShowFilter(!showFilter)}
            className={`p-2 rounded-lg transition-colors ${
              showFilter ? 'bg-emerald-100 text-emerald-700' : 'text-slate-500 hover:bg-slate-100'
            }`}
          >
            <Filter size={16} />
          </button>
        </div>

        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search suppliers or regions..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-[13px] text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400/30 transition-all"
          />
        </div>

        <AnimatePresence>
          {showFilter && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="flex flex-wrap gap-1.5 mt-3">
                {(['all', 'critical', 'high', 'medium', 'low'] as const).map(level => {
                  const colors = getRiskColor(level);
                  const isActive = filterRisk === level;
                  return (
                    <button
                      key={level}
                      onClick={() => setFilterRisk(level)}
                      className={`px-2.5 py-1 rounded-full text-[11px] transition-all capitalize flex items-center gap-1.5 ${
                        isActive
                          ? level === 'all'
                            ? 'bg-emerald-600 text-white'
                            : `${colors.light} ${colors.text} ring-1 ring-current/20`
                          : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                      }`}
                    >
                      {level === 'all' ? 'All' : level}
                      <span className={`text-[10px] ${isActive ? 'opacity-80' : 'opacity-60'}`}>
                        {riskCounts[level]}
                      </span>
                    </button>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Supplier Cards */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {sortedSuppliers.map(supplier => {
          const colors = getRiskColor(supplier.riskLevel);
          const isSelected = selectedId === supplier.id;
          const isHovered = hoveredId === supplier.id;

          return (
            <motion.button
              key={supplier.id}
              onClick={() => onSelect(supplier.id)}
              onMouseEnter={() => onHover(supplier.id)}
              onMouseLeave={() => onHover(null)}
              className={`w-full text-left p-3 rounded-xl transition-all cursor-pointer ${
                isSelected
                  ? 'bg-white shadow-md ring-1 ring-emerald-300/50'
                  : isHovered
                  ? 'bg-white shadow-sm'
                  : 'bg-white/60 hover:bg-white hover:shadow-sm'
              }`}
              layout
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: colors.dot }} />
                    <h4 className="text-[13px] text-slate-900 truncate font-medium">{supplier.name}</h4>
                  </div>
                  <div className="flex items-center gap-1 ml-4 text-[11px] text-slate-500">
                    <MapPin size={10} />
                    {supplier.region}
                  </div>
                </div>
                <div className={`shrink-0 px-2 py-0.5 rounded-md text-[11px] capitalize ${colors.light} ${colors.text}`}>
                  {supplier.riskScore}
                </div>
              </div>

              <div className="flex items-center gap-3 mt-2.5 ml-4">
                <div className="flex items-center gap-1 text-[10px] text-slate-500">
                  <Shield size={10} className="text-slate-400" />
                  {supplier.protectedAreaOverlap}% overlap
                </div>
                <div className="flex items-center gap-1 text-[10px] text-slate-500">
                  <AlertTriangle size={10} className="text-slate-400" />
                  {supplier.threatenedSpeciesCount} species
                </div>
                <div className="flex items-center gap-1 text-[10px] text-slate-500">
                  <TreePine size={10} className="text-slate-400" />
                  {supplier.vegetationCondition}%
                </div>
              </div>

              <div className="mt-2.5 ml-4 h-1 bg-slate-100 rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: colors.dot }}
                  initial={{ width: 0 }}
                  animate={{ width: `${supplier.riskScore}%` }}
                  transition={{ duration: 0.6, ease: 'easeOut' }}
                />
              </div>
            </motion.button>
          );
        })}

        {sortedSuppliers.length === 0 && (
          <div className="text-center py-10 text-slate-400 text-[13px]">
            No suppliers match your search.
          </div>
        )}
      </div>
    </div>
  );
}
