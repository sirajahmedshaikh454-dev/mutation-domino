import type {
  AnalysisListResponse,
  AnalysisParameters,
  AnalysisResponse,
  CreateAnalysisInput,
  ProteinResponse,
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: Record<string, unknown>;

  constructor(
    message: string,
    options: { code?: string; status?: number; details?: Record<string, unknown> } = {},
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = options.code ?? 'UNKNOWN_ERROR';
    this.status = options.status ?? 0;
    this.details = options.details ?? {};
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  let message = `Request failed with status ${response.status}.`;
  let code = 'HTTP_ERROR';
  let details: Record<string, unknown> = {};

  try {
    const payload = (await response.json()) as {
      error?: { code?: string; message?: string; details?: Record<string, unknown> };
      detail?: unknown;
    };
    if (payload.error) {
      code = payload.error.code ?? code;
      message = payload.error.message ?? message;
      details = payload.error.details ?? {};
    } else if (typeof payload.detail === 'string') {
      message = payload.detail;
      code = 'REQUEST_INVALID';
    } else if (Array.isArray(payload.detail)) {
      code = 'REQUEST_INVALID';
      details = { validation: payload.detail };
      message = 'The request did not pass validation.';
    }
  } catch {
    // Keep the generic message when the response body is not JSON.
  }

  return new ApiError(message, { code, status: response.status, details });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: 'application/json', ...(init?.body ? { 'Content-Type': 'application/json' } : {}) },
      ...init,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error;
    }
    throw new ApiError('The local API could not be reached. Is the backend running?', {
      code: 'NETWORK_ERROR',
      details: { reason: error instanceof Error ? error.message : String(error) },
    });
  }

  if (!response.ok) {
    throw await toApiError(response);
  }

  return (await response.json()) as T;
}

export function getProtein(accession: string, signal?: AbortSignal): Promise<ProteinResponse> {
  return request<ProteinResponse>(`/proteins/${encodeURIComponent(accession.trim().toUpperCase())}`, {
    signal,
  });
}

export function createAnalysis(input: CreateAnalysisInput): Promise<AnalysisResponse> {
  return request<AnalysisResponse>('/analyses', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function getAnalysis(id: string, signal?: AbortSignal): Promise<AnalysisResponse> {
  return request<AnalysisResponse>(`/analyses/${encodeURIComponent(id)}`, { signal });
}

export function listAnalyses(
  params: { limit?: number; offset?: number } = {},
  signal?: AbortSignal,
): Promise<AnalysisListResponse> {
  const search = new URLSearchParams();
  search.set('limit', String(params.limit ?? 20));
  search.set('offset', String(params.offset ?? 0));
  return request<AnalysisListResponse>(`/analyses?${search.toString()}`, { signal });
}

export function structureUrl(accession: string): string {
  return `${API_BASE}/proteins/${encodeURIComponent(accession)}/structure`;
}

export function exportJsonUrl(id: string): string {
  return `${API_BASE}/analyses/${encodeURIComponent(id)}/export.json`;
}

export function exportPdfUrl(id: string): string {
  return `${API_BASE}/analyses/${encodeURIComponent(id)}/report.pdf`;
}

export const DEFAULT_PARAMETERS: AnalysisParameters = {
  ca_radius_angstrom: 8,
  heavy_atom_radius_angstrom: 5,
};
