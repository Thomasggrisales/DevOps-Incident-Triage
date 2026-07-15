import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Dashboard() {
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Verificamos si hay un token guardado
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');

    if (!token) {
      // Si no hay token, lo mandamos al login
      navigate('/login');
    } else if (userData) {
      setUser(JSON.parse(userData));
    }
  }, [navigate]);

  const handleLogout = () => {
    // Limpiamos los datos y cerramos sesión
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  return (
    <div className="flex min-h-screen bg-slate-900 text-white">
      
      {/* Barra Lateral (Sidebar) */}
      <aside className="hidden w-64 flex-col border-r border-white/10 bg-slate-900/50 p-6 md:flex">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 font-bold text-white shadow-lg">
            DT
          </div>
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
              onClick={handleLogout}
              className="rounded-lg border border-red-500/50 px-4 py-2 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/10 hover:text-red-300"
            >
              Cerrar Sesión
            </button>
          </div>
        </header>

        {/* Área de tarjetas placeholder */}
        <div className="p-8">
          <div className="grid gap-6 md:grid-cols-3">
            {/* Tarjeta 1 */}
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
              <h3 className="text-sm font-medium text-gray-400">Incidentes Activos</h3>
              <p className="mt-2 text-4xl font-bold text-blue-400">0</p>
            </div>
            {/* Tarjeta 2 */}
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
              <h3 className="text-sm font-medium text-gray-400">Tasa de Resolución</h3>
              <p className="mt-2 text-4xl font-bold text-green-400">100%</p>
            </div>
            {/* Tarjeta 3 */}
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
              <h3 className="text-sm font-medium text-gray-400">Alertas Críticas</h3>
              <p className="mt-2 text-4xl font-bold text-red-400">0</p>
            </div>
          </div>

          {/* Área grande para futuro contenido (tablas, gráficas, etc.) */}
          <div className="mt-8 rounded-2xl border border-white/10 bg-white/5 p-8 text-center backdrop-blur-sm">
            <svg className="mx-auto mb-4 h-12 w-12 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <h3 className="text-lg font-medium text-gray-300">No hay datos recientes</h3>
            <p className="mt-1 text-sm text-gray-500">Aquí irán las listas de incidentes y los registros del sistema.</p>
          </div>
        </div>
      </main>
    </div>
  );
}