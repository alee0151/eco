import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import { Epic2Supplier, getRiskColor } from '../../data/epic2-data';
import { GIS_LAYER_GROUPS, GisSubLayer, GisFeature } from '../../data/gis-layers-data';
import LayerPanel, { ActiveLayers } from './LayerPanel';
import 'leaflet/dist/leaflet.css';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon   from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

interface MapViewProps {
  suppliers: Epic2Supplier[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  hoveredId: string | null;
  onHover: (id: string | null) => void;
}

/* ── Supplier marker icon ───────────────────────────────── */
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

/* ── Popup HTML builder ─────────────────────────────────── */
function featurePopupHtml(sub: GisSubLayer, feat: GisFeature): string {
  const rows = Object.entries(feat.meta)
    .map(([k, v]) => `<div style="display:flex;justify-content:space-between;gap:12px;padding:2px 0;border-bottom:1px solid #f1f5f9">
      <span style="color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:.04em">${k.replace(/_/g, ' ')}</span>
      <span style="font-weight:600;font-size:11px;color:#1e293b">${v}</span>
    </div>`).join('');
  return `<div style="min-width:190px;font-family:system-ui,sans-serif;padding:2px">
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
      <span style="width:10px;height:10px;border-radius:3px;background:${sub.color};flex-shrink:0"></span>
      <p style="font-weight:700;font-size:12px;color:#0f172a;margin:0">${feat.label}</p>
    </div>
    <p style="font-size:10px;color:#94a3b8;margin:0 0 8px">${sub.label}</p>
    <div style="space-y:2px">${rows}</div>
  </div>`;
}

export default function MapView({ suppliers, selectedId, onSelect, hoveredId, onHover }: MapViewProps) {
  const containerRef    = useRef<HTMLDivElement>(null);
  const mapRef          = useRef<L.Map | null>(null);
  const supplierMarkers = useRef<Map<string, L.Marker>>(new Map());
  /* GIS dataset layers: subLayerId → array of Leaflet layers */
  const gisLayers       = useRef<Map<string, L.Layer[]>>(new Map());

  const [activeLayers, setActiveLayers] = useState<ActiveLayers>(new Set());

  /* ── Toggle handler ─────────────────────────────────────── */
  const handleToggle = useCallback((subLayerId: string) => {
    setActiveLayers(prev => {
      const next = new Set(prev);
      if (next.has(subLayerId)) {
        next.delete(subLayerId);
      } else {
        next.add(subLayerId);
      }
      return next;
    });
  }, []);

  /* ── Init map ───────────────────────────────────────────── */
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      center: [-25.5, 134.5],
      zoom: 4,
      zoomControl: false,
      attributionControl: false,
    });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OSM contributors &copy; CARTO',
    }).addTo(map);
    L.control.zoom({ position: 'bottomright' }).addTo(map);
    mapRef.current = map;

    /* Add supplier markers */
    suppliers.forEach(s => {
      const colors = getRiskColor(s.riskLevel);
      const marker = L.marker([s.lat, s.lng], { icon: createIcon(colors.dot, 12, false) }).addTo(map);
      marker.bindPopup(
        `<div style="min-width:180px;font-family:system-ui,sans-serif">
          <p style="font-weight:700;font-size:13px;color:#0f172a">${s.name}</p>
          <p style="font-size:11px;color:#64748b;margin-top:3px">${s.region}</p>
          <p style="font-size:11px;margin-top:6px;font-weight:600;color:${colors.dot}">
            Risk: ${s.riskScore}/100 &bull; ${s.riskLevel.toUpperCase()}
          </p>
        </div>`
      );
      marker.on('click',     () => onSelect(s.id));
      marker.on('mouseover', () => onHover(s.id));
      marker.on('mouseout',  () => onHover(null));
      supplierMarkers.current.set(s.id, marker);
    });

    return () => {
      map.remove();
      mapRef.current = null;
      supplierMarkers.current.clear();
      gisLayers.current.clear();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Sync GIS dataset layers with activeLayers state ─────── */
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    GIS_LAYER_GROUPS.forEach(group => {
      group.subLayers.forEach(sub => {
        const isActive = activeLayers.has(sub.id);
        const existing = gisLayers.current.get(sub.id);

        if (isActive && !existing) {
          /* Build Leaflet layers for this sub-layer */
          const layers: L.Layer[] = [];

          sub.features.forEach(feat => {
            let layer: L.Layer | null = null;

            if (sub.type === 'point' || sub.type === 'heatzone') {
              const radius = sub.type === 'heatzone'
                ? (sub.radius ?? 14) * 8000    // heatzone in metres
                : (sub.radius ?? 8) * 3000;    // point observation in metres

              layer = L.circle([feat.lat, feat.lng], {
                radius,
                color: sub.color,
                fillColor: sub.color,
                fillOpacity: sub.fillOpacity,
                weight: 1.5,
                opacity: sub.strokeOpacity,
              });
            } else if (sub.type === 'polygon' && feat.bounds) {
              layer = L.rectangle(feat.bounds as L.LatLngBoundsExpression, {
                color: sub.color,
                fillColor: sub.color,
                fillOpacity: sub.fillOpacity,
                weight: 1.5,
                opacity: sub.strokeOpacity,
                dashArray: sub.id.startsWith('pr-') ? '5 4' : undefined,
              });
            } else if (sub.type === 'line' && feat.path) {
              layer = L.polyline(feat.path as L.LatLngExpression[], {
                color: sub.color,
                weight: 2.5,
                opacity: sub.strokeOpacity,
                dashArray: '8 4',
              });
            }

            if (layer) {
              layer.bindPopup(featurePopupHtml(sub, feat));
              layer.addTo(map);
              layers.push(layer);
            }
          });

          gisLayers.current.set(sub.id, layers);

        } else if (!isActive && existing) {
          /* Remove layers from map */
          existing.forEach(l => map.removeLayer(l));
          gisLayers.current.delete(sub.id);
        }
      });
    });
  }, [activeLayers]);

  /* ── Update supplier marker icons on select/hover ─────── */
  useEffect(() => {
    suppliers.forEach(s => {
      const marker = supplierMarkers.current.get(s.id);
      if (!marker) return;
      const colors  = getRiskColor(s.riskLevel);
      const active  = s.id === selectedId || s.id === hoveredId;
      marker.setIcon(createIcon(colors.dot, active ? 18 : 12, active));
      marker.setZIndexOffset(active ? 1000 : 0);
    });
  }, [selectedId, hoveredId, suppliers]);

  /* ── Fly to selected supplier ──────────────────────────── */
  useEffect(() => {
    if (!selectedId || !mapRef.current) return;
    const s = suppliers.find(x => x.id === selectedId);
    if (s) {
      mapRef.current.flyTo([s.lat, s.lng], 8, { duration: 1.2 });
      setTimeout(() => supplierMarkers.current.get(s.id)?.openPopup(), 1300);
    }
  }, [selectedId, suppliers]);

  return (
    <div className="relative h-full w-full">
      <style>{`
        @keyframes bioPulse {
          0%,100% { transform:scale(1); opacity:0.18; }
          50%      { transform:scale(1.5); opacity:0.05; }
        }
      `}</style>

      <div ref={containerRef} className="h-full w-full" />

      {/* Layer panel — top left */}
      <LayerPanel activeLayers={activeLayers} onToggle={handleToggle} />

      {/* Risk legend — bottom left */}
      <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-sm rounded-xl p-3 shadow-md border border-slate-200/80 z-[1000]">
        <p className="text-[10px] text-slate-500 mb-2 uppercase tracking-wider" style={{ fontWeight: 600 }}>Supplier Risk</p>
        <div className="space-y-1.5">
          {[
            { level: 'critical', label: 'Critical (75–100)' },
            { level: 'high',     label: 'High (60–74)'      },
            { level: 'medium',   label: 'Medium (30–59)'    },
            { level: 'low',      label: 'Low (0–29)'        },
          ].map(item => (
            <div key={item.level} className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: getRiskColor(item.level).dot }} />
              <span className="text-[11px] text-slate-600">{item.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Top-right summary badges */}
      <div className="absolute top-3 right-3 flex gap-2 z-[1000]">
        {[
          { label: 'Critical', count: suppliers.filter(s => s.riskLevel === 'critical').length, color: '#dc2626' },
          { label: 'High',     count: suppliers.filter(s => s.riskLevel === 'high').length,     color: '#d97706' },
        ].map(stat => (
          <div key={stat.label} className="bg-white/95 backdrop-blur-sm rounded-lg px-3 py-1.5 shadow-sm border border-slate-200/80 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: stat.color }} />
            <span className="text-[11px] text-slate-700" style={{ fontWeight: 600 }}>{stat.count} {stat.label}</span>
          </div>
        ))}
      </div>

      {/* Active layer chips — shows which dataset layers are on */}
      {activeLayers.size > 0 && (
        <div className="absolute bottom-4 right-4 flex flex-wrap gap-1.5 max-w-[220px] justify-end z-[1000]">
          {GIS_LAYER_GROUPS.flatMap(g => g.subLayers)
            .filter(s => activeLayers.has(s.id))
            .map(sub => (
              <div
                key={sub.id}
                className="flex items-center gap-1 bg-white/95 backdrop-blur-sm rounded-full px-2 py-1 border border-slate-200 shadow-sm"
              >
                <span className="w-2 h-2 rounded-sm" style={{ backgroundColor: sub.color }} />
                <span className="text-[10px] text-slate-600" style={{ fontWeight: 500 }}>{sub.label}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
