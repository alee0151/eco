/**
 * api.ts
 *
 * Centralised API client for the eco backend.
 * All components should import from here — never use fetch() directly.
 *
 * Base URL resolves to:
 *   - Dev  : http://localhost:8000  (set NEXT_PUBLIC_API_URL in .env.local)
 *   - Prod : relative /api  (served by the same origin via reverse proxy)
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// ── Types (mirror backend schemas) ─────────────────────────────────────────

export interface SupplierAPI {
  id:                  string;
  name:                string;
  abn:                 string | null;
  address:             string | null;
  commodity:           string | null;
  region:              string | null;
  confidence_score:    number | null;
  status:              'pending' | 'validated' | 'approved' | 'rejected';
  is_validated:        boolean;
  enriched_name:       string | null;
  enriched_address:    string | null;
  abr_status:          string | null;
  abn_found:           boolean | null;
  name_discrepancy:    boolean | null;
  address_discrepancy: boolean | null;
  lat:                 number | null;
  lng:                 number | null;
  resolution_level:    string | null;
  inference_method:    string | null;
  file_name:           string | null;
  file_type:           string | null;
  warnings:            string | null;  // JSON string — parse with JSON.parse()
}

export interface ThreatenedSpeciesAPI {
  id:           number;
  name:         string;
  species_type: string | null;
  status:       string | null;
}

export interface BiodiversitySupplierAPI {
  id:                       string;
  name:                     string;
  region:                   string | null;
  lat:                      number | null;
  lng:                      number | null;
  risk_score:               number | null;
  risk_level:               string | null;
  protected_area_overlap:   number | null;
  threatened_species_count: number | null;
  vegetation_condition:     number | null;
  deforestation_rate:       number | null;
  water_stress_index:       number | null;
  carbon_stock:             number | null;
  last_assessment:          string | null;
  industry:                 string | null;
  notes:                    string | null;
  threatened_species:       ThreatenedSpeciesAPI[];
}

// ── Epic 1 — Suppliers ──────────────────────────────────────────────────────

export const suppliersApi = {
  list:   ()                       => request<SupplierAPI[]>('/api/suppliers'),
  get:    (id: string)             => request<SupplierAPI>(`/api/suppliers/${id}`),
  create: (body: Partial<SupplierAPI>) =>
    request<SupplierAPI>('/api/suppliers', { method: 'POST', body: JSON.stringify(body) }),
  update: (id: string, body: Partial<SupplierAPI>) =>
    request<SupplierAPI>(`/api/suppliers/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (id: string) =>
    request<void>(`/api/suppliers/${id}`, { method: 'DELETE' }),
};

// ── Epic 2 — Biodiversity ───────────────────────────────────────────────────

export const biodiversityApi = {
  list:   ()                              => request<BiodiversitySupplierAPI[]>('/api/biodiversity/suppliers'),
  get:    (id: string)                    => request<BiodiversitySupplierAPI>(`/api/biodiversity/suppliers/${id}`),
  create: (body: Partial<BiodiversitySupplierAPI>) =>
    request<BiodiversitySupplierAPI>('/api/biodiversity/suppliers', { method: 'POST', body: JSON.stringify(body) }),
  update: (id: string, body: object)      =>
    request<BiodiversitySupplierAPI>(`/api/biodiversity/suppliers/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (id: string)                    =>
    request<void>(`/api/biodiversity/suppliers/${id}`, { method: 'DELETE' }),
  species: (id: string)                   =>
    request<ThreatenedSpeciesAPI[]>(`/api/biodiversity/suppliers/${id}/species`),
};

// ── Health ──────────────────────────────────────────────────────────────────

export const healthApi = {
  check: () => request<{ status: string }>('/api/health'),
};
