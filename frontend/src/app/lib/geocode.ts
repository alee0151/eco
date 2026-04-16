/**
 * geocode.ts — G-NAF geocoder via backend /api/geocode
 *
 * Routes all geocoding through the FastAPI backend, which calls the
 * Geoscape Address API (backed by the official Australian G-NAF dataset)
 * with an automatic Nominatim OSM fallback when Geoscape is unavailable.
 *
 * G-NAF advantages over Nominatim for Australian addresses:
 *   • Official government dataset — every registered Australian address
 *   • Persistent G-NAF PID for each address — stable cross-reference
 *   • Property-level geocode types (PROPERTY_ACCESS, BUILDING_CENTROID, etc.)
 *   • No rate-limit issues (server-side, keyed API)
 *   • Structured suburb/state/postcode matching from LLM parser output
 *
 * The backend returns a GeocodeResponse with:
 *   { lat, lng, gnaf_pid, confidence, resolution_level, inference_method,
 *     display_address, source }
 *
 * Callers (EnrichmentPage, MapPage) pass enrichedAddress as primary input
 * and the LLM-parsed components (street/suburb/state/postcode) for
 * structured matching — enabling G-NAF to use exact field matching rather
 * than fuzzy free-text search.
 */

import { geocodeApi, type GeocodeResult } from './api';

export interface GeoResult {
  lat:             number;
  lng:             number;
  gnafPid?:        string;
  resolutionLevel: 'facility' | 'regional' | 'state' | 'unknown';
  inferenceMethod: string;
  displayName:     string;
  source:          string;   // 'geoscape' | 'nominatim' | 'centroid'
  confidence:      number;
}

function toGeoResult(r: GeocodeResult): GeoResult {
  const level = (
    r.resolution_level === 'facility' ? 'facility'
    : r.resolution_level === 'regional' ? 'regional'
    : r.resolution_level === 'state'    ? 'state'
    : 'unknown'
  ) as GeoResult['resolutionLevel'];

  return {
    lat:             r.lat,
    lng:             r.lng,
    gnafPid:         r.gnaf_pid || undefined,
    resolutionLevel: level,
    inferenceMethod: r.inference_method,
    displayName:     r.display_address,
    source:          r.source,
    confidence:      r.confidence,
  };
}

/**
 * Geocode a supplier address via the backend G-NAF (Geoscape) endpoint.
 *
 * @param enrichedAddress  ABR-validated address string (highest priority)
 * @param rawAddress       LLM-parsed formatted address OR raw CSV value
 * @param supplierName     Company name (unused in G-NAF mode, kept for API compat)
 * @param parsedComponents Optional structured fields from LLM parser — passed
 *                         directly to the backend for field-level G-NAF matching
 */
export async function geocodeSupplier(
  enrichedAddress: string | undefined,
  rawAddress: string,
  supplierName: string,
  parsedComponents?: {
    street?:   string;
    suburb?:   string;
    state?:    string;
    postcode?: string;
  },
): Promise<GeoResult | null> {
  // Prefer ABR-enriched address; fall back to LLM-parsed or raw CSV
  const address = enrichedAddress?.trim() || rawAddress?.trim() || supplierName?.trim() || '';

  if (!address) return null;

  try {
    const result = await geocodeApi.geocode(address, parsedComponents);
    return toGeoResult(result);
  } catch (err) {
    console.error('[geocode] /api/geocode failed:', err);
    return null;
  }
}
