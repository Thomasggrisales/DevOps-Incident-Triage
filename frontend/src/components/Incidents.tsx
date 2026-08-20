import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import softserveLogo from '../assets/softserve.png';
import { apiFetch } from '../api';

interface Incident {
  id: number;
  title: string;
  description: string;
  source: string;
  severity: string;
  status: string;
  created_at: string;
}

const STATUS_ORDER = ['open', 'investigating', 'resolved'];

const STATUS_LABELS: Record<string, string> = {
  open: 'Abiertos', investigating: 'En investigación', resolved: 'Resueltos',
};

const STATUS_BADGE: Record<string, string> = {
  open: 'bg-rose-500/20 text-rose-300',
  investigating: 'bg-amber-500/20 text-amber-300',
  resolved: 'bg-green-500/20 text-green-300',
};

const SEVERITY_BADGE: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-300',
  high: 'bg-orange-500/20 text-orange-300',
  medium: 'bg-yellow-500/20 text-yellow-300',
  low: 'bg-blue-500/20 text-blue-300',
  pending: 'bg-gray-500/20 text-gray-300',
};

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  // El backend guarda UTC. Si el ISO no trae zona horaria, lo interpretamos como UTC
  // para evitar que `new Date` lo lea como hora local y muestre una hora desfasada.
  const hasTz = /[zZ]|[+-]\d{2}:?\d{2}$/.test(iso);
  const normalized = hasTz ? iso : `${iso}Z`;
  return new Date(normalized).toLocaleString('es-CO', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function Incidents() {
  const [user] = useState<{ name: string; email: string } | null>(() => {
    const raw = localStorage.getItem('user');
    return raw ? JSON.parse(raw) : null;
  });
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const navigate = useNavigate();
  const ITEMS_PER_PAGE = 20;

  const getIncidents = async (): Promise<Incident[]> => {
    const response = await apiFetch('/incidents/');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  };

  const loadIncidents = async () => {
    setLoading(true);
    setError('');
    try {
      setIncidents(await getIncidents());
    } catch {
      setError('No se pudieron cargar los incidentes. Verifica que el backend esté disponible.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      navigate('/login');
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await getIncidents();
        if (!cancelled) setIncidents(data);
      } catch {
        if (!cancelled) {
          setError('No se pudieron cargar los incidentes. Verifica que el backend esté disponible.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const handleFilterChange = (status: string) => {
    setFilterStatus(status);
    setCurrentPage(1);
  };

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setCurrentPage(1);
  };

  const filtered = incidents
    .filter((inc) => filterStatus === 'all' || inc.status === filterStatus)
    .filter((inc) => {
      const term = search.trim().toLowerCase();
      return !term || inc.title.toLowerCase().includes(term) || String(inc.id).includes(term);
    });

  const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE);
  const paginatedIncidents = filtered.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const activeCount = incidents.filter((inc) => inc.status === 'open' || inc.status === 'investigating').length;
  const resolvedCount = incidents.filter((inc) => inc.status === 'resolved').length;

  return (
    <div className="flex min-h-screen bg-slate-900 text-white">

      {/* Barra Lateral (Sidebar) */}
      <aside className="hidden w-64 flex-col border-r border-white/10 bg-slate-900/50 p-6 md:flex">
        <div className="mb-8 flex items-center gap-3">
          <img
            src={softserveLogo}
            alt="Softserve Logo"
            className="h-10 w-10 rounded-lg object-cover shadow-lg bg-white/5 border border-white/10"
          />
          <h2 className="text-xl font-extrabold tracking-tight">DevOps Triage</h2>
        </div>

        <nav className="flex flex-1 flex-col gap-2">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-gray-400 transition-colors hover:bg-white/5 hover:text-white"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            Inicio
          </button>
          <button
            onClick={() => navigate('/incidents')}
            className="flex w-full items-center gap-3 rounded-lg bg-blue-600/20 px-4 py-3 text-left text-blue-400 transition-colors"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Incidentes
          </button>

          <button
            onClick={() => navigate('/chat')}
            className="mt-4 flex w-full items-center gap-3 rounded-lg border border-purple-500/30 bg-purple-600/10 px-4 py-3 text-left text-purple-400 transition-colors hover:bg-purple-600/20 hover:text-purple-300"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            Asistente IA
          </button>
        </nav>
      </aside>

      {/* Contenido Principal */}
      <main className="flex flex-1 flex-col">
        {/* Cabecera (Topbar) */}
        <header className="flex items-center justify-between border-b border-white/10 bg-slate-900/50 px-8 py-4 backdrop-blur-md">
          <div>
            <h1 className="text-2xl font-bold">Incidentes</h1>
            <p className="text-sm text-gray-400">
              {incidents.length} en total · {activeCount} activos · {resolvedCount} resueltos
            </p>
          </div>

          <div className="flex items-center gap-6">
            <span className="text-sm text-gray-300">
              Hola, <strong className="text-white">{user?.name || 'Ingeniero'}</strong>
            </span>
            <button
              onClick={loadIncidents}
              disabled={loading}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-gray-300 transition-colors hover:bg-white/10 hover:text-white disabled:opacity-50"
            >
              {loading ? 'Cargando…' : 'Refrescar'}
            </button>
            <button
              onClick={handleLogout}
              className="rounded-lg border border-red-500/50 px-4 py-2 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/10 hover:text-red-300"
            >
              Cerrar Sesión
            </button>
          </div>
        </header>

        {/* Contenido */}
        <div className="flex-1 overflow-y-auto p-8">
          {error && (
            <div className="mb-6 rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-300">
              {error}
            </div>
          )}

          {/* Filtros */}
          <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => handleFilterChange('all')}
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                  filterStatus === 'all'
                    ? 'bg-blue-600/30 text-blue-300'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
                }`}
              >
                Todos
              </button>
              {STATUS_ORDER.map((status) => (
                <button
                  key={status}
                  onClick={() => handleFilterChange(status)}
                  className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                    filterStatus === status
                      ? 'bg-blue-600/30 text-blue-300'
                      : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  {STATUS_LABELS[status]}
                </button>
              ))}
            </div>

            <input
              type="text"
              placeholder="Buscar por título o ID…"
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="w-full rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400/50 md:w-72"
            />
          </div>

          {/* Tabla de incidentes (resumen desde el dashboard) */}
          <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wider text-gray-500">
                  <th className="px-6 pb-3 pt-4 font-medium">ID</th>
                  <th className="px-4 pb-3 pt-4 font-medium">Título</th>
                  <th className="px-4 pb-3 pt-4 font-medium">Severidad</th>
                  <th className="px-4 pb-3 pt-4 font-medium">Estado</th>
                  <th className="px-4 pb-3 pt-4 font-medium">Fuente</th>
                  <th className="px-6 pb-3 pt-4 font-medium">Creado</th>
                </tr>
              </thead>
              <tbody>
                {paginatedIncidents.map((inc) => (
                  <tr key={inc.id} onClick={() => navigate(`/chat/${inc.id}`)} className="border-b border-white/5 transition-colors last:border-0 hover:bg-white/5 cursor-pointer">
                    <td className="px-6 py-3 text-gray-400">#{inc.id}</td>
                    <td className="max-w-[340px] truncate px-4 py-3 text-gray-200">{inc.title}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${SEVERITY_BADGE[inc.severity] || SEVERITY_BADGE.pending}`}>
                        {inc.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${STATUS_BADGE[inc.status] || STATUS_BADGE.open}`}>
                        {inc.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400">{inc.source}</td>
                    <td className="whitespace-nowrap px-6 py-3 text-gray-400">{formatDate(inc.created_at)}</td>
                  </tr>
                ))}
                {!loading && filtered.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-sm text-gray-500">
                      No hay incidentes que coincidan con los filtros.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Paginación */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between">
              <p className="text-sm text-gray-400">
                Mostrando {((currentPage - 1) * ITEMS_PER_PAGE) + 1}–{Math.min(currentPage * ITEMS_PER_PAGE, filtered.length)} de {filtered.length} incidentes
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-gray-300 transition-colors hover:bg-white/10 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Anterior
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter((page) => {
                    if (totalPages <= 7) return true;
                    if (page === 1 || page === totalPages) return true;
                    if (Math.abs(page - currentPage) <= 1) return true;
                    return false;
                  })
                  .reduce<(number | string)[]>((acc, page, i, arr) => {
                    if (i > 0 && (arr[i - 1] as number) + 1 !== page) {
                      acc.push('...');
                    }
                    acc.push(page);
                    return acc;
                  }, [])
                  .map((page, i) =>
                    typeof page === 'string' ? (
                      <span key={`ellipsis-${i}`} className="px-2 text-gray-500">…</span>
                    ) : (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                          currentPage === page
                            ? 'bg-blue-600/30 text-blue-300'
                            : 'text-gray-400 hover:bg-white/10 hover:text-white'
                        }`}
                      >
                        {page}
                      </button>
                    )
                  )}
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-gray-300 transition-colors hover:bg-white/10 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Siguiente
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
