/**
 * types.ts — Canonical frontend Supplier type.
 * Matches SupplierRecord from the DB (via backend schemas.py).
 */

export interface Supplier {
  id: string;
  name: string;
  abn: string;
  address: string;
  commodity: string;
  region: string;
  confidenceScore: number;
  status: "pending" | "validated" | "approved" | "rejected";
  isValidated: boolean;
  // Enrichment (set after ABR validation)
  enrichedName?: string;
  enrichedAddress?: string;
  abrStatus?: string;
  abnFound?: boolean;
  nameDiscrepancy?: boolean;
  addressDiscrepancy?: boolean;
  // Location (set after geocoding)
  coordinates?: { lat: number; lng: number };
  resolutionLevel?: "facility" | "regional" | "state" | "unknown";
  inferenceMethod?: string;
  // Source file info
  fileName?: string;
  fileType?: "pdf" | "image" | "csv";
  warnings?: string[];
}
