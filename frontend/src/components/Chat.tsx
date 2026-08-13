import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import softserveLogo from '../assets/softserve.png';
import { apiFetch } from '../api';

interface AgentState {
  severity?: string;
  owner_team?: string;
  hypothesis?: string;
  plan?: string[];
  actions_taken?: string[];
  pending_checks?: string[];
  evidence?: { tool: string; query: string; result?: string }[];
  fix?: string;
  fix_risk?: string;
  needs_approval?: boolean;
  verification?: string;
  verdict?: string;
}

interface ChatMessage {
  role: 'user' | 'agent';
  text: string;
  sessionId?: string | null;
  needsApproval?: boolean;
  fix?: string;
  fixRisk?: string;
  approvalStatus?: string | null;
}

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'agent', text: '¡Hola! Soy el Copilot de Triage DevOps. Envíame una alerta o descripción de incidente y lo clasificaré, investigaré con logs/métricas, propondré un fix y lo verificaré.' }
  ]);
  const [agentState, setAgentState] = useState<AgentState | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const navigate = useNavigate();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, agentState]);

  // Registra la decisión humana sobre el fix propuesto por el agente.
  const handleApproval = async (index: number, decision: 'approved' | 'rejected') => {
    const msg = messages[index];
    if (!msg?.sessionId || msg.approvalStatus) return;

    setMessages((prev) => prev.map((m, i) => (i === index ? { ...m, approvalStatus: 'pending' } : m)));
    try {
      const response = await apiFetch('/incidents/approval/', {
        method: 'POST',
        body: JSON.stringify({ session_id: msg.sessionId, decision }),
      });
      if (response.ok) {
        setMessages((prev) => prev.map((m, i) => (i === index ? { ...m, approvalStatus: decision } : m)));
      } else {
        setMessages((prev) => prev.map((m, i) => (i === index ? { ...m, approvalStatus: 'error' } : m)));
      }
    } catch {
      setMessages((prev) => prev.map((m, i) => (i === index ? { ...m, approvalStatus: 'error' } : m)));
    }
  };

  const executeSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    setMessages((prev) => [...prev, { role: 'user', text: userMessage }]);
    setIsLoading(true);

    try {
      const response = await apiFetch('/incidents/chat/', {
        method: 'POST',
        body: JSON.stringify({ question: userMessage, session_id: sessionId }),
      });

      const data = await response.json();

      if (response.ok) {
        if (data.session_id) setSessionId(data.session_id);
        setAgentState(data.state);
        const agentMsg = {
          role: 'agent' as const,
          text: data.answer,
          sessionId: data.session_id,
          needsApproval: Boolean(data.state?.needs_approval),
          fix: data.state?.fix || '',
          fixRisk: data.state?.fix_risk || '',
          approvalStatus: null,
        };
        if (data.new_session) {
          // El usuario describió otro incidente: empezamos un hilo limpio.
          setMessages([agentMsg]);
        } else {
          setMessages((prev) => [...prev, agentMsg]);
        }
      } else {
        setMessages((prev) => [...prev, { role: 'agent', text: `Error: ${data.detail || data.error || 'Hubo un problema de conexión.'}` }]);
      }
    } catch {
      setMessages((prev) => [...prev, { role: 'agent', text: 'Error crítico: No se pudo conectar con el backend.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendForm = (e: FormEvent) => {
    e.preventDefault();
    executeSend();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      executeSend();
    }
  };

  const handleInputChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  const startNewSession = () => {
    setSessionId(null);
    setAgentState(null);
    setMessages([
      { role: 'agent', text: 'Nueva sesión de incidente iniciada. Envíame la alerta o descripción.' }
    ]);
  };

  const renderApprovalCard = (msg: ChatMessage, index: number) => {
    if (!msg.needsApproval || !msg.fix) return null;

    let statusContent;
    if (msg.approvalStatus === 'approved') {
      statusContent = <p className="mt-2 text-sm font-medium text-green-400">✓ Fix aprobado y aplicado. Incidente resuelto.</p>;
    } else if (msg.approvalStatus === 'rejected') {
      statusContent = <p className="mt-2 text-sm font-medium text-red-400">✗ Fix rechazado. Incidente reabierto.</p>;
    } else if (msg.approvalStatus === 'error') {
      statusContent = <p className="mt-2 text-sm font-medium text-red-400">Error al registrar la decisión. Intenta de nuevo.</p>;
    } else {
      statusContent = (
        <div className="mt-2 flex gap-2">
          <button
            onClick={() => handleApproval(index, 'approved')}
            disabled={isLoading || msg.approvalStatus === 'pending'}
            className="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-500 text-white text-sm font-medium disabled:opacity-50 transition-colors"
          >
            Aprobar fix
          </button>
          <button
            onClick={() => handleApproval(index, 'rejected')}
            disabled={isLoading || msg.approvalStatus === 'pending'}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-medium disabled:opacity-50 transition-colors"
          >
            Rechazar
          </button>
        </div>
      );
    }

    return (
      <div className="mt-3 p-3 rounded-xl bg-slate-800/80 border border-amber-500/40">
        <p className="text-amber-300 font-semibold mb-1">
          Fix propuesto requiere aprobación
          {msg.fixRisk ? ` (riesgo: ${msg.fixRisk})` : ''}
        </p>
        <p className="whitespace-pre-wrap text-xs text-gray-300">{msg.fix}</p>
        {statusContent}
      </div>
    );
  };

  return (
    <div className="flex min-h-screen bg-slate-900 text-white font-sans">

      <div className="absolute left-6 top-6 flex items-center gap-4">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2 text-gray-400 transition-colors hover:text-white"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Dashboard
        </button>
        <button
          onClick={() => navigate('/incidents')}
          className="flex items-center gap-2 text-gray-400 transition-colors hover:text-white"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
          Incidentes
        </button>
      </div>

      <div className="flex flex-col w-full max-w-5xl mx-auto my-16 bg-white/5 border border-white/10 rounded-2xl shadow-2xl backdrop-blur-sm overflow-hidden">

        <div className="bg-slate-900/80 border-b border-white/10 p-5 flex items-center gap-4">
          <img
            src={softserveLogo}
            alt="Softserve Logo"
            className="h-12 w-12 rounded-xl object-cover shadow-lg bg-white/5 border border-white/10"
          />

          <div className="flex-1">
            <h2 className="text-xl font-bold text-white tracking-tight">Copilot de Incidentes</h2>
            <p className="text-sm text-gray-400 flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              Conectado a Weaviate Vector DB
            </p>
          </div>

          {sessionId && (
            <button
              onClick={startNewSession}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-gray-300 transition-colors hover:bg-white/10 hover:text-white"
            >
              Nueva sesión
            </button>
          )}
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Área de mensajes */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 min-h-[500px] max-h-[600px]">
            {messages.map((msg, index) => (
              <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] p-4 rounded-2xl text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-tr-sm shadow-md'
                      : 'bg-white/5 border border-white/10 text-gray-200 rounded-tl-sm shadow-sm'
                  }`}
                >
                  <span className="whitespace-pre-wrap font-mono">{msg.text}</span>
                  {renderApprovalCard(msg, index)}
                </div>
              </div>
            ))}

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

          {/* Panel de razonamiento del agente */}
          {agentState && (
            <aside className="w-80 border-l border-white/10 overflow-y-auto max-h-[600px] bg-slate-900/40 p-4 space-y-4 text-sm">
              <h3 className="text-xs font-bold uppercase tracking-wider text-purple-400">Razonamiento del agente</h3>

              <div className="flex flex-wrap gap-2">
                <span className={`px-2 py-1 rounded-md text-xs font-semibold ${
                  agentState.severity === 'critical' ? 'bg-red-500/20 text-red-300'
                  : agentState.severity === 'high' ? 'bg-orange-500/20 text-orange-300'
                  : agentState.severity === 'medium' ? 'bg-yellow-500/20 text-yellow-300'
                  : 'bg-blue-500/20 text-blue-300'
                }`}>
                  Severidad: {agentState.severity || 'pending'}
                </span>
                {agentState.owner_team && (
                  <span className="px-2 py-1 rounded-md bg-purple-500/20 text-purple-300 text-xs font-semibold">
                    {agentState.owner_team}
                  </span>
                )}
                {agentState.needs_approval && (
                  <span className="px-2 py-1 rounded-md bg-amber-500/20 text-amber-300 text-xs font-semibold">
                    Requiere aprobación
                  </span>
                )}
              </div>

              <Section title="Hipótesis" value={agentState.hypothesis} />
              <Section title="Fix propuesto" value={agentState.fix} />
              <Section title="Verificación" value={agentState.verification} />

              {agentState.actions_taken && agentState.actions_taken.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-400 mb-1">Acciones tomadas</h4>
                  <ul className="space-y-1">
                    {agentState.actions_taken.map((a, i) => (
                      <li key={i} className="text-xs text-gray-300 flex gap-2">
                        <span className="text-green-400">✓</span> {a}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {agentState.pending_checks && agentState.pending_checks.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-400 mb-1">Checks pendientes</h4>
                  <ul className="space-y-1">
                    {agentState.pending_checks.map((c, i) => (
                      <li key={i} className="text-xs text-gray-300 flex gap-2">
                        <span className="text-amber-400">○</span> {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {agentState.evidence && agentState.evidence.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-400 mb-1">Herramientas usadas</h4>
                  <ul className="space-y-1">
                    {agentState.evidence.map((e, i) => (
                      <li key={i} className="text-xs text-gray-300">
                        <span className="text-purple-400">{e.tool}</span>
                        <span className="text-gray-500"> ← {e.query}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </aside>
          )}
        </div>

        <div className="p-4 bg-slate-900/50 border-t border-white/10">
          <form onSubmit={handleSendForm} className="flex gap-3 items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={sessionId
                ? "Envía una corrección o aprueba el fix... (Shift + Enter para nueva línea)"
                : "Ej: 'El API Gateway está devolviendo 504 en producción'"}
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

function Section({ title, value }: { title: string; value?: string }) {
  if (!value) return null;
  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-400 mb-1">{title}</h4>
      <p className="text-xs text-gray-200 leading-relaxed whitespace-pre-wrap">{value}</p>
    </div>
  );
}
