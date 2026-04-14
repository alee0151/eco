import { useState } from 'react';
import { Leaf, Layers, BarChart3, Download } from 'lucide-react';
import SupplierList from './SupplierList';
import MapView from './MapView';
import RiskProfile from './RiskProfile';
import { suppliers } from '../../data/epic2-data';

export default function BiodiversityDashboard() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const selectedSupplier = suppliers.find(s => s.id === selectedId) || null;

  const avgRisk = Math.round(suppliers.reduce((sum, s) => sum + s.riskScore, 0) / suppliers.length);
  const criticalCount = suppliers.filter(s => s.riskLevel === 'critical' || s.riskLevel === 'high').length;

  return (
    <div className="h-full flex flex-col bg-slate-50">
      {/* Top bar */}
      <header className="h-12 bg-emerald-700 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-emerald-500/30 flex items-center justify-center">
              <Leaf size={15} className="text-emerald-100" />
            </div>
            <div>
              <h1 className="text-[14px] text-white tracking-tight leading-none font-semibold">
                BioRisk Monitor
              </h1>
              <p className="text-[9px] text-emerald-300 tracking-wider uppercase">
                Biodiversity Risk Assessment Platform
              </p>
            </div>
          </div>

          <div className="h-5 w-px bg-emerald-500/30 mx-2" />

          <div className="flex items-center gap-4 text-[11px]">
            <div className="text-emerald-200">
              <span className="text-white font-semibold text-[14px]">{suppliers.length}</span>{' '}
              <span className="text-emerald-300">Suppliers</span>
            </div>
            <div className="text-emerald-200">
              <span className="text-white font-semibold text-[14px]">{avgRisk}</span>{' '}
              <span className="text-emerald-300">Avg Risk</span>
            </div>
            <div className="text-emerald-200">
              <span className="text-amber-200 font-semibold text-[14px]">{criticalCount}</span>{' '}
              <span className="text-emerald-300">High/Critical</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] text-emerald-200 hover:bg-emerald-500/20 transition-colors">
            <Layers size={13} />
            Layers
          </button>
          <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] text-emerald-200 hover:bg-emerald-500/20 transition-colors">
            <BarChart3 size={13} />
            Reports
          </button>
          <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] text-emerald-200 hover:bg-emerald-500/20 transition-colors">
            <Download size={13} />
            Export
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex min-h-0">
        {/* Left panel - Supplier list */}
        <div className="w-[300px] shrink-0 border-r border-slate-200 overflow-hidden">
          <SupplierList
            suppliers={suppliers}
            selectedId={selectedId}
            onSelect={setSelectedId}
            hoveredId={hoveredId}
            onHover={setHoveredId}
          />
        </div>

        {/* Center - Map */}
        <div className="flex-1 min-w-0 relative">
          <MapView
            suppliers={suppliers}
            selectedId={selectedId}
            onSelect={setSelectedId}
            hoveredId={hoveredId}
            onHover={setHoveredId}
          />
        </div>

        {/* Right panel - Risk profile */}
        <div className="w-[340px] shrink-0 border-l border-slate-200 overflow-hidden">
          <RiskProfile
            supplier={selectedSupplier}
            onClose={() => setSelectedId(null)}
          />
        </div>
      </div>
    </div>
  );
}
