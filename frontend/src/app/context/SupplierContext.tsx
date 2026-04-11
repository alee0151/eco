import { createContext, useContext, useState, ReactNode } from "react";
import { Supplier } from "../data/types";
import { mockSuppliers } from "../data/mock-suppliers";

interface SupplierContextType {
  suppliers: Supplier[];
  setSuppliers: (s: Supplier[]) => void;
  addSupplier: (s: Partial<Supplier>) => void;
  updateSupplier: (id: string, updates: Partial<Supplier>) => void;
  removeSupplier: (id: string) => void;
}

const SupplierContext = createContext<SupplierContextType>(null!);

export function SupplierProvider({ children }: { children: ReactNode }) {
  const [suppliers, setSuppliers] = useState<Supplier[]>(mockSuppliers);

  const addSupplier = (data: Partial<Supplier>) => {
    const newSupplier: Supplier = {
      id: `SUP-${Math.random().toString(36).substr(2, 6).toUpperCase()}`,
      name: data.name || "",
      abn: data.abn || "",
      address: data.address || "",
      commodity: data.commodity || "",
      region: data.region || "",
      confidenceScore: data.confidenceScore ?? 0,
      status: "pending",
      isValidated: false,
      fileName: data.fileName,
      fileType: data.fileType,
      warnings: data.warnings || [],
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

  return (
    <SupplierContext.Provider
      value={{ suppliers, setSuppliers, addSupplier, updateSupplier, removeSupplier }}
    >
      {children}
    </SupplierContext.Provider>
  );
}

export const useSuppliers = () => useContext(SupplierContext);