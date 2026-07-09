import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState(''); // Estado para la segunda contraseña
  const [showPassword, setShowPassword] = useState(false); // Estado para el ojito
  const [error, setError] = useState('');
  
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validación de contraseñas iguales
    if (password !== confirmPassword) {
      setError('Las contraseñas no coinciden. Por favor, verifica e intenta de nuevo.');
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, email, password, role: 'devops' }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Ocurrió un error al registrar el usuario');
      }

      alert('¡Cuenta creada con éxito! Ahora puedes iniciar sesión.');
      navigate('/login');
      
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-blue-900 p-4 sm:p-8">
      
      <div className="flex w-full max-w-5xl flex-col overflow-hidden rounded-3xl border border-white/20 bg-white/10 shadow-2xl backdrop-blur-md md:flex-row">
        
        {/* === COLUMNA IZQUIERDA: FORMULARIO === */}
        <div className="w-full border-r border-white/10 bg-slate-900/40 p-8 md:w-5/12 lg:p-12">
          
          <div className="mx-auto mb-6 flex h-24 w-24 items-center justify-center rounded-full border-2 border-blue-400/50 bg-white/5 shadow-inner backdrop-blur-sm">
            <svg className="h-12 w-12 text-blue-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>

          <h2 className="mb-8 text-center text-2xl font-bold tracking-tight text-white">
            Crear Cuenta
          </h2>

          {error && (
            <div className="mb-6 rounded-xl border-l-4 border-red-500 bg-red-500/20 p-4 text-sm text-white backdrop-blur-sm">
              <p>{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Campo: Nombre */}
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
              </div>
              <input
                type="text"
                required
                placeholder="Ej. Pepito Pérez"
                className="w-full rounded-full border border-white/20 bg-white/5 py-3 pl-11 pr-4 text-sm text-white placeholder-gray-400 transition-colors focus:border-blue-400 focus:bg-white/10 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            {/* Campo: Correo */}
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <input
                type="email"
                required
                placeholder="tu@correo.com"
                className="w-full rounded-full border border-white/20 bg-white/5 py-3 pl-11 pr-4 text-sm text-white placeholder-gray-400 transition-colors focus:border-blue-400 focus:bg-white/10 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            {/* Campo: Contraseña */}
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <input
                type={showPassword ? "text" : "password"}
                required
                placeholder="Contraseña"
                className="w-full rounded-full border border-white/20 bg-white/5 py-3 pl-11 pr-12 text-sm text-white placeholder-gray-400 transition-colors focus:border-blue-400 focus:bg-white/10 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
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

            {/* Campo: Confirmar Contraseña */}
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <input
                type={showPassword ? "text" : "password"}
                required
                placeholder="Confirmar contraseña"
                className="w-full rounded-full border border-white/20 bg-white/5 py-3 pl-11 pr-12 text-sm text-white placeholder-gray-400 transition-colors focus:border-blue-400 focus:bg-white/10 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </div>

            <button
              type="submit"
              className="mt-6 w-full rounded-full bg-blue-600/90 py-3 text-sm font-bold tracking-wide text-white transition-all hover:bg-blue-500 hover:shadow-[0_0_15px_rgba(59,130,246,0.5)] focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-slate-900 active:scale-[0.98]"
            >
              Registrarse
            </button>
            
            <div className="mt-6 text-center text-sm text-gray-400">
              ¿Ya tienes cuenta?{' '}
              <Link to="/login" className="font-semibold text-blue-300 transition-colors hover:text-white">
                Inicia sesión
              </Link>
            </div>
          </form>
        </div>

        {/* === COLUMNA DERECHA: WELCOME === */}
        <div className="relative hidden w-full flex-col justify-center p-12 md:flex md:w-7/12">
          <div className="absolute inset-0 bg-gradient-to-tr from-blue-500/10 via-transparent to-transparent"></div>
          
          <div className="relative z-10">
            <h1 className="mb-4 text-6xl font-extrabold tracking-tight text-white drop-shadow-lg lg:text-7xl">
              Welcome.
            </h1>
            <p className="max-w-md text-lg leading-relaxed text-blue-100/80">
              Estás a un paso de unirte al equipo. Registra tus credenciales para acceder al portal centralizado de DevOps Triage.
            </p>
          </div>

        </div>

      </div>
    </div>
  );
}