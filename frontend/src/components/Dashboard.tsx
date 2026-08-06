import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import softserveLogo from '../assets/softserve.png';

interface IncidentStats {
  total: number;
  active: number;
  resolved: number;
  critical_active: number;
  resolution_rate: number;
  mttr_hours: number | null;
  by_status: Record<string, number>;
  by_severity: Record<string, number>;
  recent: {
    id: number;
    title: string;
    severity: string;
    status: string;
    source: string;
    created_at: string | null;
  }[];
}

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'pending'];
const SEVERITY_LABELS: Record<string, string> = {
  critical: 'Críticos', high: 'Altos', medium: 'Medios', low: 'Bajos', pending: 'Pendientes',
};
const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500', high: 'bg-orange-500', medium: 'bg-yellow-500', low: 'bg-blue-500', pending: 'bg-gray-500',
};

const STATUS_ORDER = ['open', 'investigating', 'resolved', 'closed'];
const STATUS_LABELS: Record<string, string> = {
  open: 'Abiertos', investigating: 'En investigación', resolved: 'Resueltos', closed: 'Cerrados',
};
const STATUS_COLORS: Record<string, string> = {
  open: 'bg-rose-500', investigating: 'bg-amber-500', resolved: 'bg-green-500', closed: 'bg-gray-400',
};

interface BarDatum { label: string; value: number; color: string }

function BarChart({ data }: { data: BarDatum[] }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="space-y-3">
      {data.map((d) => (
        <div key={d.label}>
          <div className="mb-1 flex justify-between text-xs">
            <span className="text-gray-400">{d.label}</span>
            <span className="font-semibold text-gray-200">{d.value}</span>
          </div>
          <div className="h-2.5 w-full rounded-full bg-white/10">
            <div className={`h-2.5 rounded-full ${d.color}`} style={{ width: `${(d.value / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
      <h3 className="text-sm font-medium text-gray-400">{label}</h3>
      <p className={`mt-2 text-4xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">{title}</h3>
      {children}
    </div>
  );
}

const STATUS_BADGE: Record<string, string> = {
  open: 'bg-rose-500/20 text-rose-300',
  investigating: 'bg-amber-500/20 text-amber-300',
  resolved: 'bg-green-500/20 text-green-300',
  closed: 'bg-gray-500/20 text-gray-300',
};

const SEVERITY_BADGE: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-300',
  high: 'bg-orange-500/20 text-orange-300',
  medium: 'bg-yellow-500/20 text-yellow-300',
  low: 'bg-blue-500/20 text-blue-300',
  pending: 'bg-gray-500/20 text-gray-300',
};

export default function Dashboard() {
  const [user] = useState<{ name: string; email: string } | null>(() => {
    const raw = localStorage.getItem('user');
    return raw ? JSON.parse(raw) : null;
  });
  const [stats, setStats] = useState<IncidentStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const getStats = async (): Promise<IncidentStats | null> => {
    const response = await fetch('http://localhost:8000/incidents/stats/');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  };

  const loadStats = async () => {
    setLoading(true);
    setError('');
    try {
      setStats(await getStats());
    } catch {
      setError('No se pudieron cargar las métricas. Verifica que el backend esté disponible.');
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
        const data = await getStats();
        if (!cancelled) setStats(data);
      } catch {
        if (!cancelled) {
          setError('No se pudieron cargar las métricas. Verifica que el backend esté disponible.');
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

  const severityBars: BarDatum[] = SEVERITY_ORDER.map((key) => ({
    label: SEVERITY_LABELS[key],
    value: stats?.by_severity[key] ?? 0,
    color: SEVERITY_COLORS[key],
  }));

  const statusBars: BarDatum[] = STATUS_ORDER.map((key) => ({
    label: STATUS_LABELS[key],
    value: stats?.by_status[key] ?? 0,
    color: STATUS_COLORS[key],
  }));

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
          <a href="#" className="flex items-center gap-3 rounded-lg bg-blue-600/20 px-4 py-3 text-blue-400 transition-colors">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            Inicio
          </a>
          <a href="#" className="flex items-center gap-3 rounded-lg px-4 py-3 text-gray-400 transition-colors hover:bg-white/5 hover:text-white">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Incidentes
          </a>

          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-3 rounded-lg mt-4 border border-purple-500/30 bg-purple-600/10 px-4 py-3 text-purple-400 transition-colors hover:bg-purple-600/20 hover:text-purple-300 w-full text-left"
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
          <h1 className="text-2xl font-bold">Resumen General</h1>

          <div className="flex items-center gap-6">
            <span className="text-sm text-gray-300">
              Hola, <strong className="text-white">{user?.name || 'Ingeniero'}</strong>
            </span>
            <button
              onClick={loadStats}
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

          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Total de incidentes" value={stats?.total ?? 0} color="text-blue-400" />
            <StatCard label="Activos" value={stats?.active ?? 0} color="text-amber-400" />
            <StatCard label="Resueltos" value={stats?.resolved ?? 0} color="text-green-400" />
            <StatCard label="MTTR (horas)" value={stats?.mttr_hours ?? '—'} color="text-purple-400" />
          </div>

          <div className="mt-8 grid gap-6 md:grid-cols-2">
            <Panel title="Incidentes por severidad">
              <BarChart data={severityBars} />
            </Panel>
            <Panel title="Incidentes por estado">
              <BarChart data={statusBars} />
            </Panel>
          </div>

          <div className="mt-8">
            <Panel title="Incidentes recientes">
              {stats && stats.recent.length > 0 ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wider text-gray-500">
                      <th className="pb-2 pr-4 font-medium">ID</th>
                      <th className="pb-2 pr-4 font-medium">Título</th>
                      <th className="pb-2 pr-4 font-medium">Severidad</th>
                      <th className="pb-2 font-medium">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.recent.map((inc) => (
                      <tr key={inc.id} className="border-b border-white/5 last:border-0">
                        <td className="py-2.5 pr-4 text-gray-400">#{inc.id}</td>
                        <td className="max-w-[300px] truncate py-2.5 pr-4 text-gray-200">{inc.title}</td>
                        <td className="py-2.5 pr-4">
                          <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${SEVERITY_BADGE[inc.severity] || SEVERITY_BADGE.pending}`}>
                            {inc.severity}
                          </span>
                        </td>
                        <td className="py-2.5">
                          <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${STATUS_BADGE[inc.status] || STATUS_BADGE.open}`}>
                            {inc.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-sm text-gray-500">Aún no hay incidentes registrados.</p>
              )}
            </Panel>
          </div>
        </div>
      </main>
    </div>
  );
}
