import { useEffect, useRef } from 'react';
import L from 'leaflet';
import { Epic2Supplier, getRiskColor } from '../../data/epic2-data';
import 'leaflet/dist/leaflet.css';

interface MapViewProps {
  suppliers: Epic2Supplier[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  hoveredId: string | null;
  onHover: (id: string | null) => void;
}

function createIcon(color: string, size: number, pulse: boolean) {
  return L.divIcon({
    className: '',
    iconSize: [size + 16, size + 16],
    iconAnchor: [(size + 16) / 2, (size + 16) / 2],
    html: `
      <div style="position:relative;width:${size + 16}px;height:${size + 16}px;display:flex;align-items:center;justify-content:center;">
        ${pulse ? `<div style="position:absolute;width:${size + 16}px;height:${size + 16}px;border-radius:50%;background:${color};opacity:0.15;animation:mapPulse 2s ease-in-out infinite;"></div>` : ''}
        <div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2.5px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);position:relative;z-index:2;"></div>
      </div>
    `,
  });
}

export default function MapView({ suppliers, selectedId, onSelect, hoveredId, onHover }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, L.Marker>>(new Map());
  const circlesRef = useRef<Map<string, L.CircleMarker>>(new Map());

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: [-25.5, 134.5],
      zoom: 4,
      zoomControl: false,
      attributionControl: false,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OSM',
    }).addTo(map);

    mapRef.current = map;

    suppliers.forEach(supplier => {
      const colors = getRiskColor(supplier.riskLevel);
      const marker = L.marker([supplier.lat, supplier.lng], {
        icon: createIcon(colors.dot, 14, false),
      }).addTo(map);

      marker.bindTooltip(`
        <div style="font-family:sans-serif;font-size:12px;">
          <div style="display:flex;align-items:center;gap:6px;">
            <span style="width:8px;height:8px;border-radius:50%;background:${colors.dot};display:inline-block;"></span>
            <span style="color:#1e293b;">${supplier.name}</span>
          </div>
          <div style="color:#64748b;margin-top:2px;">Risk Score: ${supplier.riskScore}/100</div>
        </div>
      `, { direction: 'top', offset: [0, -12], className: 'ecotrace-tooltip' });

      marker.on('click', () => onSelect(supplier.id));
      marker.on('mouseover', () => onHover(supplier.id));
      marker.on('mouseout', () => onHover(null));

      markersRef.current.set(supplier.id, marker);

      if (supplier.protectedAreaOverlap > 20) {
        const circle = L.circleMarker([supplier.lat, supplier.lng], {
          radius: supplier.protectedAreaOverlap * 0.8,
          color: colors.dot,
          fillColor: colors.dot,
          fillOpacity: 0.06,
          weight: 1,
          opacity: 0.25,
          dashArray: '4 4',
        }).addTo(map);
        circlesRef.current.set(supplier.id, circle);
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
      markersRef.current.clear();
      circlesRef.current.clear();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    suppliers.forEach(supplier => {
      const marker = markersRef.current.get(supplier.id);
      if (!marker) return;
      const colors = getRiskColor(supplier.riskLevel);
      const isActive = supplier.id === selectedId || supplier.id === hoveredId;
      marker.setIcon(createIcon(colors.dot, isActive ? 18 : 14, isActive));
      if (isActive) marker.setZIndexOffset(1000);
      else marker.setZIndexOffset(0);
    });
  }, [selectedId, hoveredId, suppliers]);

  useEffect(() => {
    if (!selectedId || !mapRef.current) return;
    const supplier = suppliers.find(s => s.id === selectedId);
    if (supplier) {
      mapRef.current.flyTo([supplier.lat, supplier.lng], 8, { duration: 1.2 });
    }
  }, [selectedId, suppliers]);

  return (
    <div className="relative h-full w-full">
      <style>{`
        @keyframes mapPulse {
          0%, 100% { transform: scale(1); opacity: 0.15; }
          50% { transform: scale(1.4); opacity: 0.05; }
        }
        .ecotrace-tooltip {
          background: white !important;
          border: 1px solid #e2e8f0 !important;
          border-radius: 8px !important;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
          padding: 8px 12px !important;
        }
        .ecotrace-tooltip::before {
          border-top-color: #e2e8f0 !important;
        }
      `}</style>
      <div ref={containerRef} className="h-full w-full" />

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur-sm rounded-xl p-3 shadow-lg border border-slate-200/50 z-[1000]">
        <div className="text-[10px] text-slate-500 mb-2 uppercase tracking-wider">Risk Level</div>
        <div className="space-y-1.5">
          {[
            { level: 'critical', label: 'Critical (75-100)' },
            { level: 'high',     label: 'High (60-74)'     },
            { level: 'medium',   label: 'Medium (30-59)'   },
            { level: 'low',      label: 'Low (0-29)'       },
          ].map(item => (
            <div key={item.level} className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: getRiskColor(item.level).dot }} />
              <span className="text-[11px] text-slate-700">{item.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Summary badges */}
      <div className="absolute top-4 right-4 flex gap-2 z-[1000]">
        {[
          { label: 'Critical', count: suppliers.filter(s => s.riskLevel === 'critical').length, color: '#dc2626' },
          { label: 'High',     count: suppliers.filter(s => s.riskLevel === 'high').length,     color: '#d97706' },
        ].map(stat => (
          <div key={stat.label} className="bg-white/90 backdrop-blur-sm rounded-lg px-3 py-2 shadow-lg border border-slate-200/50 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: stat.color }} />
            <span className="text-[11px] text-slate-700">{stat.count} {stat.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
