/**
 * geocode.ts — Nominatim geocoder with Australian bias + resolution grading.
 *
 * Fixes applied:
 *  1. Always appends countrycodes=au + ", Australia" suffix → prevents
 *     ambiguous names (e.g. "Richmond", "Port Augusta") resolving to US/UK.
 *  2. Prefers enrichedAddress (post-ABR validated) over the raw CSV address.
 *  3. 3-tier fallback: enrichedAddress → rawAddress → supplierName.
 *  4. Serial queue enforces Nominatim ToS: max 1 request/second.
 *  5. classifyType maps OSM type/class → resolutionLevel for UI confidence display.
 */

export interface GeoResult {
  lat: number;
  lng: number;
  resolutionLevel: 'facility' | 'regional' | 'state' | 'unknown';
  inferenceMethod: string;
  displayName: string;
}

// ── OSM type → resolution level ──────────────────────────────────────────────
const FACILITY_TYPES = new Set([
  'building', 'office', 'commercial', 'industrial',
  'house', 'amenity', 'shop', 'place_of_worship',
]);
const REGIONAL_TYPES = new Set([
  'suburb', 'neighbourhood', 'quarter', 'city_district',
  'town', 'village', 'hamlet', 'locality', 'postcode',
]);
const STATE_TYPES = new Set(['state', 'state_district', 'county', 'region']);

function classifyType(osmType: string, classType: string): GeoResult['resolutionLevel'] {
  const t = osmType ?? classType ?? '';
  if (FACILITY_TYPES.has(t)) return 'facility';
  if (REGIONAL_TYPES.has(t)) return 'regional';
  if (STATE_TYPES.has(t))    return 'state';
  return 'unknown';
}

// ── Serial queue: Nominatim ToS = max 1 req/sec ───────────────────────────────
let _queue = Promise.resolve();
function enqueue<T>(fn: () => Promise<T>): Promise<T> {
  const result = _queue.then(fn);
  // swallow errors so the queue keeps moving even if one request fails
  _queue = result.then(() => {}, () => {});
  return result;
}

async function nominatimQuery(q: string): Promise<GeoResult | null> {
  // Rate-limit guard: ensure ≥1.1s between requests
  await new Promise(r => setTimeout(r, 1100));

  const params = new URLSearchParams({
    q,
    format:         'jsonv2',
    countrycodes:   'au',       // ← FIX: constrain to Australia only
    addressdetails: '1',
    limit:          '1',
  });

  let res: Response;
  try {
    res = await fetch(
      `https://nominatim.openstreetmap.org/search?${params}`,
      {
        headers: {
          'Accept-Language': 'en-AU',
          'User-Agent': 'eco-supply-chain-risk/1.0 (github.com/alee0151/eco)',
        },
      }
    );
  } catch {
    return null; // network failure
  }

  if (!res.ok) return null;

  let data: unknown;
  try { data = await res.json(); } catch { return null; }

  if (!Array.isArray(data) || !data.length) return null;

  const hit = data[0] as Record<string, string>;
  return {
    lat:             parseFloat(hit.lat),
    lng:             parseFloat(hit.lon),
    resolutionLevel: classifyType(hit.type ?? '', hit.class ?? ''),
    inferenceMethod: 'nominatim',
    displayName:     hit.display_name ?? '',
  };
}

/**
 * Geocode a supplier address with Australian country bias and 3-tier fallback.
 *
 * Attempt order (stops at first non-unknown result):
 *   1. enrichedAddress + ", Australia"   — most precise; post-ABR validated
 *   2. rawAddress      + ", Australia"   — original CSV value
 *   3. supplierName    + ", Australia"   — last resort; yields regional resolution
 *
 * All calls are serialised through a global queue to respect Nominatim's
 * 1 request/second rate limit.
 */
export function geocodeSupplier(
  enrichedAddress: string | undefined,
  rawAddress: string,
  supplierName: string,
): Promise<GeoResult | null> {
  return enqueue(async () => {
    // Attempt 1: enriched / ABR-validated address (preferred)
    if (enrichedAddress?.trim()) {
      const r = await nominatimQuery(`${enrichedAddress.trim()}, Australia`);
      if (r && r.resolutionLevel !== 'unknown') {
        return { ...r, inferenceMethod: 'enriched-address' };
      }
    }

    // Attempt 2: raw CSV address
    if (rawAddress?.trim()) {
      const r = await nominatimQuery(`${rawAddress.trim()}, Australia`);
      if (r && r.resolutionLevel !== 'unknown') {
        return { ...r, inferenceMethod: 'raw-address' };
      }
    }

    // Attempt 3: company name fallback
    if (supplierName?.trim()) {
      const r = await nominatimQuery(`${supplierName.trim()}, Australia`);
      if (r) {
        return { ...r, inferenceMethod: 'name-fallback', resolutionLevel: 'regional' };
      }
    }

    return null;
  });
}
