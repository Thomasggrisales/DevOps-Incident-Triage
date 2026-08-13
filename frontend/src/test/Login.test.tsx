import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Login from '../components/Login';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => mockNavigate };
});

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('guarda el token y navega a /dashboard al iniciar sesión correctamente', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ access_token: 'token-abc', user: { name: 'DevOps', email: 'a@b.com' } }),
      }),
    );

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText('tu@correo.com'), 'devops@example.com');
    await user.type(screen.getByPlaceholderText('••••••••'), 'secreto123');
    await user.click(screen.getByRole('button', { name: 'Iniciar Sesión' }));

    await vi.waitFor(() => {
      expect(localStorage.getItem('token')).toBe('token-abc');
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('muestra un error si las credenciales son incorrectas', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: false }));

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText('tu@correo.com'), 'devops@example.com');
    await user.type(screen.getByPlaceholderText('••••••••'), 'mal-pass');
    await user.click(screen.getByRole('button', { name: 'Iniciar Sesión' }));

    expect(await screen.findByText('Correo o contraseña incorrectos')).toBeInTheDocument();
    expect(localStorage.getItem('token')).toBeNull();
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
