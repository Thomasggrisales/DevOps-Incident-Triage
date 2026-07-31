import requests
from app.services.incident import search_incidents_semantic

# Hemos mejorado radicalmente las instrucciones para evitar alucinaciones
template = """Eres un Tech Lead Senior y experto en Desarrollo y DevOps.

INSTRUCCIONES ESTRICTAS:
1. Si el usuario te envía código con errores, tu trabajo es encontrar el error de sintaxis (ej. comillas faltantes, paréntesis, variables no definidas) o de lógica.
2. Asume SIEMPRE que se usan versiones modernas de los lenguajes (ej. Python 3). NUNCA sugieras importaciones antiguas o librerías innecesarias.
3. Muestra el código corregido siempre dentro de bloques de código (```).
4. Sé directo, conciso y no inventes problemas que no existen.
5. Si el usuario pregunta por fallas del sistema, responde usando ÚNICAMENTE el "Contexto".

Contexto (Incidentes recuperados, si aplica):
{context}

Pregunta o código del usuario: {question}

Respuesta experta:"""

def ask_devops_assistant(question: str) -> str:
    # 1. Búsqueda de incidentes
    try:
        search_results = search_incidents_semantic(question, limit=3)
    except Exception:
        search_results = []
    
    context_text = ""
    for inc in search_results:
        context_text += f"- Título: {inc['title']}\n  Estado: {inc['status']}\n  Descripción: {inc['description']}\n\n"
    
    if not context_text.strip():
        context_text = "No se encontraron incidentes. Por favor, analiza el código o responde la duda técnica usando tu conocimiento de Tech Lead."

    final_prompt = template.format(context=context_text, question=question)

    # 2. Conexión a Ollama Local desde dentro de Docker
    # host.docker.internal apunta a tu máquina física (localhost de Windows)
    OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
    
    payload = {
        "model": "mistral", # Cambia esto a "llama3" si prefieres usar ese modelo
        "prompt": final_prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 400
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        
        if response.status_code == 200:
            return response.json()["response"].strip()
        else:
            return f"🚨 Error interno de Ollama ({response.status_code}): {response.text}"
            
    except requests.exceptions.ConnectionError:
        return "🚨 No se pudo conectar a Ollama. Asegúrate de que Ollama esté abierto en tu computadora y funcionando."
    except requests.exceptions.Timeout:
        return "🚨 El modelo de Ollama tardó demasiado en generar la respuesta."
    except Exception as e:
        return f"🚨 Error inesperado: {str(e)}"