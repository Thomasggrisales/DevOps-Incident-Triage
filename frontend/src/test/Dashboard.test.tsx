import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '../components/Dashboard';

vi.mock('../api', () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from '../api';

const mockApiFetch = vi.mocked(apiFetch);

function jsonResponse(body: unknown) {
  return { ok: true, json: async () => body } as Response;
}

const stats = {
  total: 12,
  active: 3,
  resolved: 8,
  critical_active: 1,
  resolution_rate: 66.7,
  mttr_hours: 1.5,
  by_severity: { critical: 2, high: 4, medium: 3, low: 2, pending: 1 },
  by_status: { open: 2, investigating: 1, resolved: 8, closed: 1 },
};

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

describe('Dashboard', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('user', JSON.stringify({ name: 'Carlos', email: 'c@x.com' }));
    mockApiFetch.mockReset();
  });

  it('redirige a /login si no hay token', async () => {
    localStorage.removeItem('token');
    renderDashboard();
    // Sin token no se dispara ninguna petición a la API.
    expect(mockApiFetch).not.toHaveBeenCalled();
  });

  it('muestra las métricas devueltas por la API', async () => {
    localStorage.setItem('token', 'token-abc');
    mockApiFetch.mockResolvedValueOnce(jsonResponse(stats));

    renderDashboard();

    expect(await screen.findByText('Resumen General')).toBeInTheDocument();
    expect(await screen.findByText('Carlos')).toBeInTheDocument();
    expect(await screen.findByText('12')).toBeInTheDocument();
    expect(screen.getAllByText('8').length).toBeGreaterThan(0);
    expect(screen.getAllByText('1.5').length).toBeGreaterThan(0);
  });

  it('muestra un mensaje de error si la API falla', async () => {
    localStorage.setItem('token', 'token-abc');
    mockApiFetch.mockRejectedValueOnce(new Error('network'));

    renderDashboard();

    expect(
      await screen.findByText('No se pudieron cargar las métricas. Verifica que el backend esté disponible.'),
    ).toBeInTheDocument();
  });

  it('muestra el nombre del usuario guardado en localStorage', async () => {
    localStorage.setItem('token', 'token-abc');
    mockApiFetch.mockResolvedValueOnce(jsonResponse(stats));

    renderDashboard();

    expect(await screen.findByText(/Hola,/)).toBeInTheDocument();
    expect(screen.getByText('Carlos')).toBeInTheDocument();
  });
});
