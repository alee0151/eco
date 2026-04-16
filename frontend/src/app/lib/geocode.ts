/**
 * geocode.ts — G-NAF geocoder via backend /api/geocode
 *
 * ALL geocoding is server-side only, routed through the FastAPI backend
 * which calls the Geoscape Address API (backed by the official Australian
 * G-NAF dataset — Geocoded National Address File).
 *
 * There is NO client-side geocoding and NO Nominatim calls from the frontend.
 * Nominatim is used only as a server-side fallback inside backend/routes/geocode.py
 * when the GEOSCAPE_API_KEY is not set.
 *
 * This function is called EXCLUSIVELY from EnrichmentPage.
 * MapPage is render-only and never calls this function.
 *
 * Backend response shape (GeocodeResponse):
 *   lat, lng, gnaf_pid, confidence, resolution_level,
 *   inference_method, display_address, source
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
  return {
    lat:             r.lat,
    lng:             r.lng,
    gnafPid:         r.gnaf_pid || undefined,
    resolutionLevel: (
      r.resolution_level === 'facility' ? 'facility'
      : r.resolution_level === 'regional' ? 'regional'
      : r.resolution_level === 'state'    ? 'state'
      : 'unknown'
    ) as GeoResult['resolutionLevel'],
    inferenceMethod: r.inference_method,
    displayName:     r.display_address,
    source:          r.source,
    confidence:      r.confidence,
  };
}

/**
 * Geocode a supplier address via the backend G-NAF (Geoscape) endpoint.
 * Called only from EnrichmentPage — never from MapPage.
 *
 * @param enrichedAddress  ABR-validated address (highest priority for G-NAF lookup)
 * @param rawAddress       LLM-parsed formatted address, or raw CSV value as fallback
 * @param supplierName     Company name (used only as last-resort fallback text)
 * @param parsedComponents Structured fields from LLM parser — street/suburb/state/postcode.
 *                         Passed directly to backend for field-level G-NAF structured matching,
 *                         which is more accurate than free-text search.
 */
export async function geocodeSupplier(
  enrichedAddress: string | undefined,
  rawAddress:      string,
  supplierName:    string,
  parsedComponents?: {
    street?:   string;
    suburb?:   string;
    state?:    string;
    postcode?: string;
  },
): Promise<GeoResult | null> {
  // Priority: ABR-enriched → LLM-parsed formatted → raw CSV → supplier name
  const address = (
    enrichedAddress?.trim()  ||
    rawAddress?.trim()        ||
    supplierName?.trim()      ||
    ''
  );

  if (!address) return null;

  try {
    const result = await geocodeApi.geocode(address, parsedComponents);
    return toGeoResult(result);
  } catch (err) {
    console.error('[geocode] /api/geocode failed — G-NAF backend unreachable:', err);
    return null;
  }
}
