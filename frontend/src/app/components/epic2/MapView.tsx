import { useEffect, useRef } from 'react';
import L from 'leaflet';
import { Epic2Supplier, getRiskColor } from '../../data/epic2-data';
import 'leaflet/dist/leaflet.css';

/* Fix Leaflet default icon paths broken by bundlers */
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

/* ── Icon factory — mirrors MapPage.tsx createMarkerIcon ── */
function createIcon(color: string, size: number, pulse: boolean) {
  return L.divIcon({
    className: '',
    html: `<div style="display:flex;align-items:center;justify-content:center;width:30px;height:30px;position:relative">
      ${pulse
        ? `<div style="position:absolute;width:30px;height:30px;border-radius:50%;background:${color};opacity:0.18;animation:bioPulse 1.5s ease-in-out infinite;"></div>`
        : ''}
      <div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2.5px solid white;box-shadow:0 1px 6px rgba(0,0,0,0.25);position:relative;z-index:1;"></div>
    </div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

export default function MapView({ suppliers, selectedId, onSelect, hoveredId, onHover }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef       = useRef<L.Map | null>(null);
  const markersRef   = useRef<Map<string, L.Marker>>(new Map());
  const circlesRef   = useRef<Map<string, L.CircleMarker>>(new Map());

  /* Init map — same tile & zoom as MapPage */
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: [-25.5, 134.5],
      zoom: 4,
      zoomControl: false,
      attributionControl: false,
    });

    /* Same tile provider as MapPage (OpenStreetMap via Carto Voyager) */
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OSM contributors &copy; CARTO',
    }).addTo(map);

    mapRef.current = map;

    suppliers.forEach(s => {
      const colors = getRiskColor(s.riskLevel);
      const marker = L.marker([s.lat, s.lng], { icon: createIcon(colors.dot, 12, false) }).addTo(map);

      marker.bindPopup(
        `<div style="min-width:180px;font-family:sans-serif">
          <p style="font-weight:700;font-size:13px;color:#0f172a">${s.name}</p>
          <p style="font-size:11px;color:#64748b;margin-top:3px">${s.region}</p>
          <p style="font-size:11px;margin-top:6px;font-weight:600;color:${colors.dot}">
            Risk Score: ${s.riskScore}/100 &bull; ${s.riskLevel.toUpperCase()}
          </p>
        </div>`
      );

      marker.on('click',     () => onSelect(s.id));
      marker.on('mouseover', () => onHover(s.id));
      marker.on('mouseout',  () => onHover(null));
      markersRef.current.set(s.id, marker);

      if (s.protectedAreaOverlap > 20) {
        const circle = L.circleMarker([s.lat, s.lng], {
          radius: s.protectedAreaOverlap * 0.8,
          color: colors.dot,
          fillColor: colors.dot,
          fillOpacity: 0.06,
          weight: 1,
          opacity: 0.25,
          dashArray: '4 4',
        }).addTo(map);
        circlesRef.current.set(s.id, circle);
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
      markersRef.current.clear();
      circlesRef.current.clear();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* Update icons on select/hover */
  useEffect(() => {
    suppliers.forEach(s => {
      const marker = markersRef.current.get(s.id);
      if (!marker) return;
      const colors  = getRiskColor(s.riskLevel);
      const isActive = s.id === selectedId || s.id === hoveredId;
      marker.setIcon(createIcon(colors.dot, isActive ? 18 : 12, isActive));
      marker.setZIndexOffset(isActive ? 1000 : 0);
    });
  }, [selectedId, hoveredId, suppliers]);

  /* Fly to selected */
  useEffect(() => {
    if (!selectedId || !mapRef.current) return;
    const s = suppliers.find(x => x.id === selectedId);
    if (s) {
      mapRef.current.flyTo([s.lat, s.lng], 8, { duration: 1.2 });
      setTimeout(() => markersRef.current.get(s.id)?.openPopup(), 1300);
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

      {/* Risk legend — same card style as MapPage popups */}
      <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-sm rounded-xl p-3 shadow-md border border-slate-200/80 z-[1000]">
        <p className="text-[10px] text-slate-500 mb-2 uppercase tracking-wider" style={{ fontWeight: 600 }}>Risk Level</p>
        <div className="space-y-1.5">
          {[
            { level: 'critical', label: 'Critical (75–100)' },
            { level: 'high',     label: 'High (60–74)'     },
            { level: 'medium',   label: 'Medium (30–59)'   },
            { level: 'low',      label: 'Low (0–29)'       },
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
          { label: 'Critical', count: suppliers.filter(s => s.riskLevel === 'critical').length, color: '#ef4444' },
          { label: 'High',     count: suppliers.filter(s => s.riskLevel === 'high').length,     color: '#f59e0b' },
        ].map(stat => (
          <div key={stat.label} className="bg-white/95 backdrop-blur-sm rounded-lg px-3 py-1.5 shadow-sm border border-slate-200/80 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: stat.color }} />
            <span className="text-[11px] text-slate-700" style={{ fontWeight: 600 }}>{stat.count} {stat.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
