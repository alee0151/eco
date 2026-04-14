import { motion, AnimatePresence } from 'motion/react';
import {
  Shield, TreePine, Droplets, AlertTriangle, Leaf, Calendar,
  Building2, FileText, TrendingDown, X, Info
} from 'lucide-react';
import clsx from 'clsx';
import { Epic2Supplier, getRiskColor, getStatusLabel, getSpeciesIcon } from '../../data/epic2-data';

interface RiskProfileProps {
  supplier: Epic2Supplier | null;
  onClose: () => void;
}

/* ── Metric card — matches MapPage ScoreBadge aesthetic ── */
function MetricCard({ icon: Icon, label, value, unit, dot, danger }: {
  icon: React.ElementType;
  label: string;
  value: number | string;
  unit?: string;
  dot: string;
  danger?: boolean;
}) {
  return (
    <div className={clsx(
      'rounded-xl border p-3',
      danger ? 'bg-red-50/60 border-red-100' : 'bg-slate-50 border-slate-100'
    )}>
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon size={12} className={danger ? 'text-red-500' : 'text-slate-400'} />
        <span className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-xl" style={{ fontWeight: 700, color: dot }}>{value}</span>
        {unit && <span className="text-[11px] text-slate-400">{unit}</span>}
      </div>
    </div>
  );
}

/* ── Condition bar — matches MapPage confidence bar ── */
function ConditionBar({ value, label }: { value: number; label: string }) {
  const color = value >= 70 ? '#10b981' : value >= 40 ? '#f59e0b' : '#ef4444';
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-[11px] text-slate-500">{label}</span>
        <span className="text-[11px] text-slate-700" style={{ fontWeight: 600 }}>{value}%</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

export default function RiskProfile({ supplier, onClose }: RiskProfileProps) {
  /* Empty state — matches MapPage "no supplier" pattern */
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
      </div>
    );
  }

  const colors = getRiskColor(supplier.riskLevel);

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
                <span className={clsx(
                  'px-2 py-0.5 rounded-full text-[10px] capitalize',
                  colors.light, colors.text
                )} style={{ fontWeight: 600 }}>
                  {supplier.riskLevel} risk
                </span>
              </div>
              <h2 className="text-sm text-slate-900" style={{ fontWeight: 700 }}>{supplier.name}</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 transition-colors"
            >
              <X size={14} />
            </button>
          </div>

          <div className="flex items-center gap-3 text-[11px] text-slate-500">
            <span className="flex items-center gap-1"><Building2 size={11} />{supplier.industry}</span>
            <span className="flex items-center gap-1"><Calendar size={11} />{supplier.lastAssessment}</span>
          </div>

          {/* Risk score ring + condition bars */}
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
                  animate={{ strokeDasharray: `${supplier.riskScore} ${100 - supplier.riskScore}` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-[16px]" style={{ fontWeight: 700, color: colors.dot }}>
                  {supplier.riskScore}
                </span>
              </div>
            </div>
            <div className="flex-1 space-y-2">
              <ConditionBar value={supplier.vegetationCondition} label="Vegetation Health" />
              <ConditionBar value={100 - supplier.waterStressIndex} label="Water Security" />
            </div>
          </div>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">

          {/* Metrics grid */}
          <div className="grid grid-cols-2 gap-2">
            <MetricCard
              icon={Shield} label="Protected" value={supplier.protectedAreaOverlap} unit="%"
              dot={supplier.protectedAreaOverlap > 30 ? '#ef4444' : '#10b981'}
              danger={supplier.protectedAreaOverlap > 30}
            />
            <MetricCard
              icon={AlertTriangle} label="Threatened" value={supplier.threatenedSpeciesCount} unit="spp"
              dot={supplier.threatenedSpeciesCount > 20 ? '#ef4444' : '#f59e0b'}
              danger={supplier.threatenedSpeciesCount > 20}
            />
            <MetricCard
              icon={TrendingDown} label="Deforestation" value={supplier.deforestationRate} unit="%/yr"
              dot={supplier.deforestationRate > 1.5 ? '#ef4444' : '#f59e0b'}
              danger={supplier.deforestationRate > 1.5}
            />
            <MetricCard
              icon={Leaf} label="Carbon Stock" value={supplier.carbonStock} unit="t/ha"
              dot="#10b981"
            />
          </div>

          {/* Water stress bar */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <div className="flex items-center gap-1.5 mb-2">
              <Droplets size={12} className="text-slate-400" />
              <span className="text-[11px] text-slate-500 uppercase tracking-wider">Water Stress Index</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: 'linear-gradient(90deg,#10b981,#f59e0b,#ef4444)' }}
                  initial={{ width: 0 }}
                  animate={{ width: `${supplier.waterStressIndex}%` }}
                  transition={{ duration: 0.8 }}
                />
              </div>
              <span className="text-xs text-slate-700 min-w-[36px] text-right" style={{ fontWeight: 700 }}>
                {supplier.waterStressIndex}/100
              </span>
            </div>
            <div className="flex justify-between mt-1 text-[9px] text-slate-400">
              <span>Low</span><span>Extreme</span>
            </div>
          </div>

          {/* Threatened species */}
          <div>
            <h4 className="text-[11px] text-slate-500 uppercase tracking-wider mb-2">
              Key Threatened Species
            </h4>
            <div className="space-y-1.5">
              {supplier.threatenedSpecies.map((species, i) => {
                const statusCls: Record<string, string> = {
                  critically_endangered: 'bg-red-50 text-red-700 border-red-100',
                  endangered:           'bg-amber-50 text-amber-700 border-amber-100',
                  vulnerable:           'bg-yellow-50 text-yellow-700 border-yellow-200',
                };
                return (
                  <motion.div
                    key={species.name}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center gap-2.5 p-2 bg-white rounded-lg border border-slate-100"
                  >
                    <span className="text-[15px]">{getSpeciesIcon(species.type)}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] text-slate-800 truncate" style={{ fontWeight: 500 }}>{species.name}</p>
                      <p className="text-[10px] text-slate-400 capitalize">{species.type}</p>
                    </div>
                    <span className={clsx('px-1.5 py-0.5 rounded text-[9px] border shrink-0', statusCls[species.status] || '')}>
                      {getStatusLabel(species.status)}
                    </span>
                  </motion.div>
                );
              })}
            </div>
          </div>

          {/* Assessment notes */}
          {supplier.notes && (
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <div className="flex items-center gap-1.5 mb-1.5">
                <FileText size={11} className="text-slate-400" />
                <span className="text-[11px] text-slate-500 uppercase tracking-wider">Assessment Notes</span>
              </div>
              <p className="text-[12px] text-slate-600 leading-relaxed">{supplier.notes}</p>
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
