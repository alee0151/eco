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
  // Enrichment
  enrichedName?: string;
  enrichedAddress?: string;
  abrStatus?: string;
  abnFound?: boolean;
  nameDiscrepancy?: boolean;
  addressDiscrepancy?: boolean;
  // Location
  coordinates?: { lat: number; lng: number };
  resolutionLevel?: "facility" | "regional" | "state" | "unknown";
  inferenceMethod?: string;
  // Source
  fileName?: string;
  fileType?: "pdf" | "image" | "csv";
  warnings?: string[];
}
