/**
 * Typed API client — all backend calls go through here.
 * The Vite dev proxy rewrites /api/* → http://localhost:8000/api/*
 */

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body?.detail ?? body?.message ?? message;
    } catch {
      // ignore JSON parse failure
    }
    throw new ApiError(res.status, message);
  }

  return res.json() as Promise<T>;
}

/* ── Extract endpoint ─────────────────────────────────────── */

export interface ExtractResult {
  name: string;
  abn: string;
  address: string;
  commodity: string;
  /** 0–100 confidence the model has in each extracted field */
  confidence?: {
    name: number;
    abn: number;
    address: number;
    commodity: number;
  };
  /** Any warnings the backend wants to surface to the user */
  warnings?: string[];
}

/**
 * Upload a single file (PDF or image) to the backend.
 * Returns extracted supplier fields.
 */
export async function extractFromFile(file: File): Promise<ExtractResult> {
  const formData = new FormData();
  formData.append("file", file);

  return request<ExtractResult>("/api/extract", {
    method: "POST",
    body: formData,
  });
}
