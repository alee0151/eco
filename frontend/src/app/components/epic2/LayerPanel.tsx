import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Layers, Bird, Shield, TreePine, Droplets, AlertTriangle,
  ChevronDown, ChevronRight, Eye, EyeOff, X, Info,
} from 'lucide-react';
import clsx from 'clsx';
import { GIS_LAYER_GROUPS, GisLayerGroup, GisSubLayer } from '../../data/gis-layers-data';

export type ActiveLayers = Set<string>;

interface LayerPanelProps {
  activeLayers: ActiveLayers;
  onToggle: (subLayerId: string) => void;
}

/* Map group ids → Lucide icon */
function GroupIcon({ id, className }: { id: string; className?: string }) {
  const icons: Record<string, React.ElementType> = {
    'threatened-species':  Bird,
    'protected-regions':   Shield,
    'forest-cover':        TreePine,
    'water-bodies':        Droplets,
    'deforestation-risk':  AlertTriangle,
  };
  const Icon = icons[id] || Layers;
  return <Icon className={className} />;
}

/* ── Sub-layer row ─────────────────────────────────────── */
function SubLayerRow({ sub, active, onToggle }: { sub: GisSubLayer; active: boolean; onToggle: () => void }) {
  const featureCount = sub.features.length;
  return (
    <div
      className={clsx(
        'flex items-center gap-2.5 px-3 py-2 rounded-lg transition-all cursor-pointer select-none',
        active ? 'bg-emerald-50 border border-emerald-100' : 'hover:bg-slate-50'
      )}
      onClick={onToggle}
    >
      {/* Colour swatch */}
      <span
        className="w-3 h-3 rounded-sm shrink-0 border"
        style={{
          backgroundColor: sub.color + '40',   // 25% opacity swatch
          borderColor: sub.color,
        }}
      />

      <span className={clsx('flex-1 text-[12px] leading-tight', active ? 'text-slate-800' : 'text-slate-600')}
        style={{ fontWeight: active ? 600 : 400 }}>
        {sub.label}
      </span>

      <span className="text-[10px] text-slate-400 tabular-nums shrink-0">{featureCount}</span>

      <button
        className={clsx('p-0.5 rounded transition-colors shrink-0', active ? 'text-emerald-600' : 'text-slate-300 hover:text-slate-500')}
        onClick={e => { e.stopPropagation(); onToggle(); }}
        aria-label={active ? `Hide ${sub.label}` : `Show ${sub.label}`}
      >
        {active ? <Eye size={13} /> : <EyeOff size={13} />}
      </button>
    </div>
  );
}

/* ── Layer group accordion ─────────────────────────────── */
function LayerGroup({
  group, activeLayers, onToggle,
}: { group: GisLayerGroup; activeLayers: ActiveLayers; onToggle: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const activeCount = group.subLayers.filter(s => activeLayers.has(s.id)).length;

  return (
    <div className="border border-slate-100 rounded-xl overflow-hidden">
      {/* Group header */}
      <button
        className="w-full flex items-center gap-2.5 px-3 py-2.5 bg-white hover:bg-slate-50 transition-colors text-left"
        onClick={() => setOpen(v => !v)}
      >
        <span className="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">
          <GroupIcon id={group.id} className="w-3.5 h-3.5 text-slate-500" />
        </span>

        <div className="flex-1 min-w-0">
          <p className="text-[12px] text-slate-800 truncate" style={{ fontWeight: 600 }}>{group.label}</p>
          <p className="text-[10px] text-slate-400 truncate">{group.description}</p>
        </div>

        {activeCount > 0 && (
          <span className="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full shrink-0" style={{ fontWeight: 700 }}>
            {activeCount}
          </span>
        )}

        {open
          ? <ChevronDown size={14} className="text-slate-400 shrink-0" />
          : <ChevronRight size={14} className="text-slate-400 shrink-0" />}
      </button>

      {/* Sub-layers */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-slate-100"
          >
            <div className="p-2 space-y-1 bg-slate-50/60">
              {group.subLayers.map(sub => (
                <SubLayerRow
                  key={sub.id}
                  sub={sub}
                  active={activeLayers.has(sub.id)}
                  onToggle={() => onToggle(sub.id)}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── Main LayerPanel component ─────────────────────────── */
export default function LayerPanel({ activeLayers, onToggle }: LayerPanelProps) {
  const [open, setOpen] = useState(false);
  const totalActive = activeLayers.size;

  return (
    <div className="absolute top-3 left-3 z-[1001]">
      {/* Trigger button — matches MapPage Export btn style */}
      <button
        onClick={() => setOpen(v => !v)}
        className={clsx(
          'flex items-center gap-1.5 px-3 py-2 text-xs rounded-lg shadow-sm border transition-all',
          open || totalActive > 0
            ? 'bg-emerald-600 text-white border-emerald-700 hover:bg-emerald-700'
            : 'bg-white/95 backdrop-blur-sm text-slate-700 border-slate-200 hover:bg-slate-50'
        )}
        style={{ fontWeight: 600 }}
        aria-label="Toggle layer panel"
      >
        <Layers size={13} />
        Layers
        {totalActive > 0 && (
          <span className="bg-white/25 text-white px-1.5 py-0.5 rounded-full text-[10px]" style={{ fontWeight: 700 }}>
            {totalActive}
          </span>
        )}
      </button>

      {/* Floating panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.18 }}
            className="absolute top-full left-0 mt-2 w-[280px] bg-white rounded-2xl border border-slate-200 shadow-lg overflow-hidden"
          >
            {/* Panel header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Layers size={14} className="text-emerald-600" />
                <span className="text-sm text-slate-800" style={{ fontWeight: 700 }}>Dataset Layers</span>
              </div>
              <div className="flex items-center gap-2">
                {totalActive > 0 && (
                  <button
                    className="text-[11px] text-slate-400 hover:text-red-500 transition-colors"
                    onClick={() => GIS_LAYER_GROUPS.forEach(g => g.subLayers.forEach(s => activeLayers.has(s.id) && onToggle(s.id)))}
                    style={{ fontWeight: 500 }}
                  >
                    Clear all
                  </button>
                )}
                <button
                  onClick={() => setOpen(false)}
                  className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 transition-colors"
                >
                  <X size={13} />
                </button>
              </div>
            </div>

            {/* Source note */}
            <div className="px-4 py-2 bg-slate-50/60 border-b border-slate-100 flex items-start gap-1.5">
              <Info size={11} className="text-slate-400 mt-0.5 shrink-0" />
              <p className="text-[10px] text-slate-400 leading-relaxed">
                Mock data based on EPBC Act, TERN AusCover, ABARES, Global Forest Watch, and BOM datasets.
              </p>
            </div>

            {/* Layer groups */}
            <div className="p-3 space-y-2 max-h-[420px] overflow-y-auto">
              {GIS_LAYER_GROUPS.map(group => (
                <LayerGroup
                  key={group.id}
                  group={group}
                  activeLayers={activeLayers}
                  onToggle={onToggle}
                />
              ))}
            </div>

            {/* Active count footer */}
            <div className="px-4 py-2.5 border-t border-slate-100 bg-slate-50/40">
              <p className="text-[11px] text-slate-500">
                <span style={{ fontWeight: 600 }}>{totalActive}</span> of{' '}
                <span style={{ fontWeight: 600 }}>{GIS_LAYER_GROUPS.reduce((n, g) => n + g.subLayers.length, 0)}</span>
                {' '}sub-layers active
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
