/**
 * SupplierContext.tsx
 *
 * Session-only supplier state — no database, no API.
 *
 * Suppliers are stored in React state for the lifetime of the browser
 * session. A new tab or page refresh starts with an empty list. Users
 * must re-upload their files each session.
 *
 * All mutations (add, update, remove) are synchronous in-memory operations.
 */

import { createContext, useContext, useState, ReactNode } from "react";
import { Supplier } from "../data/types";

interface SupplierContextType {
  suppliers:      Supplier[];
  loading:        boolean;
  setSuppliers:   (s: Supplier[]) => void;
  addSupplier:    (s: Partial<Supplier>) => void;
  updateSupplier: (id: string, updates: Partial<Supplier>) => void;
  removeSupplier: (id: string) => void;
  clearAll:       () => void;
}

const SupplierContext = createContext<SupplierContextType>(null!);

export function SupplierProvider({ children }: { children: ReactNode }) {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);

  const addSupplier = (data: Partial<Supplier>) => {
    const newSupplier: Supplier = {
      id:              `SUP-${Math.random().toString(36).substr(2, 6).toUpperCase()}`,
      name:            data.name || "",
      abn:             data.abn || "",
      address:         data.address || "",
      commodity:       data.commodity || "",
      region:          data.region || "",
      confidenceScore: data.confidenceScore ?? 0,
      status:          "pending",
      isValidated:     false,
      fileName:        data.fileName,
      fileType:        data.fileType,
      warnings:        data.warnings || [],
      ...data,
    };
    setSuppliers((prev) => [...prev, newSupplier]);
  };

  const updateSupplier = (id: string, updates: Partial<Supplier>) => {
    setSuppliers((prev) =>
      prev.map((s) => (s.id === id ? { ...s, ...updates } : s))
    );
  };

  const removeSupplier = (id: string) => {
    setSuppliers((prev) => prev.filter((s) => s.id !== id));
  };

  const clearAll = () => setSuppliers([]);

  return (
    <SupplierContext.Provider
      value={{
        suppliers,
        loading: false,   // no async load — always ready
        setSuppliers,
        addSupplier,
        updateSupplier,
        removeSupplier,
        clearAll,
      }}
    >
      {children}
    </SupplierContext.Provider>
  );
}

export const useSuppliers = () => useContext(SupplierContext);
