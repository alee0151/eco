import { motion, AnimatePresence } from 'motion/react';
import {
  Shield, TreePine, Droplets, AlertTriangle, Leaf, Calendar,
  Building2, FileText, TrendingDown, Gauge, X, ChevronRight
} from 'lucide-react';
import { Supplier, getRiskColor, getStatusLabel, getSpeciesIcon } from './data';

interface RiskProfileProps {
  supplier: Supplier | null;
  onClose: () => void;
}

function MetricCard({ icon: Icon, label, value, unit, color, danger }: {
  icon: any; label: string; value: number | string; unit?: string; color: string; danger?: boolean;
}) {
  return (
    <div className={`rounded-xl p-3 border ${danger ? 'bg-rust-50/50 border-rust-100' : 'bg-white border-earth-100'}`}>
      <div className="flex items-center gap-2 mb-2">
        <div className={`p-1.5 rounded-lg ${danger ? 'bg-rust-100' : 'bg-earth-50'}`}>
          <Icon size={13} className={danger ? 'text-rust-600' : 'text-earth-500'} />
        </div>
        <span className="text-[11px] text-earth-500 uppercase tracking-wider">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-[22px] text-earth-900 font-[family-name:var(--font-family-serif)]" style={{ color }}>
          {value}
        </span>
        {unit && <span className="text-[11px] text-earth-400">{unit}</span>}
      </div>
    </div>
  );
}

function ConditionBar({ value, label }: { value: number; label: string }) {
  const getColor = (v: number) => {
    if (v >= 70) return '#67a383';
    if (v >= 40) return '#c99a00';
    return '#dc2626';
  };
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-[11px] text-earth-600">{label}</span>
        <span className="text-[11px] text-earth-800">{value}%</span>
      </div>
      <div className="h-1.5 bg-earth-100 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: getColor(value) }}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

export default function RiskProfile({ supplier, onClose }: RiskProfileProps) {
  if (!supplier) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-earth-50 p-6 text-center">
        <div className="w-16 h-16 rounded-2xl bg-earth-100 flex items-center justify-center mb-4">
          <Leaf size={28} className="text-earth-300" />
        </div>
        <h3 className="text-earth-700 mb-1">No Supplier Selected</h3>
        <p className="text-[13px] text-earth-400 max-w-[220px]">
          Click a supplier from the list or map to view their biodiversity risk profile.
        </p>
      </div>
    );
  }

  const colors = getRiskColor(supplier.riskLevel);

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={supplier.id}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        transition={{ duration: 0.3 }}
        className="h-full flex flex-col bg-earth-50"
      >
        {/* Header */}
        <div className="p-4 bg-white border-b border-earth-200">
          <div className="flex items-start justify-between mb-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[11px] text-earth-400 font-mono">{supplier.id}</span>
                <span className={`px-2 py-0.5 rounded-full text-[10px] capitalize ${colors.light} ${colors.text}`}>
                  {supplier.riskLevel} risk
                </span>
              </div>
              <h2 className="text-forest-800 tracking-tight">{supplier.name}</h2>
            </div>
            <button onClick={onClose} className="p-1.5 rounded-lg text-earth-400 hover:bg-earth-100 transition-colors">
              <X size={16} />
            </button>
          </div>

          <div className="flex items-center gap-4 text-[12px] text-earth-500">
            <span className="flex items-center gap-1"><Building2 size={12} />{supplier.industry}</span>
            <span className="flex items-center gap-1"><Calendar size={12} />{supplier.lastAssessment}</span>
          </div>

          {/* Big risk score */}
          <div className="mt-4 flex items-center gap-4">
            <div className="relative w-16 h-16">
              <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#e8ded0"
                  strokeWidth="3"
                />
                <motion.path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke={colors.dot}
                  strokeWidth="3"
                  strokeLinecap="round"
                  initial={{ strokeDasharray: '0 100' }}
                  animate={{ strokeDasharray: `${supplier.riskScore} ${100 - supplier.riskScore}` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-[18px] font-[family-name:var(--font-family-serif)]" style={{ color: colors.dot }}>
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

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Metrics grid */}
          <div className="grid grid-cols-2 gap-2">
            <MetricCard
              icon={Shield}
              label="Protected Overlap"
              value={supplier.protectedAreaOverlap}
              unit="%"
              color={supplier.protectedAreaOverlap > 30 ? '#dc2626' : '#67a383'}
              danger={supplier.protectedAreaOverlap > 30}
            />
            <MetricCard
              icon={AlertTriangle}
              label="Threatened Spp."
              value={supplier.threatenedSpeciesCount}
              unit="species"
              color={supplier.threatenedSpeciesCount > 20 ? '#dc2626' : '#d97706'}
              danger={supplier.threatenedSpeciesCount > 20}
            />
            <MetricCard
              icon={TrendingDown}
              label="Deforestation"
              value={supplier.deforestationRate}
              unit="% /yr"
              color={supplier.deforestationRate > 1.5 ? '#dc2626' : '#c99a00'}
              danger={supplier.deforestationRate > 1.5}
            />
            <MetricCard
              icon={Leaf}
              label="Carbon Stock"
              value={supplier.carbonStock}
              unit="t/ha"
              color="#67a383"
            />
          </div>

          {/* Threatened Species */}
          <div>
            <h4 className="text-[12px] text-earth-500 uppercase tracking-wider mb-2 font-[family-name:var(--font-family-sans)]">
              Key Threatened Species
            </h4>
            <div className="space-y-1.5">
              {supplier.threatenedSpecies.map((species, i) => {
                const statusColors: Record<string, string> = {
                  critically_endangered: 'bg-rust-50 text-rust-700 border-rust-100',
                  endangered: 'bg-amber-50 text-amber-700 border-amber-100',
                  vulnerable: 'bg-[#fdf6e3] text-[#a67c00] border-[#f0d78c]',
                };
                return (
                  <motion.div
                    key={species.name}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center gap-2.5 p-2 bg-white rounded-lg border border-earth-100"
                  >
                    <span className="text-[16px]">{getSpeciesIcon(species.type)}</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-[12px] text-earth-800 truncate">{species.name}</div>
                      <div className="text-[10px] text-earth-400 capitalize">{species.type}</div>
                    </div>
                    <span className={`px-1.5 py-0.5 rounded text-[9px] border ${statusColors[species.status] || ''}`}>
                      {getStatusLabel(species.status)}
                    </span>
                  </motion.div>
                );
              })}
            </div>
          </div>

          {/* Notes */}
          {supplier.notes && (
            <div className="p-3 bg-white rounded-xl border border-earth-100">
              <div className="flex items-center gap-1.5 mb-1.5">
                <FileText size={12} className="text-earth-400" />
                <span className="text-[11px] text-earth-500 uppercase tracking-wider">Assessment Notes</span>
              </div>
              <p className="text-[12px] text-earth-700 leading-relaxed">{supplier.notes}</p>
            </div>
          )}

          {/* Water Stress Detail */}
          <div className="p-3 bg-white rounded-xl border border-earth-100">
            <div className="flex items-center gap-1.5 mb-2">
              <Droplets size={12} className="text-earth-400" />
              <span className="text-[11px] text-earth-500 uppercase tracking-wider">Water Stress Index</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-2 bg-earth-100 rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{
                    backgroundColor: supplier.waterStressIndex > 70 ? '#dc2626' : supplier.waterStressIndex > 40 ? '#d97706' : '#67a383',
                    background: `linear-gradient(90deg, #67a383, #d97706, #dc2626)`,
                  }}
                  initial={{ width: 0 }}
                  animate={{ width: `${supplier.waterStressIndex}%` }}
                  transition={{ duration: 0.8 }}
                />
              </div>
              <span className="text-[13px] text-earth-800 font-[family-name:var(--font-family-serif)] min-w-[36px] text-right">
                {supplier.waterStressIndex}/100
              </span>
            </div>
            <div className="flex justify-between mt-1 text-[9px] text-earth-400">
              <span>Low Stress</span>
              <span>Extreme</span>
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
