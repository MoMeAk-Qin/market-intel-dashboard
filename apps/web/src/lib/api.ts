const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:4000';

type QueryValue = string | number | boolean | undefined | null;

type QueryParams = Record<string, QueryValue>;

const buildQuery = (params?: QueryParams) => {
  if (!params) return '';
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    searchParams.set(key, String(value));
  });
  const query = searchParams.toString();
  return query ? `?${query}` : '';
};

const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }
  return (await response.json()) as T;
};

export const apiGet = async <T>(path: string, params?: QueryParams): Promise<T> => {
  const url = `${API_BASE_URL}${path}${buildQuery(params)}`;
  const response = await fetch(url, { cache: 'no-store' });
  return handleResponse<T>(response);
};

export const apiPost = async <T>(path: string, body: Record<string, unknown>): Promise<T> => {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return handleResponse<T>(response);
};
