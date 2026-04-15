/**
 * MapView.tsx — centre panel of the Biodiversity split layout.
 *
 * Layout of bottom-left controls (bottom → top):
 *   [Risk Legend]  ← always visible
 *   [Layers btn]   ← always visible, sits directly above legend
 *   [Layer panel]  ← expands upward from the Layers btn when open
 *
 * IBRA highlight tiers:
 *   Selected supplier's bioregion  → amber fill, thick border
 *   Other supplier bioregions      → blue fill, solid border
 *   Reference regions              → faint blue dashed outline
 *
 * CAPAD layer:
 *   Fetches real records from /api/biodiversity/capad (capad_protected_areas)
 *   Colour-coded by IUCN category; each marker shows a rich popup.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import { Layers, X } from 'lucide-react';
import clsx from 'clsx';
import wellknown from 'wellknown';
import { Supplier } from '../../context/SupplierContext';
import { IbraRecord, CapadRecord, SupplierRiskSummary, speciesApi, ibraApi, capadApi } from '../../lib/api';
import 'leaflet/dist/leaflet.css';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon   from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

// ── Risk colours ──────────────────────────────────────────────────────────────
const RISK_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high:     '#f97316',
  medium:   '#f59e0b',
  low:      '#10b981',
  none:     '#94a3b8',
};

// ── IBRA colours ──────────────────────────────────────────────────────────────
const IBRA_COLOR          = '#2563eb';
const IBRA_SELECTED_COLOR = '#f59e0b';

// ── CAPAD IUCN colours ────────────────────────────────────────────────────────
/**
 * Colour each protected area marker by its IUCN management category.
 * Categories Ia / Ib are strict nature reserves → darkest teal.
 * Not Reported / unknown → neutral slate.
 */
const CAPAD_IUCN_COLORS: Record<string, string> = {
  'Ia':           '#0f4c5c',   // Strict Nature Reserve
  'Ib':           '#0d6e6e',   // Wilderness Area
  'II':           '#0d9488',   // National Park
  'III':          '#06b6d4',   // Natural Monument
  'IV':           '#16a34a',   // Habitat/Species Management
  'V':            '#84cc16',   // Protected Landscape/Seascape
  'VI':           '#10b981',   // Protected Area with Sustainable Use
  'Not Reported': '#94a3b8',
  'Not Applicable': '#94a3b8',
};

function capadIucnColor(cat: string | null): string {
  if (!cat) return CAPAD_IUCN_COLORS['Not Reported'];
  return CAPAD_IUCN_COLORS[cat] ?? CAPAD_IUCN_COLORS['Not Reported'];
}

// ── CAPAD marker HTML ─────────────────────────────────────────────────────────
function capadIcon(color: string) {
  return L.divIcon({
    className: '',
    html: `<div style="
      width:10px;height:10px;
      border-radius:3px;
      background:${color};
      border:2px solid white;
      box-shadow:0 1px 4px rgba(0,0,0,0.3);
    "></div>`,
    iconSize: [10, 10],
    iconAnchor: [5, 5],
  });
}

// ── CAPAD popup content ───────────────────────────────────────────────────────
function capadPopup(r: CapadRecord): string {
  const color    = capadIucnColor(r.iucn_cat);
  const area     = r.gis_area_ha != null ? `${Number(r.gis_area_ha).toLocaleString()} ha` : '—';
  const epbc     = r.epbc_trigger || '—';
  const authority = r.authority  || '—';
  const governance = r.governance || '—';
  return `
    <div style="min-width:210px;font-family:sans-serif;">
      <p style="font-weight:700;font-size:13px;color:#0f172a;margin-bottom:2px">${r.pa_name ?? 'Protected Area'}</p>
      <span style="display:inline-block;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:700;color:white;background:${color};margin-bottom:6px">
        IUCN ${r.iucn_cat ?? 'Not Reported'}
      </span>
      <div style="font-size:11px;color:#334155;line-height:1.7">
        <p><b>Type:</b> ${r.pa_type ?? '—'} (${r.pa_type_abbr ?? '—'})</p>
        <p><b>State:</b> ${r.state ?? '—'}</p>
        <p><b>Area:</b> ${area}</p>
        <p><b>Governance:</b> ${governance}</p>
        <p><b>Authority:</b> ${authority}</p>
        <p><b>EPBC trigger:</b> ${epbc}</p>
      </div>
    </div>
  `;
}

// ── Risk scoring ──────────────────────────────────────────────────────────────
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

// ── Layer definitions ─────────────────────────────────────────────────────────
interface LayerDef { id: string; label: string; color: string; group: string; desc: string; }

const LAYER_DEFS: LayerDef[] = [
  { id: 'species', label: 'Species Occurrences',    color: '#8b5cf6', group: 'Biodiversity',     desc: 'ALA threatened species records near suppliers' },
  { id: 'capad',   label: 'CAPAD Protected Areas',  color: '#0d9488', group: 'Protected Regions', desc: 'Real CAPAD 2024 protected areas — coloured by IUCN category' },
  { id: 'kba',     label: 'Key Biodiversity Areas', color: '#16a34a', group: 'Protected Regions', desc: 'BirdLife KBA boundaries' },
  { id: 'ibra',    label: 'IBRA Bioregions',        color: IBRA_COLOR, group: 'Bioregions',       desc: 'IBRA 7 bioregion outlines (all 89 regions)' },
];

// ── CAPAD IUCN legend entries for the layer panel ─────────────────────────────
const CAPAD_LEGEND: { cat: string; label: string }[] = [
  { cat: 'Ia',           label: 'Ia — Strict Nature Reserve' },
  { cat: 'Ib',           label: 'Ib — Wilderness Area' },
  { cat: 'II',           label: 'II — National Park' },
  { cat: 'III',          label: 'III — Natural Monument' },
  { cat: 'IV',           label: 'IV — Habitat/Species Mgmt' },
  { cat: 'V',            label: 'V — Protected Landscape' },
  { cat: 'VI',           label: 'VI — Sustainable Use' },
  { cat: 'Not Reported', label: 'Not Reported / N/A' },
];

// ── Props ─────────────────────────────────────────────────────────────────────
interface MapViewProps {
  suppliers:  Supplier[];
  summaries:  SupplierRiskSummary[];
  selectedId: string | null;
  onSelect:   (id: string) => void;
  hoveredId:  string | null;
  onHover:    (id: string | null) => void;
}

export default function MapView({ suppliers, summaries, selectedId, onSelect, hoveredId, onHover }: MapViewProps) {
  const containerRef   = useRef<HTMLDivElement>(null);
  const mapRef         = useRef<L.Map | null>(null);
  const markersRef     = useRef<Map<string, L.Marker>>(new Map());
  const layerGroupRef  = useRef<Map<string, L.LayerGroup>>(new Map());
  const ibraRecordsRef = useRef<IbraRecord[] | null>(null);
  // Cache fetched CAPAD records so re-toggling doesn't re-fetch
  const capadRecordsRef = useRef<CapadRecord[] | null>(null);

  const [layerPanelOpen,   setLayerPanelOpen]   = useState(false);
  const [activeLayers,     setActiveLayers]      = useState<Set<string>>(new Set(['species']));
  const [layerLoading,     setLayerLoading]      = useState<Set<string>>(new Set());
  const [capadLegendOpen,  setCapadLegendOpen]   = useState(false);

  // ── Init map ──────────────────────────────────────────────────────────────
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

  // ── Supplier markers ───────────────────────────────────────────────────────
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

  // ── Fly to selected ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!selectedId || !mapRef.current) return;
    const s = suppliers.find(x => x.id === selectedId);
    if (s?.coordinates) {
      mapRef.current.flyTo([s.coordinates.lat, s.coordinates.lng], 8, { duration: 1.2 });
      setTimeout(() => markersRef.current.get(s.id)?.openPopup(), 1300);
    }
  }, [selectedId, suppliers]);

  // ── IBRA draw helper ──────────────────────────────────────────────────────
  const drawIbraLayer = useCallback((records: IbraRecord[]) => {
    const map = mapRef.current;
    if (!map) return;

    layerGroupRef.current.get('ibra')?.remove();
    const group = L.layerGroup().addTo(map);
    layerGroupRef.current.set('ibra', group);

    const selectedCode: string | null = selectedId
      ? (summaries.find(sm => sm.supplier_id === selectedId)?.ibra_code ?? null)
      : null;

    const highlightedCodes = new Set<string>(
      summaries
        .filter(sm => sm.ibra_code && sm.ibra_code !== selectedCode)
        .map(sm => sm.ibra_code as string)
    );

    records.forEach(record => {
      if (!record.geometry) return;
      try {
        const geojson = wellknown.parse(record.geometry);
        if (!geojson) return;

        const code          = record.ibra_reg_code ?? '';
        const isSelected    = !!selectedCode && code === selectedCode;
        const isHighlighted = highlightedCodes.has(code);

        const matchedSuppliers = summaries
          .filter(sm => sm.ibra_code === code)
          .map(sm => sm.supplier_name)
          .filter(Boolean);

        const areakm2 = record.shape_area
          ? (record.shape_area / 1_000_000).toFixed(0)
          : null;

        let supplierBadge = '';
        if (matchedSuppliers.length > 0) {
          const names = matchedSuppliers.slice(0, 3).join(', ')
            + (matchedSuppliers.length > 3 ? ` +${matchedSuppliers.length - 3} more` : '');
          const badgeStyle = isSelected
            ? 'background:#fef3c7;color:#92400e;border-radius:4px;font-size:10px;font-weight:700'
            : 'background:#dbeafe;color:#1d4ed8;border-radius:4px;font-size:10px;font-weight:600';
          const prefix = isSelected ? '\uD83D\uDCCD ' : '';
          supplierBadge = `<br/><span style="display:inline-block;margin-top:4px;padding:2px 6px;${badgeStyle}">${prefix}${names}</span>`;
        }

        const style = isSelected
          ? { color: IBRA_SELECTED_COLOR, weight: 3,   opacity: 1,   fillColor: IBRA_SELECTED_COLOR, fillOpacity: 0.22, dashArray: undefined as string | undefined }
          : isHighlighted
          ? { color: IBRA_COLOR,          weight: 2.5, opacity: 0.9, fillColor: IBRA_COLOR,          fillOpacity: 0.15, dashArray: undefined as string | undefined }
          : { color: IBRA_COLOR,          weight: 0.8, opacity: 0.4, fillColor: IBRA_COLOR,          fillOpacity: 0.03, dashArray: '4 5' };

        const tooltipContent =
          `<b style="font-size:12px">${record.ibra_reg_name ?? code ?? 'Unknown'}</b>` +
          `<br/><span style="font-size:10px;color:#64748b">` +
          `${record.state ?? 'Australia'}${areakm2 ? ` \u00b7 ${areakm2} km\u00b2` : ''}` +
          `</span>` +
          supplierBadge;

        L.geoJSON(geojson as any, { style })
          .bindTooltip(tooltipContent, { sticky: true })
          .addTo(group);
      } catch (err) {
        console.warn('[MapView] IBRA parse error for', record.ibra_reg_code, err);
      }
    });
  }, [summaries, selectedId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Re-draw IBRA when summaries or selection changes ──────────────────────
  useEffect(() => {
    if (!activeLayers.has('ibra') || !ibraRecordsRef.current) return;
    drawIbraLayer(ibraRecordsRef.current);
  }, [summaries, selectedId, activeLayers, drawIbraLayer]);

  // ── CAPAD draw helper — real records from DB ───────────────────────────────
  /**
   * Render each CAPAD protected area as a small square marker coloured by
   * its IUCN management category.  Each marker opens a rich popup with:
   *   PA name, type, IUCN cat, area (ha), governance, authority, EPBC trigger.
   *
   * Only records with valid lat/lon are rendered.
   */
  const drawCapadLayer = useCallback((records: CapadRecord[]) => {
    const map = mapRef.current;
    if (!map) return;

    layerGroupRef.current.get('capad')?.remove();
    const group = L.layerGroup().addTo(map);
    layerGroupRef.current.set('capad', group);

    let rendered = 0;
    records.forEach(r => {
      if (r.latitude == null || r.longitude == null) return;
      const color = capadIucnColor(r.iucn_cat);
      L.marker([r.latitude, r.longitude], { icon: capadIcon(color) })
        .bindPopup(capadPopup(r), { maxWidth: 260 })
        .addTo(group);
      rendered++;
    });
    console.info(`[MapView] CAPAD layer: rendered ${rendered} / ${records.length} records`);
  }, []);

  // ── Re-draw CAPAD when summaries/selection changes ─────────────────────────
  useEffect(() => {
    if (!activeLayers.has('capad') || !capadRecordsRef.current) return;
    drawCapadLayer(capadRecordsRef.current);
  }, [summaries, selectedId, activeLayers, drawCapadLayer]);

  // ── Toggle dataset layers ─────────────────────────────────────────────────
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
      // ── Species ────────────────────────────────────────────────────────────
      if (layerId === 'species') {
        const group = L.layerGroup().addTo(map);
        layerGroupRef.current.set(layerId, group);
        const suppliersWithCoords = suppliers.filter(s => s.coordinates);
        if (suppliersWithCoords.length > 0) {
          const first = suppliersWithCoords[0];
          const records = await speciesApi.byBbox({
            min_lat: first.coordinates!.lat - 2, max_lat: first.coordinates!.lat + 2,
            min_lng: first.coordinates!.lng - 2, max_lng: first.coordinates!.lng + 2,
            limit: 300,
          }).catch(() => []);
          records.forEach(r => {
            if (!r.decimallatitude || !r.decimallongitude) return;
            L.circleMarker([r.decimallatitude, r.decimallongitude], {
              radius: 4, color: '#8b5cf6', fillColor: '#8b5cf6', fillOpacity: 0.5, weight: 1, opacity: 0.7,
            }).bindTooltip(`<b>${r.vernacularname ?? r.scientificname ?? 'Unknown'}</b><br/>${r.stateprovince ?? ''}`)
              .addTo(group);
          });
        }
      }

      // ── CAPAD — fetch real records from capad_protected_areas ─────────────
      if (layerId === 'capad') {
        if (!capadRecordsRef.current) {
          /**
           * Fetch strategy:
           *   1. Collect the unique state codes from supplier risk summaries.
           *      The backend's capad/by-state endpoint returns active records
           *      only, ordered by area desc, up to 500 per state.
           *   2. If no supplier states are known yet, fall back to a general
           *      list (limit 1500, active only) so the layer always renders.
           *   3. Deduplicate by pa_id to avoid duplicate markers when states
           *      overlap or when a supplier has no ibra_code yet.
           */
          const supplierStates = [
            ...new Set(
              summaries
                .map(sm => {
                  // ibra_code is 3 chars; we need the state string from the
                  // supplier's enrichedAddress / region or from CAPAD state.
                  // Fall back to fetching for each state known from suppliers.
                  return null; // resolved below via general list
                })
                .filter(Boolean) as string[]
            ),
          ];

          // Determine states from the supplier objects directly.
          const statesFromSuppliers = [
            ...new Set(
              suppliers
                .map(s => {
                  // Use the state code embedded in the enrichedAddress or region field.
                  // Common patterns: "..., VIC" or "Victoria" etc.
                  const r = s.region ?? '';
                  const match = r.match(/\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\b/i);
                  return match ? match[1].toUpperCase() : null;
                })
                .filter(Boolean) as string[]
            ),
          ];

          let records: CapadRecord[];
          if (statesFromSuppliers.length > 0) {
            // Fetch per-state (up to 500 each, active only)
            const pages = await Promise.all(
              statesFromSuppliers.map(st =>
                capadApi.byState(st, 500).catch(() => [] as CapadRecord[])
              )
            );
            // Also fetch a general page for any areas without a matched state
            const general = await capadApi.list({ is_active: true, limit: 500 }).catch(() => [] as CapadRecord[]);
            const all = [...pages.flat(), ...general];
            // Deduplicate by pa_id
            const seen = new Set<string>();
            records = all.filter(r => {
              const key = r.pa_id ?? String(r.id);
              if (seen.has(key)) return false;
              seen.add(key);
              return true;
            });
          } else {
            // No supplier state info — load a general batch
            const [p1, p2, p3] = await Promise.all([
              capadApi.list({ is_active: true, limit: 500, offset: 0    }).catch(() => [] as CapadRecord[]),
              capadApi.list({ is_active: true, limit: 500, offset: 500  }).catch(() => [] as CapadRecord[]),
              capadApi.list({ is_active: true, limit: 500, offset: 1000 }).catch(() => [] as CapadRecord[]),
            ]);
            records = [...p1, ...p2, ...p3];
          }

          capadRecordsRef.current = records;
          console.info(`[MapView] CAPAD: fetched ${records.length} total records`);
        }
        drawCapadLayer(capadRecordsRef.current);
      }

      // ── KBA ───────────────────────────────────────────────────────────────
      if (layerId === 'kba') {
        const group = L.layerGroup().addTo(map);
        layerGroupRef.current.set(layerId, group);
        suppliers.filter(s => s.coordinates).forEach(s => {
          const sm = summaries.find(r => r.supplier_id === s.id);
          if (!sm || sm.kba_nearby === 0) return;
          L.circle([s.coordinates!.lat, s.coordinates!.lng], {
            radius: 45000, color: '#16a34a', fillColor: '#16a34a', fillOpacity: 0.06, weight: 1.5, dashArray: '4 6',
          }).bindTooltip(`${sm.kba_nearby} Key Biodiversity Areas near ${s.enrichedName ?? s.name}`)
            .addTo(group);
        });
      }

      // ── IBRA ──────────────────────────────────────────────────────────────
      if (layerId === 'ibra') {
        if (!ibraRecordsRef.current) {
          const [page1, page2] = await Promise.all([
            ibraApi.list({ limit: 100, offset: 0   }).catch(() => []),
            ibraApi.list({ limit: 100, offset: 100 }).catch(() => []),
          ]);
          const seen = new Set<string>();
          ibraRecordsRef.current = [...page1, ...page2].filter(r => {
            const key = r.ibra_reg_code ?? r.ibra_reg_name ?? String(r.id);
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
          });
        }
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

      {/*
        ── Bottom-left control stack ──
        Flex column rendered bottom-up:
          [Risk legend]   ← always at the bottom
          [Layers btn]    ← directly above legend
          [Layer panel]   ← expands upward above the Layers btn
      */}
      <div className="absolute bottom-4 left-4 z-[1000] flex flex-col items-start gap-2">

        {/* Layer panel — renders above the button when open */}
        {layerPanelOpen && (
          <div className="w-[260px] bg-white/97 backdrop-blur-sm rounded-xl shadow-lg border border-slate-200/80 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
              <span className="text-xs text-slate-800" style={{ fontWeight: 600 }}>Map Layers</span>
              <button
                onClick={() => setLayerPanelOpen(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              >
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
                    <div key={layer.id}>
                      <div
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

                      {/* CAPAD IUCN colour legend — shown when layer is active */}
                      {layer.id === 'capad' && isActive && (
                        <div className="px-4 pb-2">
                          <button
                            className="text-[10px] text-slate-400 hover:text-slate-600 underline underline-offset-2 mb-1"
                            onClick={e => { e.stopPropagation(); setCapadLegendOpen(v => !v); }}
                          >
                            {capadLegendOpen ? 'Hide' : 'Show'} IUCN colour key
                          </button>
                          {capadLegendOpen && (
                            <div className="grid grid-cols-1 gap-0.5">
                              {CAPAD_LEGEND.map(entry => (
                                <div key={entry.cat} className="flex items-center gap-2">
                                  <div
                                    className="w-3 h-3 rounded-sm shrink-0 border border-white shadow-sm"
                                    style={{ backgroundColor: capadIucnColor(entry.cat) }}
                                  />
                                  <span className="text-[10px] text-slate-600">{entry.label}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}

            <p className="px-4 py-2 text-[10px] text-slate-400 border-t border-slate-100">More datasets coming soon: water stress, minerals</p>
          </div>
        )}

        {/* Layers toggle button */}
        <button
          onClick={() => setLayerPanelOpen(v => !v)}
          className={clsx(
            'flex items-center gap-1.5 px-3 py-2 text-xs rounded-xl shadow-md border transition-colors',
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

        {/* Risk legend — always at the bottom of the stack */}
        <div className="bg-white/95 backdrop-blur-sm rounded-xl p-3 shadow-md border border-slate-200/80">
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

      </div>{/* end bottom-left stack */}
    </div>
  );
}
