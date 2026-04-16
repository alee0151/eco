/**
 * api.ts — Centralised typed API client
 */

const BASE: string = import.meta.env.VITE_API_URL ?? '';

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

async function requestFormData<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: 'POST', body: form });
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

export interface CapadNearby {
  name:       string;
  iucn_cat:   string | null;
  pa_type:    string | null;
  governance: string | null;
  area_ha:    number | null;
  epbc:       string | null;
  state:      string | null;
  dist_km:    number | null;
}

export interface KbaNearby {
  name:     string;
  class:    string | null;
  status:   string | null;
  area_km2: number | null;
  dist_km:  number | null;
}

export interface SupplierRiskSummary {
  // identity
  supplier_id:   string;
  supplier_name: string;
  lat:           number;
  lng:           number;
  // IBRA
  ibra_region:    string | null;
  ibra_code:      string | null;
  ibra_area_km2:  number | null;
  // CAPAD
  protected_areas_nearby:  number;
  capad_nearby:            CapadNearby[];
  iucn_distribution:       Record<string, number>;
  governance_distribution: Record<string, number>;
  epbc_triggered_count:    number;
  // KBA
  kba_nearby_count: number;
  kba_nearby:       KbaNearby[];
  // Species
  species_nearby:           number;
  threatened_species_names: string[];
  species_kingdoms:         string[];
  threatened_from_dataset:  number;
  // Narrative
  assessment_notes: string | null;
}

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

export interface CapadRegion {
  id:           number;
  pa_id:        string | null;
  pa_name:      string | null;
  pa_type:      string | null;
  pa_type_abbr: string | null;
  iucn_cat:     string | null;
  state:        string | null;
  gis_area_ha:  number | null;
  governance:   string | null;
  authority:    string | null;
  epbc_trigger: string | null;
  geom_wkt:     string | null;
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

export interface ExtractFieldConfidence {
  name:      number;
  abn:       number;
  address:   number;
  commodity: number;
}

export interface ExtractResult {
  name:       string;
  abn:        string;
  address:    string;
  commodity:  string;
  confidence: ExtractFieldConfidence;
  warnings:   string[];
}

export interface EnrichResult {
  abn:                 string;
  abn_found:           boolean;
  enriched_name:       string | null;
  enriched_address:    string | null;
  abr_status:          string | null;
  name_discrepancy:    boolean | null;
  address_discrepancy: boolean | null;
  confidence_score:    number | null;
}

// ── Extract API ───────────────────────────────────────────────────────────────

export const extractApi = {
  fromFile: (file: File): Promise<ExtractResult> => {
    const form = new FormData();
    form.append('file', file);
    return requestFormData<ExtractResult>('/api/extract', form);
  },
};

// ── Enrich API ────────────────────────────────────────────────────────────────

export const enrichApi = {
  enrich: (abn: string, name: string, address: string): Promise<EnrichResult> =>
    request<EnrichResult>('/api/enrich', {
      method: 'POST',
      body: JSON.stringify({ abn, name, address }),
    }),
};

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

  regions: (params?: { state?: string; limit?: number; offset?: number }) =>
    request<CapadRegion[]>(`/api/biodiversity/capad/regions${buildQuery(params ?? {})}`),

  regionsByBbox: (bbox: { min_lat: number; max_lat: number; min_lng: number; max_lng: number; limit?: number }) =>
    request<CapadRegion[]>(`/api/biodiversity/capad/regions/by-bbox${buildQuery(bbox)}`),

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

// ── Health ────────────────────────────────────────────────────────────────────

export const healthApi = {
  check: () => request<{ status: string; version: string }>('/api/health'),
};
