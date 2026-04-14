/**
 * MapView.tsx — centre panel of the Biodiversity split layout.
 *
 * Features:
 *  - Renders supplier markers using real geocoded coordinates from SupplierContext
 *  - Layer toggle panel: Species Occurrences, CAPAD Protected Areas, KBA, IBRA regions
 *  - Marker colour driven by SupplierRiskSummary risk level
 *  - Fly-to on supplier select, pulse animation on hover/select
 *  - Risk legend bottom-left
 *  - IBRA layer:
 *      • Fetches all IBRA 7 bioregion polygons once (two paginated requests, cached
 *        in ibraRecordsRef so we never re-fetch on selection changes)
 *      • drawIbraLayer() rebuilds the Leaflet GeoJSON layer from cached records
 *        + current summaries + current selectedId — called on every relevant
 *        state change so highlights are always up-to-date
 *      • Supplier-linked regions: strong fill + solid border
 *      • Selected supplier's region: extra-thick border + 'Selected' badge
 *      • Reference regions: faint dashed outline
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import { Layers, X } from 'lucide-react';
import clsx from 'clsx';
import wellknown from 'wellknown';
import { Supplier } from '../../context/SupplierContext';
import { IbraRecord, SupplierRiskSummary, speciesApi, ibraApi } from '../../lib/api';
import 'leaflet/dist/leaflet.css';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon   from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

const RISK_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high:     '#f97316',
  medium:   '#f59e0b',
  low:      '#10b981',
  none:     '#94a3b8',
};

const IBRA_COLOR = '#2563eb';

function getRiskLevel(summary?: SupplierRiskSummary): string {
  if (!summary) return 'none';
  const score = summary.species_nearby * 2 + summary.protected_areas_nearby * 3 + summary.kba_nearby * 5;
  if (score >= 30) return 'critical';
  if (score >= 15) return 'high';
  if (score >= 5)  return 'medium';
  return 'low';
}

function createIcon(color: string, size: number, pulse: boolean) {
  return L.divIcon({
    className: '',
    html: `<div style="display:flex;align-items:center;justify-content:center;width:30px;height:30px;position:relative">
      ${pulse ? `<div style="position:absolute;width:30px;height:30px;border-radius:50%;background:${color};opacity:0.18;animation:bioPulse 1.5s ease-in-out infinite;"></div>` : ''}
      <div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2.5px solid white;box-shadow:0 1px 6px rgba(0,0,0,0.25);position:relative;z-index:1;"></div>
    </div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

// ── Layer definitions ─────────────────────────────────────────────────────
interface LayerDef {
  id:    string;
  label: string;
  color: string;
  group: string;
  desc:  string;
}

const LAYER_DEFS: LayerDef[] = [
  { id: 'species', label: 'Species Occurrences',    color: '#8b5cf6', group: 'Biodiversity',     desc: 'ALA threatened species records near suppliers' },
  { id: 'capad',   label: 'CAPAD Protected Areas',  color: '#0d9488', group: 'Protected Regions', desc: 'Commonwealth protected areas (CAPAD 2022)' },
  { id: 'kba',     label: 'Key Biodiversity Areas', color: '#16a34a', group: 'Protected Regions', desc: 'BirdLife KBA boundaries' },
  { id: 'ibra',    label: 'IBRA Bioregions',        color: IBRA_COLOR, group: 'Bioregions',       desc: 'IBRA 7 bioregion outlines (all 89 regions)' },
];

interface MapViewProps {
  suppliers:  Supplier[];
  summaries:  SupplierRiskSummary[];
  selectedId: string | null;
  onSelect:   (id: string) => void;
  hoveredId:  string | null;
  onHover:    (id: string | null) => void;
}

export default function MapView({ suppliers, summaries, selectedId, onSelect, hoveredId, onHover }: MapViewProps) {
  const containerRef  = useRef<HTMLDivElement>(null);
  const mapRef        = useRef<L.Map | null>(null);
  const markersRef    = useRef<Map<string, L.Marker>>(new Map());
  const layerGroupRef = useRef<Map<string, L.LayerGroup>>(new Map());

  // Cache raw IBRA records so we never re-fetch on selection changes
  const ibraRecordsRef = useRef<IbraRecord[] | null>(null);

  const [layerPanelOpen, setLayerPanelOpen] = useState(false);
  const [activeLayers,   setActiveLayers]   = useState<Set<string>>(new Set(['species']));
  const [layerLoading,   setLayerLoading]   = useState<Set<string>>(new Set());

  // ── Init map ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      center: [-25.5, 134.5],
      zoom: 4,
      zoomControl: false,
      attributionControl: false,
    });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OSM &copy; CARTO',
    }).addTo(map);
    L.control.zoom({ position: 'bottomright' }).addTo(map);
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      markersRef.current.clear();
      layerGroupRef.current.clear();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Add/update supplier markers ──────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markersRef.current.forEach((m, id) => {
      if (!suppliers.find(s => s.id === id)) { m.remove(); markersRef.current.delete(id); }
    });
    suppliers.forEach(s => {
      if (!s.coordinates) return;
      const summary  = summaries.find(r => r.supplier_id === s.id);
      const level    = getRiskLevel(summary);
      const color    = RISK_COLORS[level];
      const isActive = s.id === selectedId || s.id === hoveredId;
      const size     = isActive ? 18 : 12;

      if (markersRef.current.has(s.id)) {
        markersRef.current.get(s.id)!.setIcon(createIcon(color, size, isActive));
        return;
      }

      const marker = L.marker([s.coordinates.lat, s.coordinates.lng], {
        icon: createIcon(color, size, isActive),
      }).addTo(map);

      const speciesNames = summary?.threatened_species_names.slice(0, 3).join(', ') || 'None recorded';
      const ibraLabel    = summary?.ibra_region
        ? `${summary.ibra_region}${summary.ibra_code ? ` (${summary.ibra_code})` : ''}`
        : s.region ?? '';

      marker.bindPopup(`
        <div style="min-width:200px;font-family:sans-serif">
          <p style="font-weight:700;font-size:13px;color:#0f172a">${s.enrichedName ?? s.name}</p>
          <p style="font-size:11px;color:#64748b;margin-top:2px">${ibraLabel}</p>
          <div style="margin-top:8px;padding:6px 8px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0">
            <p style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px">Risk Indicators</p>
            <p style="font-size:11px;color:#334155">🦎 <b>${summary?.species_nearby ?? 0}</b> species nearby</p>
            <p style="font-size:11px;color:#334155">🛡️ <b>${summary?.protected_areas_nearby ?? 0}</b> protected areas</p>
            <p style="font-size:11px;color:#334155">🌿 <b>${summary?.kba_nearby ?? 0}</b> KBAs</p>
          </div>
          ${summary?.threatened_species_names.length ? `<p style="font-size:10px;color:#94a3b8;margin-top:6px">Species: ${speciesNames}</p>` : ''}
          <p style="margin-top:6px;font-size:11px;font-weight:600;color:${color}">${level.toUpperCase()} RISK</p>
        </div>
      `);

      marker.on('click',     () => onSelect(s.id));
      marker.on('mouseover', () => onHover(s.id));
      marker.on('mouseout',  () => onHover(null));
      markersRef.current.set(s.id, marker);
    });
  }, [suppliers, summaries, selectedId, hoveredId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Fly to selected ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!selectedId || !mapRef.current) return;
    const s = suppliers.find(x => x.id === selectedId);
    if (s?.coordinates) {
      mapRef.current.flyTo([s.coordinates.lat, s.coordinates.lng], 8, { duration: 1.2 });
      setTimeout(() => markersRef.current.get(s.id)?.openPopup(), 1300);
    }
  }, [selectedId, suppliers]);

  // ── IBRA draw helper ───────────────────────────────────────────────────────
  // Rebuilds the IBRA Leaflet layer from cached records + current
  // summaries + current selectedId without re-fetching from the backend.
  // Safe to call repeatedly — always clears the old layer group first.
  const drawIbraLayer = useCallback((records: IbraRecord[]) => {
    const map = mapRef.current;
    if (!map) return;

    // Tear down any existing IBRA layer group
    layerGroupRef.current.get('ibra')?.remove();
    const group = L.layerGroup().addTo(map);
    layerGroupRef.current.set('ibra', group);

    // Determine which IBRA codes are linked to suppliers via risk summaries
    const highlightedCodes = new Set(
      summaries.filter(sm => sm.ibra_code).map(sm => sm.ibra_code as string)
    );

    // Determine the IBRA code of the *currently selected* supplier
    const selectedCode = selectedId
      ? (summaries.find(sm => sm.supplier_id === selectedId)?.ibra_code ?? null)
      : null;

    records.forEach(record => {
      if (!record.geometry) return;
      try {
        const geojson = wellknown.parse(record.geometry);
        if (!geojson) return;

        const code          = record.ibra_reg_code ?? '';
        const isSelected    = !!selectedCode && code === selectedCode;
        const isHighlighted = highlightedCodes.has(code);

        // Collect supplier names that fall in this bioregion
        const matchedSuppliers = summaries
          .filter(sm => sm.ibra_code === code)
          .map(sm => sm.supplier_name)
          .filter(Boolean);

        const areakm2 = record.shape_area
          ? (record.shape_area / 1_000_000).toFixed(0)
          : null;

        const supplierBadge = matchedSuppliers.length > 0
          ? `<br/><span style="display:inline-block;margin-top:4px;padding:2px 6px;`
            + (isSelected
              ? `background:#fef9c3;color:#854d0e;border-radius:4px;font-size:10px;font-weight:700">Selected: `
              : `background:#dbeafe;color:#1d4ed8;border-radius:4px;font-size:10px;font-weight:600">`)
            + `${matchedSuppliers.slice(0, 3).join(', ')}${matchedSuppliers.length > 3 ? ` +${matchedSuppliers.length - 3} more` : ''}`
            + `</span>`
          : '';

        // Three-tier style: selected > highlighted > reference
        const style = isSelected
          ? {
              color:       IBRA_COLOR,
              weight:      3,
              opacity:     1,
              fillColor:   IBRA_COLOR,
              fillOpacity: 0.25,
              dashArray:   undefined as string | undefined,
            }
          : isHighlighted
          ? {
              color:       IBRA_COLOR,
              weight:      2.5,
              opacity:     0.9,
              fillColor:   IBRA_COLOR,
              fillOpacity: 0.18,
              dashArray:   undefined as string | undefined,
            }
          : {
              color:       IBRA_COLOR,
              weight:      0.8,
              opacity:     0.5,
              fillColor:   IBRA_COLOR,
              fillOpacity: 0.03,
              dashArray:   '4 5',
            };

        L.geoJSON(geojson as any, { style })
          .bindTooltip(
            `<b style="font-size:12px">${record.ibra_reg_name ?? code ?? 'Unknown'}</b>`
            + `<br/><span style="font-size:10px;color:#64748b">`
            + `${record.state ?? 'Australia'}${areakm2 ? ` · ${areakm2} km²` : ''}`
            + `</span>`
            + supplierBadge,
            { sticky: true }
          )
          .addTo(group);
      } catch (err) {
        console.warn('[MapView] Failed to parse IBRA geometry for', record.ibra_reg_code, err);
      }
    });
  }, [summaries, selectedId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Re-draw IBRA layer when summaries or selectedId change ────────────
  // This ensures highlights are always in sync even if the IBRA layer was
  // toggled on before summaries finished loading, or when user selects a
  // different supplier.
  useEffect(() => {
    if (!activeLayers.has('ibra')) return;     // layer not active — nothing to do
    if (!ibraRecordsRef.current) return;       // records not yet fetched — toggleLayer will draw
    drawIbraLayer(ibraRecordsRef.current);
  }, [summaries, selectedId, activeLayers, drawIbraLayer]);

  // ── Toggle dataset layers ───────────────────────────────────────────────
  const toggleLayer = async (layerId: string) => {
    const map = mapRef.current;
    if (!map) return;

    if (activeLayers.has(layerId)) {
      layerGroupRef.current.get(layerId)?.remove();
      layerGroupRef.current.delete(layerId);
      setActiveLayers(prev => { const n = new Set(prev); n.delete(layerId); return n; });
      return;
    }

    setLayerLoading(prev => new Set(prev).add(layerId));
    setActiveLayers(prev => new Set(prev).add(layerId));

    try {
      if (layerId === 'species') {
        const group = L.layerGroup().addTo(map);
        layerGroupRef.current.set(layerId, group);
        const suppliersWithCoords = suppliers.filter(s => s.coordinates);
        if (suppliersWithCoords.length > 0) {
          const first = suppliersWithCoords[0];
          const records = await speciesApi.byBbox({
            min_lat: first.coordinates!.lat - 2,
            max_lat: first.coordinates!.lat + 2,
            min_lng: first.coordinates!.lng - 2,
            max_lng: first.coordinates!.lng + 2,
            limit: 300,
          }).catch(() => []);
          records.forEach(r => {
            if (!r.decimallatitude || !r.decimallongitude) return;
            L.circleMarker([r.decimallatitude, r.decimallongitude], {
              radius: 4, color: '#8b5cf6', fillColor: '#8b5cf6',
              fillOpacity: 0.5, weight: 1, opacity: 0.7,
            }).bindTooltip(`<b>${r.vernacularname ?? r.scientificname ?? 'Unknown'}</b><br/>${r.stateprovince ?? ''}`)
              .addTo(group);
          });
        }
      }

      if (layerId === 'capad') {
        const group = L.layerGroup().addTo(map);
        layerGroupRef.current.set(layerId, group);
        if (summaries[0]) {
          suppliers.filter(s => s.coordinates).forEach(s => {
            const sm = summaries.find(r => r.supplier_id === s.id);
            if (!sm || sm.protected_areas_nearby === 0) return;
            L.circle([s.coordinates!.lat, s.coordinates!.lng], {
              radius: 55000, color: '#0d9488', fillColor: '#0d9488',
              fillOpacity: 0.05, weight: 1.5, dashArray: '6 4',
            }).bindTooltip(`${sm.protected_areas_nearby} protected areas within ~50 km of ${s.enrichedName ?? s.name}`)
              .addTo(group);
          });
        }
      }

      if (layerId === 'kba') {
        const group = L.layerGroup().addTo(map);
        layerGroupRef.current.set(layerId, group);
        suppliers.filter(s => s.coordinates).forEach(s => {
          const sm = summaries.find(r => r.supplier_id === s.id);
          if (!sm || sm.kba_nearby === 0) return;
          L.circle([s.coordinates!.lat, s.coordinates!.lng], {
            radius: 45000, color: '#16a34a', fillColor: '#16a34a',
            fillOpacity: 0.06, weight: 1.5, dashArray: '4 6',
          }).bindTooltip(`${sm.kba_nearby} Key Biodiversity Areas near ${s.enrichedName ?? s.name}`)
            .addTo(group);
        });
      }

      if (layerId === 'ibra') {
        // Fetch records only if we haven't already cached them
        if (!ibraRecordsRef.current) {
          const [page1, page2] = await Promise.all([
            ibraApi.list({ limit: 100, offset: 0   }).catch(() => []),
            ibraApi.list({ limit: 100, offset: 100 }).catch(() => []),
          ]);
          const allRecords = [...page1, ...page2];

          // Deduplicate by IBRA region code
          const seen = new Set<string>();
          ibraRecordsRef.current = allRecords.filter(r => {
            const key = r.ibra_reg_code ?? r.ibra_reg_name ?? String(r.id);
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
          });
        }

        // Draw using current summaries + selectedId (drawIbraLayer reads from
        // the closure captured at render time, so it always has fresh values)
        drawIbraLayer(ibraRecordsRef.current);
      }
    } catch (e) {
      console.warn(`[MapView] failed to load layer ${layerId}:`, e);
    } finally {
      setLayerLoading(prev => { const n = new Set(prev); n.delete(layerId); return n; });
    }
  };

  const criticalCount = summaries.filter(s => getRiskLevel(s) === 'critical').length;
  const highCount     = summaries.filter(s => getRiskLevel(s) === 'high').length;

  return (
    <div className="relative h-full w-full">
      <style>{`
        @keyframes bioPulse {
          0%,100% { transform:scale(1);   opacity:0.18; }
          50%      { transform:scale(1.5); opacity:0.05; }
        }
      `}</style>

      <div ref={containerRef} className="h-full w-full" />

      {/* ── Layer toggle button ── */}
      <button
        onClick={() => setLayerPanelOpen(v => !v)}
        className={clsx(
          'absolute top-3 left-3 z-[1000] flex items-center gap-1.5 px-3 py-2 text-xs rounded-xl shadow-md border transition-colors',
          layerPanelOpen
            ? 'bg-emerald-600 text-white border-emerald-700'
            : 'bg-white/95 backdrop-blur-sm text-slate-700 border-slate-200/80 hover:bg-slate-50'
        )}
        style={{ fontWeight: 600 }}
      >
        <Layers className="w-3.5 h-3.5" />
        Layers
        {activeLayers.size > 0 && (
          <span className={clsx('text-[10px] px-1.5 py-0.5 rounded-full', layerPanelOpen ? 'bg-white/20' : 'bg-emerald-100 text-emerald-700')}>
            {activeLayers.size}
          </span>
        )}
      </button>

      {/* ── Layer panel ── */}
      {layerPanelOpen && (
        <div className="absolute top-12 left-3 z-[1000] w-[240px] bg-white/97 backdrop-blur-sm rounded-xl shadow-lg border border-slate-200/80 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
            <span className="text-xs text-slate-800" style={{ fontWeight: 600 }}>Map Layers</span>
            <button onClick={() => setLayerPanelOpen(false)} className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {Array.from(new Set(LAYER_DEFS.map(l => l.group))).map(group => (
            <div key={group}>
              <p className="px-4 pt-3 pb-1 text-[10px] text-slate-400 uppercase tracking-widest" style={{ fontWeight: 600 }}>{group}</p>
              {LAYER_DEFS.filter(l => l.group === group).map(layer => {
                const isActive  = activeLayers.has(layer.id);
                const isLoading = layerLoading.has(layer.id);
                return (
                  <div
                    key={layer.id}
                    className={clsx(
                      'flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors select-none',
                      isActive ? 'bg-slate-50' : 'hover:bg-slate-50/60'
                    )}
                    onClick={() => toggleLayer(layer.id)}
                  >
                    <div
                      className={clsx('w-8 h-4 rounded-full border-2 flex items-center transition-all duration-200', isActive ? 'justify-end' : 'justify-start')}
                      style={{ borderColor: layer.color, backgroundColor: isActive ? layer.color + '30' : 'transparent' }}
                    >
                      <div className="w-3 h-3 rounded-full mx-0.5" style={{ backgroundColor: isActive ? layer.color : '#cbd5e1' }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] text-slate-700" style={{ fontWeight: isActive ? 600 : 500 }}>{layer.label}</p>
                      <p className="text-[10px] text-slate-400 leading-tight">{layer.desc}</p>
                    </div>
                    {isLoading && (
                      <div className="w-3.5 h-3.5 border-2 border-slate-300 border-t-transparent rounded-full animate-spin" />
                    )}
                  </div>
                );
              })}
            </div>
          ))}

          <p className="px-4 py-2 text-[10px] text-slate-400 border-t border-slate-100">More datasets coming soon: water stress, minerals</p>
        </div>
      )}

      {/* ── IBRA legend ── */}
      {activeLayers.has('ibra') && (
        <div className="absolute bottom-20 left-4 bg-white/95 backdrop-blur-sm rounded-xl p-3 shadow-md border border-slate-200/80 z-[1000] min-w-[160px]">
          <p className="text-[10px] text-slate-500 mb-2 uppercase tracking-wider" style={{ fontWeight: 600 }}>IBRA Bioregions</p>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="w-6 h-3 rounded-sm shrink-0 border-2" style={{ backgroundColor: IBRA_COLOR + '40', borderColor: IBRA_COLOR }} />
              <span className="text-[11px] text-slate-600">Selected region</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-6 h-3 rounded-sm shrink-0 border-2" style={{ backgroundColor: IBRA_COLOR + '2e', borderColor: IBRA_COLOR }} />
              <span className="text-[11px] text-slate-600">Supplier region</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-6 h-3 rounded-sm shrink-0 border" style={{ backgroundColor: IBRA_COLOR + '08', borderColor: IBRA_COLOR + '80', borderStyle: 'dashed' }} />
              <span className="text-[11px] text-slate-600">Reference region</span>
            </div>
          </div>
          <p className="text-[9px] text-slate-400 mt-2 leading-tight">Hover a polygon to see<br/>region name &amp; area</p>
        </div>
      )}

      {/* ── Risk legend ── */}
      <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-sm rounded-xl p-3 shadow-md border border-slate-200/80 z-[1000]">
        <p className="text-[10px] text-slate-500 mb-2 uppercase tracking-wider" style={{ fontWeight: 600 }}>Risk Level</p>
        <div className="space-y-1.5">
          {(['critical', 'high', 'medium', 'low'] as const).map(level => (
            <div key={level} className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: RISK_COLORS[level] }} />
              <span className="text-[11px] text-slate-600 capitalize">{level}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Top-right summary badges ── */}
      <div className="absolute top-3 right-3 flex gap-2 z-[1000]">
        {[
          { label: 'Critical', count: criticalCount, color: '#ef4444' },
          { label: 'High',     count: highCount,     color: '#f97316' },
        ].filter(s => s.count > 0).map(stat => (
          <div key={stat.label} className="bg-white/95 backdrop-blur-sm rounded-lg px-3 py-1.5 shadow-sm border border-slate-200/80 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: stat.color }} />
            <span className="text-[11px] text-slate-700" style={{ fontWeight: 600 }}>{stat.count} {stat.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
