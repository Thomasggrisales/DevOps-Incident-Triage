import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false); // Estado para el ojito
  const [error, setError] = useState('');
  
  const navigate = useNavigate();

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
      
      navigate('/dashboard');
      
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-blue-900 p-4">
      
      {/* Tarjeta con efecto Glassmorphism */}
      <div className="w-full max-w-md overflow-hidden rounded-2xl border border-white/20 bg-white/10 shadow-2xl backdrop-blur-md">
        
        {/* Cabecera */}
        <div className="px-8 pb-6 pt-10 text-center">
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
            <div className="mb-6 rounded-lg border-l-4 border-red-500 bg-red-500/20 p-4 text-sm text-white backdrop-blur-sm">
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
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  placeholder="••••••••"
                  className="w-full rounded-lg border border-white/20 bg-white/5 py-3 pl-4 pr-12 text-white placeholder-gray-400 transition-colors focus:border-blue-400 focus:bg-white/10 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                {/* Botón del ojito */}
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-4 text-gray-400 transition-colors hover:text-white focus:outline-none"
                >
                  {showPassword ? (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* Extras del diseño: Recordarme y Olvidé Contraseña */}
            <div className="flex items-center justify-between pt-1">
              <div className="flex items-center">
                <input 
                  type="checkbox" 
                  className="h-4 w-4 rounded border-white/20 bg-white/5 text-blue-500 focus:ring-blue-500/50 focus:ring-offset-0" 
                />
                <label className="ml-2 cursor-pointer block text-sm text-gray-300">
                  Recordarme
                </label>
              </div>
              <Link to="/forgot-password" className="text-sm font-medium text-blue-300 transition-colors hover:text-white">
                ¿Olvidaste tu contraseña?
              </Link>
            </div>

            <button
              type="submit"
              className="mt-6 w-full rounded-lg bg-blue-600/90 py-3 text-sm font-bold tracking-wide text-white transition-all hover:bg-blue-500 hover:shadow-[0_0_15px_rgba(59,130,246,0.5)] focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-slate-900 active:scale-[0.98]"
            >
              Iniciar Sesión
            </button>
            
            <div className="mt-4 text-center text-sm text-gray-400">
              ¿No tienes una cuenta?{' '}
              <Link to="/register" className="font-medium text-blue-300 transition-colors hover:text-white">
                Regístrate
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}