"""
Configuración de Langfuse para trazabilidad del agente de triage.

Usa degradación silenciosa: si las credenciales no están configuradas o el
SDK falla, el agente funciona igual pero sin observabilidad externa.
"""
import logging
import os
from contextlib import contextmanager
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_langfuse_handler():
    """Devuelve el CallbackHandler de Langfuse o None si no está configurado."""
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        logger.info("Langfuse no configurado (faltan LANGFUSE_PUBLIC_KEY/SECRET_KEY).")
        return None
    try:
        from langfuse.langchain import CallbackHandler

        handler = CallbackHandler()
        logger.info("Langfuse handler inicializado correctamente.")
        return handler
    except Exception as e:
        logger.warning("Langfuse no disponible, se continúa sin trazabilidad: %s", e)
        return None


@contextmanager
def trace_context(handler, *, trace_name, session_id, metadata=None, tags=None):
    """Envuelve la ejecución con atributos de trace de Langfuse si hay handler."""
    if handler is None:
        yield
        return
    from langfuse import propagate_attributes

    with propagate_attributes(
        trace_name=trace_name,
        session_id=session_id,
        metadata=metadata or {},
        tags=tags or [],
    ):
        yield
