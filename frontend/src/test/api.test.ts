import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch } from '../api';

describe('apiFetch', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('prefija la URL base de la API', async () => {
    fetchMock.mockResolvedValueOnce(new Response('{}', { status: 200 }));
    await apiFetch('/incidents/');
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/incidents/',
      expect.objectContaining({ headers: expect.any(Headers) }),
    );
  });

  it('incluye el token Bearer si existe en localStorage', async () => {
    localStorage.setItem('token', 'token-abc');
    fetchMock.mockResolvedValueOnce(new Response('{}', { status: 200 }));
    await apiFetch('/incidents/stats/');

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://localhost:8000/incidents/stats/');
    const headers = init.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer token-abc');
  });

  it('no envía Authorization si no hay token', async () => {
    fetchMock.mockResolvedValueOnce(new Response('{}', { status: 200 }));
    await apiFetch('/incidents/');

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Headers;
    expect(headers.get('Authorization')).toBeNull();
  });

  it('preserva la URL relativa y las opciones pasadas', async () => {
    fetchMock.mockResolvedValueOnce(new Response('{}', { status: 200 }));
    await apiFetch('/incidents/chat/', { method: 'POST', body: '{}' });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://localhost:8000/incidents/chat/');
    expect(init.method).toBe('POST');
    expect(init.body).toBe('{}');
  });
});
