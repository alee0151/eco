import { useEffect, useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useNavigate } from "react-router";
import { useSuppliers } from "../context/SupplierContext";
import { Supplier } from "../data/types";
import { toast } from "sonner";
import clsx from "clsx";
import {
  Search,
  CheckCircle,
  CheckCircle2,
  X,
  Edit2,
  Save,
  Download,
  MapPin,
  FileText,
  ShieldCheck,
  ShieldAlert,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Map as MapIcon,
  List,
  Hash,
  Tag,
  Layers,
  Building2,
  Leaf,
} from "lucide-react";

/* ─── Leaflet icon fix ─────────────────────────────────────────────── */
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

/* ─── State centroids (fallback) ─────────────────────────────────────── */
const STATE_CENTROIDS: Record<string, { lat: number; lng: number }> = {
  NSW: { lat: -32.1656, lng: 147.0000 },
  VIC: { lat: -37.0201, lng: 144.9646 },
  QLD: { lat: -22.5750, lng: 144.0850 },
  WA:  { lat: -25.0419, lng: 121.8989 },
  SA:  { lat: -30.0002, lng: 136.2092 },
  TAS: { lat: -42.0409, lng: 146.5978 },
  ACT: { lat: -35.4735, lng: 149.0124 },
  NT:  { lat: -19.4914, lng: 132.5510 },
};
const AUS_CENTRE = { lat: -25.2744, lng: 133.7751 };

function bestGeoAddress(s: Supplier): string {
  return (
    s.enrichedAddress?.trim() ||
    s.parsedAddress?.formatted?.trim() ||
    s.address?.trim() ||
    s.region?.trim() ||
    ""
  );
}

function bestDisplayAddress(s: Supplier): string {
  return (
    s.enrichedAddress?.trim() ||
    s.parsedAddress?.formatted?.trim() ||
    s.address?.trim() ||
    s.region?.trim() ||
    "No address"
  );
}

async function geocodeAddress(
  address: string
): Promise<{ lat: number; lng: number; level: string }> {
  const query = encodeURIComponent(address + ", Australia");
  const url = `https://nominatim.openstreetmap.org/search?q=${query}&format=json&limit=1&countrycodes=au`;

  const parseResult = (data: unknown): { lat: number; lng: number; level: string } | null => {
    if (Array.isArray(data) && data.length > 0) {
      return {
        lat:   parseFloat(data[0].lat),
        lng:   parseFloat(data[0].lon),
        level: data[0].type === "administrative" ? "state" : "address",
      };
    }
    return null;
  };

  let nominatimFailed = false;

  try {
    const res = await fetch(url, {
      headers: { "Accept-Language": "en", "User-Agent": "eco-supply-chain-app" },
    });

    if (res.status === 429) {
      await new Promise((r) => setTimeout(r, 2000));
      const retry = await fetch(url, { headers: { "Accept-Language": "en", "User-Agent": "eco-supply-chain-app" } });
      if (!retry.ok) {
        nominatimFailed = true;
      } else {
        const retryData = await retry.json();
        const result = parseResult(retryData);
        if (result) return result;
        nominatimFailed = true;
      }
    } else if (!res.ok) {
      nominatimFailed = true;
    } else {
      const data = await res.json();
      const result = parseResult(data);
      if (result) return result;
      nominatimFailed = true;
    }
  } catch {
    nominatimFailed = true;
  }

  if (nominatimFailed) {
    const stateMatch = address.toUpperCase().match(/\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\b/);
    if (stateMatch) return { ...STATE_CENTROIDS[stateMatch[1]], level: "state" };
  }

  return { ...AUS_CENTRE, level: "country" };
}

/* ─── Helpers ───────────────────────────────────────────────────── */
type ConfidenceTier = "all" | "high" | "medium" | "low";

const scoreTier = (score: number): "high" | "medium" | "low" =>
  score >= 80 ? "high" : score >= 50 ? "medium" : "low";

const TIER_COLORS = {
  high:   { dot: "#10b981", ring: "rgba(16,185,129,0.18)",  text: "text-emerald-700", bg: "bg-emerald-50",  border: "border-emerald-200" },
  medium: { dot: "#f59e0b", ring: "rgba(245,158,11,0.18)", text: "text-amber-700",   bg: "bg-amber-50",   border: "border-amber-200"   },
  low:    { dot: "#ef4444", ring: "rgba(239,68,68,0.18)",  text: "text-red-700",     bg: "bg-red-50",     border: "border-red-200"      },
};

function createMarkerIcon(score: number, selected: boolean) {
  const t = TIER_COLORS[scoreTier(score)];
  const size = selected ? 18 : 12;
  return L.divIcon({
    className: "",
    html: `<div style="display:flex;align-items:center;justify-content:center;width:30px;height:30px;position:relative">
      ${selected
        ? `<div style="position:absolute;width:30px;height:30px;border-radius:50%;background:${t.ring};animation:pulse 1.5s infinite"></div>`
        : ""}
      <div style="width:${size}px;height:${size}px;border-radius:50%;background:${t.dot};border:2.5px solid white;box-shadow:0 1px 6px rgba(0,0,0,0.25);position:relative;z-index:1;transition:all .2s"></div>
    </div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -15],
  });
}

/* ─── Score badge ───────────────────────────────────────────────── */
function ScoreBadge({ score }: { score: number }) {
  const t = TIER_COLORS[scoreTier(score)];
  return (
    <div className={clsx("w-11 h-11 rounded-xl border flex flex-col items-center justify-center flex-shrink-0", t.bg, t.border, t.text)}>
      <span className="text-base leading-none" style={{ fontWeight: 700 }}>{score}</span>
      <span className="text-[8px] uppercase tracking-wide" style={{ fontWeight: 700 }}>score</span>
    </div>
  );
}

/* ─── Supplier card ─────────────────────────────────────────────── */
interface CardProps {
  supplier: Supplier;
  selected: boolean;
  expanded: boolean;
  editing: boolean;
  editForm: Partial<Supplier>;
  onSelect: () => void;
  onToggleExpand: () => void;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSaveEdit: () => void;
  onEditFormChange: (updates: Partial<Supplier>) => void;
  onApprove: () => void;
  onReject: () => void;
  onBiodiversity: () => void;
  cardRef: (el: HTMLDivElement | null) => void;
}

function SupplierCard({
  supplier, selected, expanded, editing, editForm,
  onSelect, onToggleExpand, onStartEdit, onCancelEdit, onSaveEdit,
  onEditFormChange, onApprove, onReject, onBiodiversity, cardRef,
}: CardProps) {
  const tier = scoreTier(supplier.confidenceScore || 0);
  const tc = TIER_COLORS[tier];

  const displayName = supplier.enrichedName || supplier.name || "Unknown";
  const displayAddr = bestDisplayAddress(supplier);

  const pa = supplier.parsedAddress;
  const hasStructured = pa && (pa.street || pa.suburb || pa.postcode);

  return (
    <div
      ref={cardRef}
      className={clsx(
        "rounded-xl border overflow-hidden transition-all duration-200",
        selected     ? "border-emerald-300 shadow-md shadow-emerald-100/60"
        : expanded   ? "border-slate-300 shadow-sm"
        : "border-slate-200 hover:border-slate-300",
        supplier.status === "approved" && "ring-1 ring-emerald-200",
        supplier.status === "rejected" && "ring-1 ring-red-100 opacity-60",
        "bg-white"
      )}
    >
      {/* Compact row */}
      <div
        className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-slate-50/60 transition-colors"
        onClick={() => { onSelect(); onToggleExpand(); }}
      >
        <ScoreBadge score={supplier.confidenceScore || 0} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <p className="text-sm text-slate-900 truncate" style={{ fontWeight: 600 }}>{displayName}</p>
            {supplier.status === "approved" && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />}
            {supplier.status === "rejected" && <X className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />}
          </div>
          <p className="text-[11px] text-slate-400 truncate mt-0.5">{displayAddr}</p>
        </div>

        <span
          className={clsx("hidden sm:inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full flex-shrink-0", tc.bg, tc.text)}
          style={{ fontWeight: 600 }}
        >
          {tier === "high" ? <ShieldCheck className="w-3 h-3" /> : tier === "medium" ? <AlertCircle className="w-3 h-3" /> : <ShieldAlert className="w-3 h-3" />}
          {tier.charAt(0).toUpperCase() + tier.slice(1)}
        </span>

        {expanded ? <ChevronUp className="w-4 h-4 text-slate-400 flex-shrink-0" /> : <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />}
      </div>

      {/* Expanded detail */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden border-t border-slate-100"
          >
            <div className="p-4">
              {editing ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { label: "Name",      key: "enrichedName" as const,    value: editForm.enrichedName || editForm.name || "" },
                      { label: "ABN",       key: "abn" as const,             value: editForm.abn || "" },
                      { label: "Address",   key: "enrichedAddress" as const, value: editForm.enrichedAddress || editForm.address || "", span: true },
                      { label: "Commodity", key: "commodity" as const,       value: editForm.commodity || "" },
                    ].map((f) => (
                      <div key={f.key} className={f.span ? "col-span-2" : ""}>
                        <label className="block text-[10px] text-slate-400 mb-1" style={{ fontWeight: 500 }}>{f.label}</label>
                        <input
                          value={f.value}
                          onChange={(e) => onEditFormChange({ [f.key]: e.target.value })}
                          className="w-full px-2.5 py-1.5 text-sm border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 transition-all"
                        />
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-end gap-2 pt-1">
                    <button onClick={onCancelEdit} className="px-3 py-1.5 text-xs border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50 transition-colors" style={{ fontWeight: 500 }}>Cancel</button>
                    <button onClick={onSaveEdit} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors" style={{ fontWeight: 500 }}>
                      <Save className="w-3 h-3" /> Save
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">

                  {/* Meta grid */}
                  <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
                    <DataRow icon={Tag}       label="Commodity"   value={supplier.commodity || "—"} />
                    <DataRow icon={Hash}      label="ABN"         value={supplier.abn || "—"} />
                    <DataRow icon={Building2} label="Entity Type" value={supplier.entityType || "—"} />
                    <DataRow icon={MapPin}    label="Coords"
                      value={
                        supplier.coordinates
                          ? `${supplier.coordinates.lat.toFixed(4)}, ${supplier.coordinates.lng.toFixed(4)}${
                              supplier.resolutionLevel ? ` (${supplier.resolutionLevel})` : ""
                            }`
                          : "Unmapped"
                      }
                    />
                    <DataRow icon={FileText}  label="Source"      value={supplier.fileName || "Upload"} />
                  </div>

                  {/* Structured address breakdown */}
                  {hasStructured && (
                    <div className="bg-violet-50 border border-violet-100 rounded-lg px-3 py-2.5 space-y-1">
                      <p className="text-[10px] text-violet-500 uppercase tracking-wide mb-1.5" style={{ fontWeight: 700 }}>
                        📍 Parsed Address
                      </p>
                      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px]">
                        {pa!.unit     && <><span className="text-violet-400">Unit</span>     <span className="text-slate-700">{pa!.unit}</span></>}
                        {pa!.street   && <><span className="text-violet-400">Street</span>   <span className="text-slate-700">{pa!.street}</span></>}
                        {pa!.suburb   && <><span className="text-violet-400">Suburb</span>   <span className="text-slate-700">{pa!.suburb}</span></>}
                        {pa!.state    && <><span className="text-violet-400">State</span>    <span className="text-slate-700">{pa!.state}</span></>}
                        {pa!.postcode && <><span className="text-violet-400">Postcode</span> <span className="text-slate-700">{pa!.postcode}</span></>}
                        {pa!.country  && <><span className="text-violet-400">Country</span>  <span className="text-slate-700">{pa!.country}</span></>}
                      </div>
                      <p className="text-[10px] text-violet-400 mt-1 truncate">
                        Geocoded as: <span className="text-slate-600">{pa!.formatted}</span>
                      </p>
                    </div>
                  )}

                  {/* ABN status */}
                  <div className="flex items-center justify-between text-[11px] bg-slate-50 rounded-lg px-3 py-2">
                    <span className="text-slate-500">ABN Status</span>
                    <span
                      className={supplier.isValidated
                        ? supplier.abnFound ? "text-emerald-600" : "text-red-500"
                        : "text-slate-400"
                      }
                      style={{ fontWeight: 600 }}
                    >
                      {supplier.isValidated ? (supplier.abnFound ? "✓ Active" : "✗ Not found") : "Pending enrichment"}
                    </span>
                  </div>

                  {/* Confidence bar */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px] text-slate-400">Confidence</span>
                      <span className={clsx("text-xs", TIER_COLORS[scoreTier(supplier.confidenceScore || 0)].text)} style={{ fontWeight: 700 }}>
                        {supplier.confidenceScore || 0}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${supplier.confidenceScore || 0}%` }}
                        transition={{ duration: 0.6, ease: "easeOut" }}
                        className={clsx("h-full rounded-full", {
                          "bg-emerald-500": (supplier.confidenceScore || 0) >= 80,
                          "bg-amber-400":   (supplier.confidenceScore || 0) >= 50 && (supplier.confidenceScore || 0) < 80,
                          "bg-red-400":     (supplier.confidenceScore || 0) < 50,
                        })}
                      />
                    </div>
                  </div>

                  {/* ── Biodiversity GIS button ── */}
                  <button
                    onClick={(e) => { e.stopPropagation(); onBiodiversity(); }}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2.5 text-xs rounded-lg bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-emerald-700 transition-colors"
                    style={{ fontWeight: 600 }}
                  >
                    <Leaf className="w-3.5 h-3.5" />
                    View Biodiversity GIS
                  </button>

                  {/* Approve / Edit / Reject row */}
                  <div className="flex gap-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); onStartEdit(); }}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50 transition-colors"
                      style={{ fontWeight: 500 }}
                    >
                      <Edit2 className="w-3 h-3" /> Edit
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); onApprove(); }}
                      className={clsx(
                        "flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs rounded-lg transition-colors",
                        supplier.status === "approved" ? "bg-emerald-700 text-white" : "bg-emerald-600 hover:bg-emerald-700 text-white"
                      )}
                      style={{ fontWeight: 500 }}
                    >
                      <CheckCircle className="w-3 h-3" />
                      {supplier.status === "approved" ? "Approved" : "Approve"}
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); onReject(); }}
                      className={clsx(
                        "flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs rounded-lg transition-colors",
                        supplier.status === "rejected" ? "bg-red-600 text-white" : "border border-red-200 text-red-500 hover:bg-red-50"
                      )}
                      style={{ fontWeight: 500 }}
                    >
                      <X className="w-3 h-3" />
                      {supplier.status === "rejected" ? "Rejected" : "Reject"}
                    </button>
                  </div>

                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function DataRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div>
      <span className="flex items-center gap-1 text-[10px] text-slate-400 mb-0.5" style={{ fontWeight: 500 }}>
        <Icon className="w-3 h-3" /> {label}
      </span>
      <p className="text-xs text-slate-700 truncate" style={{ fontWeight: 500 }}>{value}</p>
    </div>
  );
}

/* ─── Main page ───────────────────────────────────────────────── */
export function MapPage() {
  const { suppliers, updateSupplier } = useSuppliers();
  const navigate = useNavigate();

  const [geocoding, setGeocoding] = useState(true);
  const [geocodeProgress, setGeocodeProgress] = useState({ done: 0, total: 0 });
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<Map<string, L.Marker>>(new Map());
  const onMarkerClickRef = useRef<(id: string) => void>(() => {});
  const geocodedIds = useRef<Set<string>>(new Set());

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<Supplier>>({});
  const [searchTerm, setSearchTerm] = useState("");
  const [filter, setFilter] = useState<ConfidenceTier>("all");
  const [mobileTab, setMobileTab] = useState<"map" | "list">("list");

  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  onMarkerClickRef.current = useCallback((id: string) => {
    setSelectedId(id);
    setExpandedId(id);
    const el = cardRefs.current.get(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, []);

  /* ── Init map ── */
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;
    const map = L.map(mapContainerRef.current).setView([-25.2744, 133.7751], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  /* ── Geocode loop ── */
  const supplierKey = suppliers.map((s) => s.id).join(",");

  useEffect(() => {
    const currentIds = new Set(suppliers.map((s) => s.id));
    for (const id of geocodedIds.current) {
      if (!currentIds.has(id)) geocodedIds.current.delete(id);
    }

    const needsGeocode = suppliers.filter(
      (s) => !s.coordinates && !geocodedIds.current.has(s.id)
    );

    if (needsGeocode.length === 0) { setGeocoding(false); return; }

    setGeocoding(true);
    setGeocodeProgress({ done: 0, total: needsGeocode.length });

    let cancelled = false;

    const geocodeAll = async () => {
      for (let i = 0; i < needsGeocode.length; i++) {
        if (cancelled) break;
        const s = needsGeocode[i];
        geocodedIds.current.add(s.id);

        const address = bestGeoAddress(s);
        const { lat, lng, level } = await geocodeAddress(address);

        updateSupplier(s.id, {
          coordinates:     { lat, lng },
          resolutionLevel: level === "address" ? "facility" : level === "state" ? "state" : "unknown",
          inferenceMethod: level === "address"
            ? (s.parsedAddress?.formatted ? "parsed+Nominatim" : "Nominatim OSM")
            : level === "state" ? "state centroid fallback"
            : "country centroid fallback",
        });

        setGeocodeProgress({ done: i + 1, total: needsGeocode.length });
        if (i < needsGeocode.length - 1) await new Promise((r) => setTimeout(r, 1100));
      }
      if (!cancelled) setGeocoding(false);
    };

    geocodeAll();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [supplierKey]);

  /* ── Render markers ── */
  useEffect(() => {
    if (geocoding || !mapRef.current) return;

    markersRef.current.forEach((marker, id) => {
      if (!suppliers.find((s) => s.id === id)) {
        marker.remove();
        markersRef.current.delete(id);
      }
    });

    const bounds: L.LatLngExpression[] = [];

    suppliers.forEach((s) => {
      if (!s.coordinates) return;
      const pos: L.LatLngExpression = [s.coordinates.lat, s.coordinates.lng];
      bounds.push(pos);

      const isSelected = s.id === selectedId;
      const icon = createMarkerIcon(s.confidenceScore || 0, isSelected);
      const popupAddr = bestDisplayAddress(s);
      const pa = s.parsedAddress;
      const structuredLine = pa?.suburb
        ? `<p style="font-size:10px;color:#7c3aed;margin-top:2px">📍 ${[pa.street, pa.suburb, pa.state, pa.postcode].filter(Boolean).join(" · ")}</p>`
        : "";

      const popupHtml = `<div style="min-width:200px">
        <p style="font-weight:700;font-size:13px;color:#0f172a">${s.enrichedName || s.name}</p>
        <p style="font-size:11px;color:#64748b;margin-top:3px">${popupAddr}</p>
        ${structuredLine}
        <p style="font-size:11px;margin-top:6px;font-weight:600;color:${
          (s.confidenceScore || 0) >= 80 ? "#059669" :
          (s.confidenceScore || 0) >= 50 ? "#d97706" : "#dc2626"
        }">Confidence: ${s.confidenceScore || 0}%</p>
        <p style="font-size:10px;color:#94a3b8;margin-top:2px">${
          s.resolutionLevel ? `Precision: ${s.resolutionLevel}` : ""
        }${s.inferenceMethod ? ` · ${s.inferenceMethod}` : ""}</p>
      </div>`;

      const existing = markersRef.current.get(s.id);
      if (existing) {
        existing.setIcon(icon);
        existing.setPopupContent(popupHtml);
      } else {
        const marker = L.marker(pos, { icon }).addTo(mapRef.current!);
        marker.bindPopup(popupHtml);
        marker.on("click", () => onMarkerClickRef.current(s.id));
        markersRef.current.set(s.id, marker);
      }
    });

    if (bounds.length > 0 && !selectedId) {
      mapRef.current.fitBounds(L.latLngBounds(bounds), { padding: [50, 50] });
    }
  }, [geocoding, suppliers, selectedId]);

  /* ── Pan to selected ── */
  useEffect(() => {
    if (!selectedId || !mapRef.current) return;
    const s = suppliers.find((s) => s.id === selectedId);
    if (s?.coordinates) {
      mapRef.current.setView([s.coordinates.lat, s.coordinates.lng], 10, { animate: true });
      const marker = markersRef.current.get(s.id);
      setTimeout(() => marker?.openPopup(), 400);
    }
  }, [selectedId, suppliers]);

  /* ── Export CSV ── */
  const handleExport = useCallback(() => {
    if (suppliers.length === 0) { toast.error("No suppliers to export."); return; }
    const headers = [
      "Name", "ABN", "Entity Type",
      "Parsed Street", "Parsed Suburb", "Parsed State", "Parsed Postcode",
      "Formatted Address",
      "Latitude", "Longitude", "Resolution", "Inference Method",
      "Confidence", "Status", "Commodity",
    ];
    const rows = suppliers.map((s) => [
      s.enrichedName || s.name || "",
      s.abn || "",
      s.entityType || "",
      s.parsedAddress?.street   || "",
      s.parsedAddress?.suburb   || "",
      s.parsedAddress?.state    || "",
      s.parsedAddress?.postcode || "",
      bestDisplayAddress(s),
      s.coordinates?.lat?.toFixed(6) ?? "",
      s.coordinates?.lng?.toFixed(6) ?? "",
      s.resolutionLevel || "",
      s.inferenceMethod || "",
      s.confidenceScore ?? "",
      s.status || "",
      s.commodity || "",
    ].map((v) => `"${String(v).replace(/"/g, '""')}"`).join(","));
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `eco-suppliers-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Exported ${suppliers.length} suppliers to CSV`);
  }, [suppliers]);

  /* ── Handlers ── */
  const handleSelect       = (id: string) => { setSelectedId((p) => p === id ? null : id); setMobileTab("map"); };
  const handleToggleExpand = (id: string) => setExpandedId((p) => p === id ? null : id);
  const handleStartEdit    = (s: Supplier) => { setEditingId(s.id); setEditForm({ ...s }); };
  const handleSaveEdit     = (id: string) => { updateSupplier(id, editForm); setEditingId(null); toast.success("Changes saved"); };
  const handleApprove      = (id: string) => { updateSupplier(id, { status: "approved" }); toast.success("Supplier approved"); };
  const handleReject       = (id: string) => { updateSupplier(id, { status: "rejected" }); toast.success("Supplier rejected", { description: "Marked for review." }); };
  const handleBiodiversity = (id: string) => navigate(`/biodiversity?supplier=${id}`);

  /* ── Filtered list ── */
  const filtered = suppliers.filter((s) => {
    const term = searchTerm.toLowerCase();
    const matchText =
      (s.name || "").toLowerCase().includes(term) ||
      (s.enrichedName || "").toLowerCase().includes(term) ||
      (s.address || "").toLowerCase().includes(term) ||
      (s.parsedAddress?.formatted || "").toLowerCase().includes(term) ||
      (s.commodity || "").toLowerCase().includes(term);
    const matchTier = filter === "all" || scoreTier(s.confidenceScore || 0) === filter;
    return matchText && matchTier;
  });

  /* ── Stats ── */
  const approvedCount = suppliers.filter((s) => s.status === "approved").length;
  const rejectedCount = suppliers.filter((s) => s.status === "rejected").length;
  const pendingCount  = suppliers.filter((s) => s.status !== "approved" && s.status !== "rejected").length;
  const highCount     = suppliers.filter((s) => scoreTier(s.confidenceScore || 0) === "high").length;
  const mediumCount   = suppliers.filter((s) => scoreTier(s.confidenceScore || 0) === "medium").length;
  const lowCount      = suppliers.filter((s) => scoreTier(s.confidenceScore || 0) === "low").length;

  /* ─── Render ─── */
  return (
    <div className="flex flex-col h-[calc(100vh-7.5rem)] gap-4">

      {/* Header */}
      <div className="flex items-start justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl text-slate-900" style={{ fontWeight: 700 }}>Map &amp; Review</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Addresses parsed by LLM · validated via ABR · geocoded via G-NAF
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2">
            {[
              { label: "Pending",  value: pendingCount,  cls: "bg-slate-100 text-slate-600" },
              { label: "Approved", value: approvedCount, cls: "bg-emerald-50 text-emerald-700" },
              { label: "Rejected", value: rejectedCount, cls: "bg-red-50 text-red-600" },
            ].map(({ label, value, cls }) => (
              <span key={label} className={clsx("text-xs px-2.5 py-1 rounded-full", cls)} style={{ fontWeight: 600 }}>
                {value} {label}
              </span>
            ))}
          </div>
          <button
            onClick={handleExport}
            className="flex items-center gap-1.5 px-3 py-2 text-xs border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-lg transition-colors"
            style={{ fontWeight: 500 }}
          >
            <Download className="w-3.5 h-3.5" /> Export CSV
          </button>
        </div>
      </div>

      {/* Mobile tab */}
      <div className="flex md:hidden items-center gap-1 bg-slate-100 rounded-lg p-1 self-start flex-shrink-0">
        {([{ key: "list", icon: List, label: "Review" }, { key: "map", icon: MapIcon, label: "Map" }] as const).map((t) => (
          <button
            key={t.key}
            onClick={() => setMobileTab(t.key)}
            className={clsx("flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-all",
              mobileTab === t.key ? "bg-white text-slate-800 shadow-sm" : "text-slate-500"
            )}
            style={{ fontWeight: mobileTab === t.key ? 600 : 500 }}
          >
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>

      {/* Split view */}
      <div className="flex-1 flex gap-4 min-h-0">

        {/* Map panel */}
        <div className={clsx(
          "md:flex flex-col rounded-2xl overflow-hidden border border-slate-200 shadow-sm flex-[55] min-h-0 relative",
          mobileTab === "map" ? "flex" : "hidden md:flex"
        )}>
          {geocoding && (
            <div className="absolute inset-0 z-[1000] bg-white/80 backdrop-blur-sm flex flex-col items-center justify-center gap-3 rounded-2xl">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="w-7 h-7 border-[3px] border-emerald-500 border-t-transparent rounded-full"
              />
              <p className="text-sm text-slate-600" style={{ fontWeight: 500 }}>Geocoding suppliers…</p>
              {geocodeProgress.total > 0 && (
                <div className="flex flex-col items-center gap-1.5">
                  <p className="text-xs text-slate-400">{geocodeProgress.done} / {geocodeProgress.total} addresses resolved</p>
                  <div className="w-40 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                    <motion.div
                      animate={{ width: `${(geocodeProgress.done / geocodeProgress.total) * 100}%` }}
                      className="h-full bg-emerald-500 rounded-full"
                    />
                  </div>
                </div>
              )}
            </div>
          )}
          <div ref={mapContainerRef} className="w-full h-full" />
        </div>

        {/* Review panel */}
        <div className={clsx(
          "md:flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm flex-[45] min-h-0",
          mobileTab === "list" ? "flex" : "hidden md:flex"
        )}>
          <div className="px-4 pt-4 pb-3 border-b border-slate-100 flex-shrink-0 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-600" />
                <span className="text-sm text-slate-800" style={{ fontWeight: 600 }}>Suppliers</span>
                <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full" style={{ fontWeight: 600 }}>{suppliers.length}</span>
              </div>
            </div>
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              <input
                type="text"
                placeholder="Search name, address, suburb…"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-8 pr-3 py-2 text-sm border border-slate-200 rounded-lg bg-slate-50 focus:bg-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 outline-none transition-all"
              />
            </div>
            <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-0.5">
              {([
                { key: "all",    label: "All",  count: suppliers.length },
                { key: "high",   label: "High", count: highCount   },
                { key: "medium", label: "Med",  count: mediumCount },
                { key: "low",    label: "Low",  count: lowCount    },
              ] as { key: ConfidenceTier; label: string; count: number }[]).map((f) => (
                <button
                  key={f.key}
                  onClick={() => setFilter(f.key)}
                  className={clsx(
                    "flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-md text-[11px] transition-all",
                    filter === f.key ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"
                  )}
                  style={{ fontWeight: filter === f.key ? 600 : 500 }}
                >
                  {f.label}
                  <span className={clsx("text-[9px] px-1 rounded", filter === f.key ? "bg-slate-100 text-slate-600" : "bg-transparent")} style={{ fontWeight: 700 }}>
                    {f.count}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            <AnimatePresence>
              {filtered.map((s, i) => (
                <motion.div key={s.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}>
                  <SupplierCard
                    supplier={s}
                    selected={selectedId === s.id}
                    expanded={expandedId === s.id}
                    editing={editingId === s.id}
                    editForm={editForm}
                    onSelect={() => handleSelect(s.id)}
                    onToggleExpand={() => handleToggleExpand(s.id)}
                    onStartEdit={() => handleStartEdit(s)}
                    onCancelEdit={() => setEditingId(null)}
                    onSaveEdit={() => handleSaveEdit(s.id)}
                    onEditFormChange={(u) => setEditForm((prev) => ({ ...prev, ...u }))}
                    onApprove={() => handleApprove(s.id)}
                    onReject={() => handleReject(s.id)}
                    onBiodiversity={() => handleBiodiversity(s.id)}
                    cardRef={(el) => { if (el) cardRefs.current.set(s.id, el); else cardRefs.current.delete(s.id); }}
                  />
                </motion.div>
              ))}
            </AnimatePresence>
            {filtered.length === 0 && (
              <div className="text-center py-16">
                <Search className="w-8 h-8 text-slate-200 mx-auto mb-3" />
                <p className="text-sm text-slate-400">No suppliers match this filter.</p>
              </div>
            )}
          </div>

          {(approvedCount > 0 || rejectedCount > 0) && (
            <div className="border-t border-slate-100 px-4 py-3 flex-shrink-0 flex items-center justify-between">
              <div className="flex items-center gap-3">
                {approvedCount > 0 && <span className="flex items-center gap-1 text-[11px] text-emerald-600" style={{ fontWeight: 600 }}><CheckCircle2 className="w-3.5 h-3.5" /> {approvedCount} approved</span>}
                {rejectedCount > 0 && <span className="flex items-center gap-1 text-[11px] text-red-500" style={{ fontWeight: 600 }}><X className="w-3.5 h-3.5" /> {rejectedCount} rejected</span>}
              </div>
              <span className="text-[11px] text-slate-400">{pendingCount} remaining</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
