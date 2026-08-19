"""
Cliente MCP para el agente LangGraph.

Carga las tools expuestas por el MCP server como StructuredTools de
LangChain y permite invocarlas por nombre. Si el server no está disponible,
el agente degrada a las tools directas sin romper el flujo.
"""
import asyncio
import logging
import sys

from langchain_mcp_adapters.sessions import StdioConnection
from langchain_mcp_adapters.tools import load_mcp_tools

logger = logging.getLogger(__name__)

_TOOLS_CACHE: dict[str, object] | None = None


def _run_in_new_loop(coro):
    """Ejecuta la corrutina en un event loop nuevo (seguro aunque haya uno activo)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def load_mcp_tools_map() -> dict[str, object]:
    """Devuelve {nombre: StructuredTool} expuestos por el MCP server (cacheado)."""
    global _TOOLS_CACHE
    if _TOOLS_CACHE is not None:
        return _TOOLS_CACHE

    try:
        connection = StdioConnection(
            transport="stdio",
            command=sys.executable,
            args=["-m", "app.mcp.server"],
        )
        tools = _run_in_new_loop(load_mcp_tools(session=None, connection=connection))
        _TOOLS_CACHE = {t.name: t for t in tools}
        logger.info("MCP server conectado. Tools: %s", ", ".join(sorted(_TOOLS_CACHE)))
    except Exception as e:
        logger.warning("MCP server no disponible (%s). El agente usará tools directas.", e)
        _TOOLS_CACHE = {}
    return _TOOLS_CACHE


def _as_text(result) -> str:
    """Convierte el resultado de una tool MCP (bloques de contenido) a texto plano."""
    if isinstance(result, list):
        parts = []
        for item in result:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif item is not None:
                parts.append(str(item))
        if parts:
            return "\n".join(parts)
    return str(result)


def mcp_invoke(name: str, **kwargs) -> str | None:
    """Invoca una tool vía MCP. Devuelve None si MCP no está disponible o la tool no existe."""
    tool = load_mcp_tools_map().get(name)
    if tool is None:
        return None
    try:
        return _as_text(_run_in_new_loop(tool.ainvoke(kwargs)))
    except Exception as e:
        logger.warning("Error invocando la tool MCP '%s': %s", name, e)
        return None
