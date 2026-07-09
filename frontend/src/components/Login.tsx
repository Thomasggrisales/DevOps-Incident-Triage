import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      const response = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        throw new Error('Correo o contraseña incorrectos');
      }

      const data = await response.json();
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      
      alert(`¡Bienvenido ${data.user.name}!`);
      
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-blue-900 p-4">
      
      {/* Tarjeta con efecto Glassmorphism */}
      <div className="w-full max-w-md overflow-hidden rounded-2xl bg-white/10 border border-white/20 shadow-2xl backdrop-blur-md">
        
        {/* Cabecera */}
        <div className="px-8 pt-10 pb-6 text-center">
          <h2 className="text-3xl font-extrabold tracking-tight text-white">
            DevOps Triage
          </h2>
          <p className="mt-2 text-sm text-blue-200">
            Portal de gestión y resolución de incidentes
          </p>
        </div>

        {/* Contenedor del formulario */}
        <div className="px-8 pb-10">
          {error && (
            <div className="mb-6 rounded-lg bg-red-500/20 border-l-4 border-red-500 p-4 text-sm text-white backdrop-blur-sm">
              <p className="font-medium">Error de acceso</p>
              <p>{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-200">
                Correo Electrónico
              </label>
              <input
                type="email"
                required
                placeholder="tu@correo.com"
                className="w-full rounded-lg border border-white/20 bg-white/5 px-4 py-3 text-white placeholder-gray-400 transition-colors focus:border-blue-400 focus:bg-white/10 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-gray-200">
                Contraseña
              </label>
              <input
                type="password"
                required
                placeholder="••••••••"
                className="w-full rounded-lg border border-white/20 bg-white/5 px-4 py-3 text-white placeholder-gray-400 transition-colors focus:border-blue-400 focus:bg-white/10 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            {/* Extras del diseño: Recordarme y Olvidé Contraseña */}
            <div className="flex items-center justify-between pt-1">
              <div className="flex items-center">
                <input 
                  type="checkbox" 
                  className="h-4 w-4 rounded border-white/20 bg-white/5 text-blue-500 focus:ring-blue-500/50 focus:ring-offset-0" 
                />
                <label className="ml-2 block text-sm text-gray-300 cursor-pointer">
                  Recordarme
                </label>
              </div>
              <a href="#" className="text-sm font-medium text-blue-300 transition-colors hover:text-white">
                ¿Olvidaste tu contraseña?
              </a>
            </div>

            <button
              type="submit"
              className="mt-6 w-full rounded-lg bg-blue-600/90 py-3 text-sm font-bold tracking-wide text-white transition-all hover:bg-blue-500 hover:shadow-[0_0_15px_rgba(59,130,246,0.5)] focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-slate-900 active:scale-[0.98]"
            >
              Iniciar Sesión
            </button>
            
            <div className="mt-4 text-center text-sm text-gray-400">
                ¿No tienes una cuenta? <Link to="/register" className="text-blue-300 font-medium hover:text-white transition-colors">Regístrate</Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}