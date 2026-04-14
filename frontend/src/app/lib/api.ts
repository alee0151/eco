/**
 * api.ts  —  Centralised typed API client
 *
 * All components import from here — never fetch() directly.
 * Base URL is read from VITE_API_URL env var (falls back to localhost:8000).
 */

const BASE = (import.meta as any).env?.VITE_API_URL ?? 'http://localhost:8000';

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

function buildQuery(params: Record<string, string | number | boolean | undefined | null>): string {
  const q = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&');
  return q ? `?${q}` : '';
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SpeciesRecord {
  occurrence_id:    string;
  decimallatitude:  number | null;
  decimallongitude: number | null;
  scientificname:   string | null;
  vernacularname:   string | null;
  taxonconceptid:   string | null;
  kingdom:          string | null;
  occurrencestatus: string | null;
  basisofrecord:    string | null;
  eventdate:        string | null;
  stateprovince:    string | null;
  dataresourcename: string | null;
  is_obscured:      boolean | null;
  source_dataset:   string | null;
  ala_licence:      string | null;
  geom_wkt:         string | null;
}

export interface KbaRecord {
  id:           number;
  sit_rec_id:   number | null;
  region:       string | null;
  country:      string | null;
  iso3:         string | null;
  nat_name:     string | null;
  int_name:     string | null;
  sit_lat:      number | null;
  sit_long:     number | null;
  sit_area_km2: number | null;
  kba_status:   string | null;
  kba_class:    string | null;
  iba_status:   string | null;
  source:       string | null;
  shape_area:   number | null;
  geometry:     string | null;
}

export interface CapadRecord {
  id:               number;
  pa_id:            string | null;
  pa_name:          string | null;
  pa_type:          string | null;
  pa_type_abbr:     string | null;
  iucn_cat:         string | null;
  nrs_pa:           boolean | null;
  gaz_area_ha:      number | null;
  gis_area_ha:      number | null;
  state:            string | null;
  environ:          string | null;
  epbc_trigger:     string | null;
  latitude:         number | null;
  longitude:        number | null;
  governance:       string | null;
  authority:        string | null;
  effective_area_ha: number | null;
  source_dataset:   string | null;
  capad_version:    string | null;
  is_active:        boolean | null;
  geom_wkt:         string | null;
}

export interface IbraRecord {
  id:            number;
  ibra_reg_name: string | null;
  ibra_reg_code: string | null;
  ibra_reg_num:  number | null;
  state:         string | null;
  shape_area:    number | null;
  shape_len:     number | null;
  is_active:     boolean | null;
  geometry:      string | null;
}

export interface SupplierRiskSummary {
  supplier_id:              string;
  supplier_name:            string;
  lat:                      number;
  lng:                      number;
  ibra_region:              string | null;
  ibra_code:                string | null;
  protected_areas_nearby:   number;
  kba_nearby:               number;
  species_nearby:           number;
  threatened_species_names: string[];
}

export interface SupplierRecord {
  id:                   string;
  name:                 string;
  abn:                  string | null;
  address:              string | null;
  commodity:            string | null;
  region:               string | null;
  confidence_score:     number | null;
  status:               'pending' | 'validated' | 'approved' | 'rejected';
  is_validated:         boolean;
  enriched_name:        string | null;
  enriched_address:     string | null;
  abr_status:           string | null;
  abn_found:            boolean | null;
  name_discrepancy:     boolean | null;
  address_discrepancy:  boolean | null;
  lat:                  number | null;
  lng:                  number | null;
  resolution_level:     string | null;
  inference_method:     string | null;
  file_name:            string | null;
  file_type:            string | null;
  warnings:             string | null;  // pipe-separated in DB
}

// ── Species API ───────────────────────────────────────────────────────────────

export const speciesApi = {
  list: (params?: { state?: string; kingdom?: string; limit?: number; offset?: number }) =>
    request<SpeciesRecord[]>(`/api/biodiversity/species${buildQuery(params ?? {})}`),

  byBbox: (bbox: { min_lat: number; max_lat: number; min_lng: number; max_lng: number; limit?: number }) =>
    request<SpeciesRecord[]>(`/api/biodiversity/species/by-bbox${buildQuery(bbox)}`),
};

// ── KBA API ───────────────────────────────────────────────────────────────────

export const kbaApi = {
  list: (params?: { region?: string; limit?: number; offset?: number }) =>
    request<KbaRecord[]>(`/api/biodiversity/kba${buildQuery(params ?? {})}`),

  get: (id: number) =>
    request<KbaRecord>(`/api/biodiversity/kba/${id}`),
};

// ── CAPAD API ─────────────────────────────────────────────────────────────────

export const capadApi = {
  list: (params?: { state?: string; pa_type?: string; is_active?: boolean; limit?: number; offset?: number }) =>
    request<CapadRecord[]>(`/api/biodiversity/capad${buildQuery(params ?? {})}`),

  byState: (state: string, limit = 500) =>
    request<CapadRecord[]>(`/api/biodiversity/capad/by-state/${state}?limit=${limit}`),

  get: (id: number) =>
    request<CapadRecord>(`/api/biodiversity/capad/${id}`),
};

// ── IBRA API ──────────────────────────────────────────────────────────────────

export const ibraApi = {
  list: (params?: { state?: string; limit?: number; offset?: number }) =>
    request<IbraRecord[]>(`/api/biodiversity/ibra${buildQuery(params ?? {})}`),

  getByCode: (code: string) =>
    request<IbraRecord>(`/api/biodiversity/ibra/${code}`),
};

// ── Risk Summary API ──────────────────────────────────────────────────────────

export const riskApi = {
  summary: (params: {
    supplier_id:   string;
    supplier_name: string;
    lat:           number;
    lng:           number;
    buffer_deg?:   number;
  }) => request<SupplierRiskSummary>(`/api/biodiversity/risk-summary${buildQuery(params)}`),
};

// ── Suppliers API (Epic 1) ────────────────────────────────────────────────────

export const suppliersApi = {
  list:   ()                                       => request<SupplierRecord[]>('/api/suppliers'),
  get:    (id: string)                             => request<SupplierRecord>(`/api/suppliers/${id}`),
  create: (body: Partial<SupplierRecord>)          =>
    request<SupplierRecord>('/api/suppliers', { method: 'POST', body: JSON.stringify(body) }),
  update: (id: string, body: Partial<SupplierRecord>) =>
    request<SupplierRecord>(`/api/suppliers/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (id: string)                             =>
    request<void>(`/api/suppliers/${id}`, { method: 'DELETE' }),
};

// ── Health ────────────────────────────────────────────────────────────────────

export const healthApi = {
  check: () => request<{ status: string; version: string }>('/api/health'),
};
