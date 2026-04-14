/**
 * SupplierContext.tsx
 *
 * Global supplier state — seeded from the live backend API on first load.
 * Falls back to empty array if backend is unreachable (dev fallback).
 * All mutations (add, update, remove) mirror to the DB via the API.
 */

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { Supplier } from "../data/types";
import { suppliersApi, SupplierRecord } from "../lib/api";

// Map API snake_case shape → frontend camelCase Supplier type
function mapApiSupplier(r: SupplierRecord): Supplier {
  return {
    id:                r.id,
    name:              r.name,
    abn:               r.abn ?? "",
    address:           r.address ?? "",
    commodity:         r.commodity ?? "",
    region:            r.region ?? "",
    confidenceScore:   r.confidence_score ?? 0,
    status:            r.status,
    isValidated:       r.is_validated,
    enrichedName:      r.enriched_name ?? undefined,
    enrichedAddress:   r.enriched_address ?? undefined,
    abrStatus:         r.abr_status ?? undefined,
    abnFound:          r.abn_found ?? undefined,
    nameDiscrepancy:   r.name_discrepancy ?? undefined,
    addressDiscrepancy: r.address_discrepancy ?? undefined,
    coordinates:       (r.lat != null && r.lng != null)
                         ? { lat: r.lat, lng: r.lng }
                         : undefined,
    resolutionLevel:   (r.resolution_level as Supplier["resolutionLevel"]) ?? undefined,
    inferenceMethod:   r.inference_method ?? undefined,
    fileName:          r.file_name ?? undefined,
    fileType:          (r.file_type as Supplier["fileType"]) ?? undefined,
    warnings:          r.warnings ? r.warnings.split("|") : [],
  };
}

// Map frontend Supplier → API shape for PATCH/POST
function mapToApi(s: Partial<Supplier>): Partial<SupplierRecord> {
  const out: Partial<SupplierRecord> = {};
  if (s.id                !== undefined) out.id                = s.id;
  if (s.name              !== undefined) out.name              = s.name;
  if (s.abn               !== undefined) out.abn               = s.abn;
  if (s.address           !== undefined) out.address           = s.address;
  if (s.commodity         !== undefined) out.commodity         = s.commodity;
  if (s.region            !== undefined) out.region            = s.region;
  if (s.confidenceScore   !== undefined) out.confidence_score  = s.confidenceScore;
  if (s.status            !== undefined) out.status            = s.status;
  if (s.isValidated       !== undefined) out.is_validated      = s.isValidated;
  if (s.enrichedName      !== undefined) out.enriched_name     = s.enrichedName;
  if (s.enrichedAddress   !== undefined) out.enriched_address  = s.enrichedAddress;
  if (s.abrStatus         !== undefined) out.abr_status        = s.abrStatus;
  if (s.abnFound          !== undefined) out.abn_found         = s.abnFound;
  if (s.nameDiscrepancy   !== undefined) out.name_discrepancy  = s.nameDiscrepancy;
  if (s.addressDiscrepancy !== undefined) out.address_discrepancy = s.addressDiscrepancy;
  if (s.coordinates       !== undefined) {
    out.lat = s.coordinates?.lat;
    out.lng = s.coordinates?.lng;
  }
  if (s.resolutionLevel   !== undefined) out.resolution_level  = s.resolutionLevel;
  if (s.inferenceMethod   !== undefined) out.inference_method  = s.inferenceMethod;
  if (s.fileName          !== undefined) out.file_name         = s.fileName;
  if (s.fileType          !== undefined) out.file_type         = s.fileType;
  if (s.warnings          !== undefined) out.warnings          = (s.warnings ?? []).join("|");
  return out;
}

interface SupplierContextType {
  suppliers:     Supplier[];
  loading:       boolean;
  error:         string | null;
  setSuppliers:  (s: Supplier[]) => void;
  addSupplier:   (s: Partial<Supplier>) => Promise<void>;
  updateSupplier:(id: string, updates: Partial<Supplier>) => Promise<void>;
  removeSupplier:(id: string) => Promise<void>;
  reload:        () => Promise<void>;
}

const SupplierContext = createContext<SupplierContextType>(null!);

export function SupplierProvider({ children }: { children: ReactNode }) {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await suppliersApi.list();
      setSuppliers(data.map(mapApiSupplier));
    } catch (e) {
      console.error("[SupplierContext] Could not load suppliers from API", e);
      setError("Could not connect to the backend. Is the server running on port 8000?");
      // Keep existing state so UI doesn't break
    } finally {
      setLoading(false);
    }
  };

  // Load once on mount
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const addSupplier = async (data: Partial<Supplier>) => {
    const newSupplier: Supplier = {
      id:             `SUP-${Math.random().toString(36).substr(2, 6).toUpperCase()}`,
      name:           data.name || "",
      abn:            data.abn || "",
      address:        data.address || "",
      commodity:      data.commodity || "",
      region:         data.region || "",
      confidenceScore: data.confidenceScore ?? 0,
      status:         "pending",
      isValidated:    false,
      fileName:       data.fileName,
      fileType:       data.fileType,
      warnings:       data.warnings || [],
      ...data,
    };
    // Optimistic update
    setSuppliers((prev) => [...prev, newSupplier]);
    try {
      const created = await suppliersApi.create(mapToApi(newSupplier));
      // Replace optimistic record with server record (gets DB-assigned id etc.)
      setSuppliers((prev) =>
        prev.map((s) => (s.id === newSupplier.id ? mapApiSupplier(created) : s))
      );
    } catch (e) {
      console.error("[SupplierContext] addSupplier failed", e);
    }
  };

  const updateSupplier = async (id: string, updates: Partial<Supplier>) => {
    // Optimistic update first (so UI feels instant)
    setSuppliers((prev) =>
      prev.map((s) => (s.id === id ? { ...s, ...updates } : s))
    );
    try {
      await suppliersApi.update(id, mapToApi(updates));
    } catch (e) {
      console.error("[SupplierContext] updateSupplier failed", e);
      // On failure reload from server to get back to truth
      await load();
    }
  };

  const removeSupplier = async (id: string) => {
    setSuppliers((prev) => prev.filter((s) => s.id !== id));
    try {
      await suppliersApi.delete(id);
    } catch (e) {
      console.error("[SupplierContext] removeSupplier failed", e);
      await load();
    }
  };

  return (
    <SupplierContext.Provider
      value={{
        suppliers, loading, error,
        setSuppliers,
        addSupplier,
        updateSupplier,
        removeSupplier,
        reload: load,
      }}
    >
      {children}
    </SupplierContext.Provider>
  );
}

export const useSuppliers = () => useContext(SupplierContext);
