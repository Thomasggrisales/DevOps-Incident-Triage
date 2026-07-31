import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import softserveLogo from '../assets/softserve.png';

export default function Chat() {
  const [messages, setMessages] = useState([
    { role: 'agent', text: '¡Hola! Soy tu Asistente DevOps. Analizo los registros de Weaviate para ayudarte. ¿Qué incidente estamos revisando hoy?' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null); // Nueva referencia para controlar la altura del textarea
  const navigate = useNavigate();

  // Auto-scroll al final del chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Lógica principal de envío (separada para llamarla desde el teclado o el botón)
  const executeSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    
    // Reseteamos la altura del textarea después de enviar
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    setMessages((prev) => [...prev, { role: 'user', text: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/incidents/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMessage }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessages((prev) => [...prev, { role: 'agent', text: data.answer }]);
      } else {
        setMessages((prev) => [...prev, { role: 'agent', text: `Error: ${data.error || 'Hubo un problema de conexión.'}` }]);
      }
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'agent', text: 'Error crítico: No se pudo conectar con el backend.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Manejador del botón o formulario tradicional
  const handleSendForm = (e) => {
    e.preventDefault();
    executeSend();
  };

  // Manejador del teclado (El corazón del Shift + Enter)
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        // Si presiona Shift + Enter, dejamos que haga el salto de línea normal
        return;
      }
      // Si solo presiona Enter, evitamos el salto de línea y enviamos
      e.preventDefault();
      executeSend();
    }
  };

  // Manejador de cambio de texto (Auto-ajusta la altura del textarea)
  const handleInputChange = (e) => {
    setInput(e.target.value);
    
    // Reseteamos la altura a auto para calcular el nuevo tamaño
    e.target.style.height = 'auto';
    // Establecemos la altura basada en el scrollHeight (con un límite máximo en CSS)
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  return (
    <div className="flex min-h-screen bg-slate-900 text-white font-sans">
      
      {/* Botón para volver al Dashboard */}
      <button 
        onClick={() => navigate('/dashboard')}
        className="absolute top-6 left-6 flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
      >
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Volver al Dashboard
      </button>

      {/* Contenedor Principal del Chat */}
      <div className="flex flex-col w-full max-w-4xl mx-auto my-16 bg-white/5 border border-white/10 rounded-2xl shadow-2xl backdrop-blur-sm overflow-hidden">
        
        {/* Cabecera del Chat */}
        <div className="bg-slate-900/80 border-b border-white/10 p-5 flex items-center gap-4">
          
          {/* Imagen corregida: sin el div contenedor que tenía el margin-bottom */}
          <img 
            src={softserveLogo}
            alt="Softserve Logo" 
            className="h-12 w-12 rounded-xl object-cover shadow-lg bg-white/5 border border-white/10"
          />
          
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Copilot de Incidentes</h2>
            <p className="text-sm text-gray-400 flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              Conectado a Weaviate Vector DB
            </p>
          </div>
        </div>

        {/* Área de Mensajes */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 min-h-[500px]">
          {messages.map((msg, index) => (
            <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[80%] p-4 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white rounded-tr-sm shadow-md'
                    : 'bg-white/5 border border-white/10 text-gray-200 rounded-tl-sm shadow-sm'
                }`}
              >
                {/* Formateo simple para respetar los saltos de línea del agente y del usuario */}
                <span className="whitespace-pre-wrap font-mono">{msg.text}</span>
              </div>
            </div>
          ))}
          
          {/* Indicador de Carga */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white/5 border border-white/10 p-4 rounded-2xl rounded-tl-sm flex gap-2 items-center w-24 shadow-sm">
                <div className="w-2 h-2 rounded-full bg-purple-400 animate-bounce"></div>
                <div className="w-2 h-2 rounded-full bg-purple-400 animate-bounce delay-100"></div>
                <div className="w-2 h-2 rounded-full bg-purple-400 animate-bounce delay-200"></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Zona de Input */}
        <div className="p-4 bg-slate-900/50 border-t border-white/10">
          <form onSubmit={handleSendForm} className="flex gap-3 items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Ej: ¿Hay incidentes activos? (Shift + Enter para nueva línea)"
              rows={1}
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all resize-none overflow-y-auto min-h-[48px] max-h-[200px] [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-white/20 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-white/30"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="bg-purple-600 hover:bg-purple-500 text-white px-6 py-3 h-[48px] rounded-xl font-medium disabled:opacity-50 disabled:hover:bg-purple-600 transition-colors flex items-center gap-2 shadow-lg shadow-purple-900/20 whitespace-nowrap"
            >
              <span>Enviar</span>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}