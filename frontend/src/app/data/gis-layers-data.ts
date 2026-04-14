/* ─────────────────────────────────────────────────────────────
   GIS Layer mock data
   Reflects the dataset categories from the Epic 2 data report:
     1. Threatened Species observations
     2. Protected Regions (EPBC / IUCN PA)
     3. Forest Cover
     4. Water Bodies & Catchments
     5. Deforestation Risk Hotspots
   ───────────────────────────────────────────────────────────── */

export type LayerType = 'point' | 'polygon' | 'heatzone' | 'line';

export interface GisFeature {
  id: string;
  lat: number;
  lng: number;
  /** optional bounding box corners for polygon layers: [sw, ne] */
  bounds?: [[number, number], [number, number]];
  /** optional polyline path for river/catchment layers */
  path?: [number, number][];
  label: string;
  meta: Record<string, string | number>;
}

export interface GisSubLayer {
  id: string;
  label: string;
  type: LayerType;
  color: string;
  fillOpacity: number;
  strokeOpacity: number;
  radius?: number;          // for point layers (metres → Leaflet pixels)
  features: GisFeature[];
}

export interface GisLayerGroup {
  id: string;
  label: string;
  icon: string;             // emoji shorthand — replaced with Lucide in UI
  description: string;
  subLayers: GisSubLayer[];
}

/* ── 1. Threatened Species ───────────────────────────────── */
const threatenedSpeciesGroup: GisLayerGroup = {
  id: 'threatened-species',
  label: 'Threatened Species',
  icon: 'bird',
  description: 'EPBC Act listed species observations (2020–2026)',
  subLayers: [
    {
      id: 'ts-critically-endangered',
      label: 'Critically Endangered',
      type: 'point',
      color: '#dc2626',
      fillOpacity: 0.75,
      strokeOpacity: 1,
      radius: 9,
      features: [
        { id: 'ts-ce-1', lat: -16.25, lng: 145.42, label: 'Daintree River Ringtail Possum', meta: { species: 'Pseudochirulus cinereus', count: 12, year: 2025 } },
        { id: 'ts-ce-2', lat: -37.82, lng: 147.65, label: "Leadbeater's Possum",          meta: { species: 'Gymnobelideus leadbeateri', count: 8, year: 2025 } },
        { id: 'ts-ce-3', lat: -34.78, lng: 143.88, label: 'Plains-wanderer',              meta: { species: 'Pedionomus torquatus', count: 3, year: 2024 } },
        { id: 'ts-ce-4', lat: -14.50, lng: 143.72, label: 'Golden-shouldered Parrot',     meta: { species: 'Psephotellus chrysopterygius', count: 17, year: 2025 } },
      ],
    },
    {
      id: 'ts-endangered',
      label: 'Endangered',
      type: 'point',
      color: '#f59e0b',
      fillOpacity: 0.7,
      strokeOpacity: 1,
      radius: 8,
      features: [
        { id: 'ts-e-1', lat: -16.30, lng: 145.40, label: 'Southern Cassowary',      meta: { species: 'Casuarius casuarius johnsonii', count: 45, year: 2025 } },
        { id: 'ts-e-2', lat: -15.80, lng: 128.70, label: 'Northern Quoll',          meta: { species: 'Dasyurus hallucatus', count: 22, year: 2024 } },
        { id: 'ts-e-3', lat: -41.72, lng: 145.28, label: 'Tasmanian Devil',         meta: { species: 'Sarcophilus harrisii', count: 58, year: 2025 } },
        { id: 'ts-e-4', lat: -15.78, lng: 128.68, label: 'Gouldian Finch',          meta: { species: 'Erythrura gouldiae', count: 120, year: 2025 } },
        { id: 'ts-e-5', lat: -37.86, lng: 147.58, label: 'Long-footed Potoroo',     meta: { species: 'Potorous longipes', count: 14, year: 2024 } },
        { id: 'ts-e-6', lat: -14.47, lng: 143.90, label: 'Northern Bettong',        meta: { species: 'Bettongia tropica', count: 31, year: 2025 } },
      ],
    },
    {
      id: 'ts-vulnerable',
      label: 'Vulnerable',
      type: 'point',
      color: '#6366f1',
      fillOpacity: 0.6,
      strokeOpacity: 1,
      radius: 7,
      features: [
        { id: 'ts-v-1', lat: -22.35, lng: 118.30, label: 'Pilbara Olive Python', meta: { species: 'Liasis olivaceus barroni', count: 9, year: 2024 } },
        { id: 'ts-v-2', lat: -35.00, lng: 138.75, label: 'Yellow-footed Rock-wallaby', meta: { species: 'Petrogale xanthopus', count: 36, year: 2025 } },
        { id: 'ts-v-3', lat: -41.80, lng: 145.22, label: 'Giant Freshwater Crayfish', meta: { species: 'Astacopsis gouldi', count: 6, year: 2025 } },
        { id: 'ts-v-4', lat: -14.42, lng: 143.82, label: 'Palm Cockatoo',          meta: { species: 'Probosciger aterrimus', count: 27, year: 2024 } },
      ],
    },
  ],
};

/* ── 2. Protected Regions ────────────────────────────────── */
const protectedRegionsGroup: GisLayerGroup = {
  id: 'protected-regions',
  label: 'Protected Regions',
  icon: 'shield',
  description: 'EPBC Listed Protected Areas and IUCN Category I–IV reserves',
  subLayers: [
    {
      id: 'pr-national-park',
      label: 'National Parks',
      type: 'polygon',
      color: '#059669',
      fillOpacity: 0.12,
      strokeOpacity: 0.6,
      features: [
        { id: 'np-1', lat: -16.28, lng: 145.45, label: 'Daintree National Park (WHA)',
          bounds: [[-16.55, 145.20], [-15.95, 145.62]], meta: { area_km2: 1200, iucn: 'II', state: 'QLD' } },
        { id: 'np-2', lat: -41.73, lng: 145.30, label: 'Tarkine / Arthur-Pieman',
          bounds: [[-41.95, 144.85], [-41.45, 145.62]], meta: { area_km2: 4470, iucn: 'II', state: 'TAS' } },
        { id: 'np-3', lat: -14.48, lng: 143.88, label: 'Cape York Peninsula PA',
          bounds: [[-14.80, 143.60], [-14.10, 144.20]], meta: { area_km2: 2860, iucn: 'VI', state: 'QLD' } },
      ],
    },
    {
      id: 'pr-world-heritage',
      label: 'World Heritage Areas',
      type: 'polygon',
      color: '#7c3aed',
      fillOpacity: 0.10,
      strokeOpacity: 0.5,
      features: [
        { id: 'wha-1', lat: -16.40, lng: 145.50, label: 'Wet Tropics WHA',
          bounds: [[-18.50, 145.20], [-15.50, 146.00]], meta: { area_km2: 8940, year_listed: 1988, state: 'QLD' } },
        { id: 'wha-2', lat: -41.80, lng: 146.20, label: 'Tasmanian Wilderness WHA',
          bounds: [[-43.50, 144.80], [-41.00, 146.60]], meta: { area_km2: 15800, year_listed: 1982, state: 'TAS' } },
      ],
    },
    {
      id: 'pr-ramsar',
      label: 'Ramsar Wetlands',
      type: 'polygon',
      color: '#0284c7',
      fillOpacity: 0.14,
      strokeOpacity: 0.5,
      features: [
        { id: 'ramsar-1', lat: -35.10, lng: 139.30, label: 'Coorong & Lakes',
          bounds: [[-35.50, 138.80], [-34.70, 139.70]], meta: { area_km2: 4710, state: 'SA' } },
        { id: 'ramsar-2', lat: -34.90, lng: 144.20, label: 'Macquarie Marshes',
          bounds: [[-31.50, 147.60], [-31.00, 148.20]], meta: { area_km2: 485, state: 'NSW' } },
      ],
    },
    {
      id: 'pr-indigenous',
      label: 'Indigenous Protected Areas',
      type: 'polygon',
      color: '#b45309',
      fillOpacity: 0.10,
      strokeOpacity: 0.4,
      features: [
        { id: 'ipa-1', lat: -14.46, lng: 143.84, label: 'Cape York IPA',
          bounds: [[-15.20, 143.40], [-13.80, 144.50]], meta: { area_km2: 3800, state: 'QLD' } },
        { id: 'ipa-2', lat: -15.80, lng: 128.72, label: 'Bunuba IPA',
          bounds: [[-16.30, 128.20], [-15.30, 129.30]], meta: { area_km2: 2200, state: 'WA' } },
      ],
    },
  ],
};

/* ── 3. Forest Cover ─────────────────────────────────────── */
const forestCoverGroup: GisLayerGroup = {
  id: 'forest-cover',
  label: 'Forest Cover',
  icon: 'tree',
  description: 'Vegetation cover classes from TERN AusCover & ABARES datasets',
  subLayers: [
    {
      id: 'fc-intact-forest',
      label: 'Intact Native Forest',
      type: 'polygon',
      color: '#166534',
      fillOpacity: 0.18,
      strokeOpacity: 0.5,
      features: [
        { id: 'if-1', lat: -16.10, lng: 145.30, label: 'Wet Tropics Rainforest',
          bounds: [[-17.20, 145.10], [-15.50, 145.70]], meta: { cover_pct: 94, biomass_t_ha: 320 } },
        { id: 'if-2', lat: -41.70, lng: 145.20, label: 'Tarkine Temperate Rainforest',
          bounds: [[-42.10, 144.90], [-41.30, 145.70]], meta: { cover_pct: 89, biomass_t_ha: 480 } },
        { id: 'if-3', lat: -14.40, lng: 143.75, label: 'Cape York Woodland',
          bounds: [[-15.10, 143.50], [-13.90, 144.20]], meta: { cover_pct: 78, biomass_t_ha: 185 } },
      ],
    },
    {
      id: 'fc-regrowth',
      label: 'Regrowth Forest',
      type: 'polygon',
      color: '#4ade80',
      fillOpacity: 0.14,
      strokeOpacity: 0.4,
      features: [
        { id: 'rg-1', lat: -37.80, lng: 147.60, label: 'Gippsland Regrowth',
          bounds: [[-38.20, 147.10], [-37.40, 148.10]], meta: { cover_pct: 62, age_yrs: 18 } },
        { id: 'rg-2', lat: -35.10, lng: 138.70, label: 'Mt Lofty Regrowth',
          bounds: [[-35.50, 138.40], [-34.70, 139.10]], meta: { cover_pct: 55, age_yrs: 12 } },
      ],
    },
    {
      id: 'fc-cleared-land',
      label: 'Recently Cleared Land',
      type: 'polygon',
      color: '#ef4444',
      fillOpacity: 0.15,
      strokeOpacity: 0.5,
      features: [
        { id: 'cl-1', lat: -15.77, lng: 128.74, label: 'Kimberley Cleared Pastoral',
          bounds: [[-16.20, 128.30], [-15.30, 129.20]], meta: { area_ha: 8200, year: 2024 } },
        { id: 'cl-2', lat: -14.52, lng: 143.82, label: 'Cape York Land Clearing',
          bounds: [[-14.90, 143.60], [-14.10, 144.10]], meta: { area_ha: 4800, year: 2025 } },
      ],
    },
    {
      id: 'fc-plantation',
      label: 'Commercial Plantation',
      type: 'polygon',
      color: '#84cc16',
      fillOpacity: 0.12,
      strokeOpacity: 0.4,
      features: [
        { id: 'pl-1', lat: -37.82, lng: 147.60, label: 'Gippsland Pine Plantation',
          bounds: [[-38.10, 147.30], [-37.55, 147.90]], meta: { species: 'Pinus radiata', area_ha: 3200 } },
      ],
    },
  ],
};

/* ── 4. Water Bodies & Catchments ────────────────────────── */
const waterBodiesGroup: GisLayerGroup = {
  id: 'water-bodies',
  label: 'Water Bodies',
  icon: 'droplets',
  description: 'Major river catchments and surface water stress zones (BOM / CSIRO)',
  subLayers: [
    {
      id: 'wb-rivers',
      label: 'Major River Catchments',
      type: 'line',
      color: '#0ea5e9',
      fillOpacity: 0,
      strokeOpacity: 0.6,
      features: [
        { id: 'rv-1', lat: -34.75, lng: 143.92, label: 'Murray-Darling River',
          path: [[-30.5, 148.0], [-31.8, 147.2], [-33.0, 145.5], [-34.0, 144.5], [-34.75, 143.92], [-35.40, 143.30], [-35.67, 139.90]],
          meta: { length_km: 3750, flow_ML_yr: 8200 } },
        { id: 'rv-2', lat: -16.25, lng: 145.42, label: 'Daintree River',
          path: [[-16.00, 145.20], [-16.15, 145.35], [-16.25, 145.42], [-16.38, 145.48]],
          meta: { length_km: 140, flow_ML_yr: 1850 } },
        { id: 'rv-3', lat: -15.80, lng: 128.72, label: 'Mitchell River (WA)',
          path: [[-15.40, 128.30], [-15.60, 128.55], [-15.80, 128.72], [-16.00, 128.90]],
          meta: { length_km: 380, flow_ML_yr: 4200 } },
      ],
    },
    {
      id: 'wb-high-stress',
      label: 'High Water Stress Zones',
      type: 'heatzone',
      color: '#f97316',
      fillOpacity: 0.18,
      strokeOpacity: 0.3,
      radius: 16,
      features: [
        { id: 'ws-1', lat: -34.75, lng: 143.92, label: 'Murray-Darling Basin (Stress: 82/100)', meta: { stress_index: 82, trend: 'worsening' } },
        { id: 'ws-2', lat: -22.31, lng: 118.35, label: 'Pilbara Region (Stress: 91/100)',        meta: { stress_index: 91, trend: 'critical' } },
        { id: 'ws-3', lat: -15.77, lng: 128.74, label: 'Kimberley Pastoral (Stress: 68/100)',    meta: { stress_index: 68, trend: 'stable' } },
      ],
    },
  ],
};

/* ── 5. Deforestation Risk ───────────────────────────────── */
const deforestationRiskGroup: GisLayerGroup = {
  id: 'deforestation-risk',
  label: 'Deforestation Risk',
  icon: 'alert',
  description: 'Annual tree-cover loss hotspots (Global Forest Watch / ABARES 2020–2025)',
  subLayers: [
    {
      id: 'def-critical',
      label: 'Critical Loss Zones (>2%/yr)',
      type: 'heatzone',
      color: '#7f1d1d',
      fillOpacity: 0.22,
      strokeOpacity: 0.4,
      radius: 18,
      features: [
        { id: 'dl-1', lat: -16.25, lng: 145.42, label: 'Daintree Corridor Loss (2.4%/yr)',   meta: { rate_pct_yr: 2.4, area_ha: 1240 } },
        { id: 'dl-2', lat: -14.45, lng: 143.85, label: 'Cape York Frontier Loss (2.1%/yr)', meta: { rate_pct_yr: 2.1, area_ha: 2800 } },
      ],
    },
    {
      id: 'def-high',
      label: 'High Loss Zones (1–2%/yr)',
      type: 'heatzone',
      color: '#dc2626',
      fillOpacity: 0.15,
      strokeOpacity: 0.35,
      radius: 14,
      features: [
        { id: 'dl-3', lat: -15.77, lng: 128.74, label: 'Kimberley Pastoral Loss (1.8%/yr)', meta: { rate_pct_yr: 1.8, area_ha: 6400 } },
      ],
    },
    {
      id: 'def-moderate',
      label: 'Moderate Loss Zones (0.5–1%/yr)',
      type: 'heatzone',
      color: '#f59e0b',
      fillOpacity: 0.12,
      strokeOpacity: 0.3,
      radius: 11,
      features: [
        { id: 'dl-4', lat: -41.75, lng: 145.25, label: 'Tarkine Margins Loss (0.9%/yr)', meta: { rate_pct_yr: 0.9, area_ha: 520 } },
        { id: 'dl-5', lat: -22.31, lng: 118.35, label: 'Pilbara Scrub Loss (0.7%/yr)',   meta: { rate_pct_yr: 0.7, area_ha: 3200 } },
      ],
    },
  ],
};

export const GIS_LAYER_GROUPS: GisLayerGroup[] = [
  threatenedSpeciesGroup,
  protectedRegionsGroup,
  forestCoverGroup,
  waterBodiesGroup,
  deforestationRiskGroup,
];

export type { GisLayerGroup, GisSubLayer, GisFeature };
