import { useState } from 'react';
import { Download, List, Map as MapIcon } from 'lucide-react';
import clsx from 'clsx';
import { motion } from 'motion/react';
import SupplierList from './SupplierList';
import MapView from './MapView';
import RiskProfile from './RiskProfile';
import { suppliers } from '../../data/epic2-data';

export default function BiodiversityDashboard() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState<'map' | 'list'>('list');

  const selectedSupplier = suppliers.find(s => s.id === selectedId) || null;

  const avgRisk     = Math.round(suppliers.reduce((sum, s) => sum + s.riskScore, 0) / suppliers.length);
  const criticalCount = suppliers.filter(s => s.riskLevel === 'critical').length;
  const highCount     = suppliers.filter(s => s.riskLevel === 'high').length;
  const lowCount      = suppliers.filter(s => s.riskLevel === 'low').length;

  return (
    <>
      {/* ── Page header — matches MapPage.tsx pattern exactly ── */}
      <div className="flex items-start justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl text-slate-900" style={{ fontWeight: 700 }}>Biodiversity GIS</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Geospatial biodiversity risk overlay — visualise supplier exposure to protected areas and threatened species.
          </p>
        </div>

        {/* Stats + export */}
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2">
            {[
              { label: 'Suppliers',  value: suppliers.length, cls: 'bg-slate-100 text-slate-600'    },
              { label: 'Avg Risk',   value: avgRisk,          cls: 'bg-amber-50 text-amber-700'     },
              { label: 'Critical',   value: criticalCount,    cls: 'bg-red-50 text-red-600'         },
              { label: 'Low Risk',   value: lowCount,         cls: 'bg-emerald-50 text-emerald-700' },
            ].map(({ label, value, cls }) => (
              <span key={label} className={clsx('text-xs px-2.5 py-1 rounded-full', cls)} style={{ fontWeight: 600 }}>
                {value} {label}
              </span>
            ))}
          </div>
          <button
            className="flex items-center gap-1.5 px-3 py-2 text-xs border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg transition-colors"
            style={{ fontWeight: 500 }}
          >
            <Download className="w-3.5 h-3.5" /> Export
          </button>
        </div>
      </div>

      {/* ── Mobile tab toggle — matches MapPage.tsx pattern ── */}
      <div className="flex md:hidden items-center gap-1 bg-slate-100 rounded-lg p-1 self-start flex-shrink-0">
        {([
          { key: 'list', icon: List,    label: 'Suppliers' },
          { key: 'map',  icon: MapIcon, label: 'Map'       },
        ] as const).map(t => (
          <button
            key={t.key}
            onClick={() => setMobileTab(t.key)}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-all',
              mobileTab === t.key ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500'
            )}
            style={{ fontWeight: mobileTab === t.key ? 600 : 500 }}
          >
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>

      {/* ── Three-panel split: list | map | risk profile ── */}
      <div className="flex-1 flex gap-4 min-h-0">

        {/* LEFT — Supplier list */}
        <div className={clsx(
          'md:flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm w-[280px] shrink-0 min-h-0',
          mobileTab === 'list' ? 'flex' : 'hidden md:flex'
        )}>
          <SupplierList
            suppliers={suppliers}
            selectedId={selectedId}
            onSelect={setSelectedId}
            hoveredId={hoveredId}
            onHover={setHoveredId}
          />
        </div>

        {/* CENTER — Map */}
        <div className={clsx(
          'md:flex flex-col rounded-2xl overflow-hidden border border-slate-200 shadow-sm flex-1 min-h-0',
          mobileTab === 'map' ? 'flex' : 'hidden md:flex'
        )}>
          <MapView
            suppliers={suppliers}
            selectedId={selectedId}
            onSelect={setSelectedId}
            hoveredId={hoveredId}
            onHover={setHoveredId}
          />
        </div>

        {/* RIGHT — Risk profile (always visible on desktop, slides in) */}
        <div className="hidden md:flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm w-[320px] shrink-0 min-h-0 overflow-hidden">
          <RiskProfile
            supplier={selectedSupplier}
            onClose={() => setSelectedId(null)}
          />
        </div>
      </div>
    </>
  );
}
