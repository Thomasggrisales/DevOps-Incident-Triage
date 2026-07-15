import { useState } from 'react';
import { Link } from 'react-router-dom';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setIsLoading(true);

    try {
      // ⚠️ IMPORTANTE: Necesitaremos crear este endpoint en el backend más adelante
      const response = await fetch('http://localhost:8000/auth/forgot-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        throw new Error('Hubo un problema al procesar tu solicitud. Intenta de nuevo.');
      }

      // Simulamos éxito para el usuario
      setMessage('Si el correo está registrado, te hemos enviado un enlace con instrucciones para recuperar tu cuenta.');
      setEmail(''); // Limpiamos el campo
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-blue-900 p-4">
      
      {/* Tarjeta Glassmorphism (diseño centrado como el login) */}
      <div className="w-full max-w-md overflow-hidden rounded-2xl border border-white/20 bg-white/10 shadow-2xl backdrop-blur-md">
        
        <div className="px-8 pb-6 pt-10 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full border-2 border-blue-400/50 bg-white/5 shadow-inner backdrop-blur-sm">
            <svg className="h-8 w-8 text-blue-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-white">
            Recuperar Contraseña
          </h2>
          <p className="mt-2 text-sm text-blue-200">
            Ingresa tu correo y te enviaremos las instrucciones.
          </p>
        </div>

        <div className="px-8 pb-10">
          {error && (
            <div className="mb-6 rounded-lg border-l-4 border-red-500 bg-red-500/20 p-4 text-sm text-white backdrop-blur-sm">
              <p>{error}</p>
            </div>
          )}

          {message && (
            <div className="mb-6 rounded-lg border-l-4 border-green-500 bg-green-500/20 p-4 text-sm text-white backdrop-blur-sm">
              <p>{message}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
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

            <button
              type="submit"
              disabled={isLoading}
              className={`mt-6 w-full rounded-full py-3 text-sm font-bold tracking-wide text-white transition-all focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-slate-900 active:scale-[0.98] ${
                isLoading ? 'bg-blue-600/50 cursor-not-allowed' : 'bg-blue-600/90 hover:bg-blue-500 hover:shadow-[0_0_15px_rgba(59,130,246,0.5)]'
              }`}
            >
              {isLoading ? 'Enviando...' : 'Enviar enlace'}
            </button>
            
            <div className="mt-6 text-center text-sm">
              <Link to="/login" className="font-semibold text-blue-300 transition-colors hover:text-white flex items-center justify-center gap-2">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Volver al inicio de sesión
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}