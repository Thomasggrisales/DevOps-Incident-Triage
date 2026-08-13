const API_BASE = 'http://localhost:8000';

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = localStorage.getItem('token');
  const headers = new Headers(init?.headers);
  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return fetch(`${API_BASE}${path}`, { ...init, headers });
}
