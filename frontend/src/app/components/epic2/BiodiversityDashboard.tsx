/**
 * BiodiversityDashboard.tsx
 *
 * Three-panel layout wired to live data:
 *   LEFT   — SupplierList  (visible immediately from session context)
 *   CENTRE — MapView       (real geocoded coords, layer toggles)
 *   RIGHT  — RiskProfile   (risk summary OR approved-supplier detail)
 *
 * Layer data is fetched ON DEMAND inside MapView when the user toggles a
 * layer — no background prefetch here. MapView caches each layer so
 * subsequent toggles are instant.
 */

import { useState, useEffect, useRef } from 'react';
import { Download, List, Map as MapIcon, RefreshCw, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import clsx from 'clsx';
import { useSuppliers } from '../../context/SupplierContext';
import { riskApi, SupplierRiskSummary } from '../../lib/api';
import SupplierList from './SupplierList';
import MapView from './MapView';
import RiskProfile from './RiskProfile';

const BASE: string = import.meta.env.VITE_API_URL ?? '';

interface DbCounts { capad_active: number; kba_total: number; species_total: number; }

function riskLevel(s: SupplierRiskSummary): 'critical' | 'high' | 'medium' | 'low' {
  const score = s.species_nearby * 2 + s.protected_areas_nearby * 3 + s.kba_nearby * 5;
  if (score >= 30) return 'critical';
  if (score >= 15) return 'high';
  if (score >= 5)  return 'medium';
  return 'low';
}

async function pMap<T, R>(
  items: T[],
  fn: (item: T) => Promise<R>,
  limit: number,
): Promise<R[]> {
  const results: R[] = [];
  let idx = 0;
  async function worker() {
    while (idx < items.length) {
      const i = idx++;
      results[i] = await fn(items[i]);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}

function upsertSummary(
  prev: SupplierRiskSummary[],
  result: SupplierRiskSummary,
): SupplierRiskSummary[] {
  const idx = prev.findIndex(s => s.supplier_id === result.supplier_id);
  if (idx >= 0) {
    const next = [...prev];
    next[idx] = result;
    return next;
  }
  return [...prev, result];
}

export default function BiodiversityDashboard() {
  const { suppliers } = useSuppliers();

  const [summaries, setSummaries]         = useState<SupplierRiskSummary[]>([]);
  const [dbCounts, setDbCounts]           = useState<DbCounts | null>(null);
  const [countsLoading, setCountsLoading] = useState(true);
  const [riskLoading, setRiskLoading]     = useState(false);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId,  setHoveredId]  = useState<string | null>(null);
  const [mobileTab,  setMobileTab]  = useState<'map' | 'list'>('list');

  const prefetchStarted = useRef(false);
  const currentRunId    = useRef(0);

  // ── Counts only — small, fast ─────────────────────────────────────────────
  useEffect(() => {
    if (prefetchStarted.current) return;
    prefetchStarted.current = true;
    setCountsLoading(true);
    fetch(`${BASE}/api/biodiversity/counts`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then((d: DbCounts) => setDbCounts(d))
      .catch(() => setDbCounts(null))
      .finally(() => setCountsLoading(false));
  }, []);

  // ── Risk summaries ────────────────────────────────────────────────────────
  const computeRisk = async () => {
    const runId = ++currentRunId.current;
    setRiskLoading(true);
    const candidates = suppliers.filter(
      s => s.coordinates && (
        s.status === 'approved' || s.status === 'validated' ||
        s.isValidated || s.status === 'pending'
      )
    );
    if (!candidates.length) { setRiskLoading(false); return; }
    await pMap(
      candidates,
      async s => {
        const result = await riskApi.summary({
          supplier_id:   s.id,
          supplier_name: s.enrichedName ?? s.name,
          lat:           s.coordinates!.lat,
          lng:           s.coordinates!.lng,
        }).catch(() => null);
        if (result && runId === currentRunId.current) {
          setSummaries(prev => upsertSummary(prev, result));
        }
        return result;
      },
      3,
    );
    if (runId === currentRunId.current) setRiskLoading(false);
  };

  const geocodedCount = suppliers.filter(s => !!s.coordinates).length;
  useEffect(() => {
    if (geocodedCount > 0) computeRisk();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geocodedCount, suppliers.length]);

  // ── CSV export ────────────────────────────────────────────────────────────
  const handleExport = () => {
    if (!summaries.length) return;
    const header = ['Supplier ID','Name','Lat','Lng','IBRA Region','Risk Level',
                    'Species Nearby','Protected Areas','KBAs'].join(',');
    const rows = summaries.map(s => [
      `"${s.supplier_id}"`,
      `"${s.supplier_name.replace(/"/g,'""')}"`,
      s.lat, s.lng,
      `"${s.ibra_region ?? ''}"`,
      riskLevel(s),
      s.species_nearby, s.protected_areas_nearby, s.kba_nearby,
    ].join(','));
    const csv  = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const a    = Object.assign(document.createElement('a'), {
      href: url, download: `eco-biodiversity-${new Date().toISOString().slice(0,10)}.csv`,
    });
    a.click();
    URL.revokeObjectURL(url);
  };

  const criticalCount = summaries.filter(s => riskLevel(s) === 'critical').length;
  const assessedCount = summaries.length;

  const selectedSupplier = suppliers.find(s => s.id === selectedId) ?? null;
  const selectedSummary  = summaries.find(s => s.supplier_id === selectedId) ?? null;

  return (
    <>
      {/* ── Page header ── */}
      <div className="flex items-start justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl text-slate-900" style={{ fontWeight: 700 }}>Biodiversity GIS</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Geospatial biodiversity risk — supplier exposure to protected areas, KBAs &amp; threatened species.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2">
            {countsLoading
              ? <span className="h-6 w-36 rounded-full bg-slate-100 animate-pulse block" />
              : [
                  { label: 'CAPAD',    value: dbCounts ? dbCounts.capad_active.toLocaleString('en-AU') : '—', cls: 'bg-teal-50 text-teal-700'   },
                  { label: 'KBAs',     value: dbCounts ? dbCounts.kba_total.toLocaleString('en-AU')    : '—', cls: 'bg-green-50 text-green-700' },
                  { label: 'Critical', value: criticalCount,                                                   cls: 'bg-red-50 text-red-600'     },
                  { label: 'Assessed', value: assessedCount,                                                   cls: 'bg-slate-100 text-slate-600' },
                ].map(({ label, value, cls }) => (
                  <span key={label} className={clsx('text-xs px-2.5 py-1 rounded-full', cls)} style={{ fontWeight: 600 }}>
                    {value} {label}
                  </span>
                ))
            }
          </div>

          <button
            onClick={computeRisk}
            disabled={riskLoading}
            className="flex items-center gap-1.5 px-3 py-2 text-xs border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg transition-colors disabled:opacity-50"
            style={{ fontWeight: 500 }}
          >
            <RefreshCw className={clsx('w-3.5 h-3.5', riskLoading && 'animate-spin')} />
            Refresh
          </button>

          <button
            onClick={handleExport}
            disabled={!summaries.length}
            className="flex items-center gap-1.5 px-3 py-2 text-xs border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg transition-colors disabled:opacity-40"
            style={{ fontWeight: 500 }}
          >
            <Download className="w-3.5 h-3.5" /> Export CSV
          </button>
        </div>
      </div>

      {/* ── Mobile tab toggle ── */}
      <div className="flex md:hidden items-center gap-1 bg-slate-100 rounded-lg p-1 self-start flex-shrink-0">
        {([{ key: 'list', icon: List, label: 'Suppliers' }, { key: 'map', icon: MapIcon, label: 'Map' }] as const).map(t => (
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

      {/* ── Three-panel split ── */}
      <div className="flex-1 flex gap-4 min-h-0">

        <div className={clsx(
          'md:flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm w-[280px] shrink-0 min-h-0 overflow-hidden',
          mobileTab === 'list' ? 'flex' : 'hidden md:flex'
        )}>
          <AnimatePresence>
            {riskLoading && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-50 border-b border-emerald-100 flex-shrink-0 overflow-hidden"
              >
                <Loader2 className="w-3 h-3 text-emerald-500 animate-spin flex-shrink-0" />
                <span className="text-[11px] text-emerald-700" style={{ fontWeight: 500 }}>
                  Computing biodiversity risk…
                </span>
              </motion.div>
            )}
          </AnimatePresence>
          <SupplierList
            suppliers={suppliers}
            summaries={summaries}
            riskLoading={riskLoading}
            selectedId={selectedId}
            onSelect={setSelectedId}
            hoveredId={hoveredId}
            onHover={setHoveredId}
          />
        </div>

        <div className={clsx(
          'md:flex flex-col rounded-2xl overflow-hidden border border-slate-200 shadow-sm flex-1 min-h-0',
          mobileTab === 'map' ? 'flex' : 'hidden md:flex'
        )}>
          <MapView
            suppliers={suppliers}
            summaries={summaries}
            selectedId={selectedId}
            onSelect={setSelectedId}
            hoveredId={hoveredId}
            onHover={setHoveredId}
          />
        </div>

        <div className="hidden md:flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm w-[320px] shrink-0 min-h-0 overflow-hidden">
          <RiskProfile
            supplier={selectedSupplier}
            summary={selectedSummary}
            onClose={() => setSelectedId(null)}
          />
        </div>
      </div>
    </>
  );
}
