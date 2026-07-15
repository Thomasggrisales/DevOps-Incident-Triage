import os
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
from app.services.incident import search_incidents_semantic

# 1. Configurar el LLM de Hugging Face
# Asegúrate de que HUGGINGFACEHUB_API_TOKEN esté en tu .env
llm = HuggingFaceEndpoint(
    repo_id="mistralai/Mistral-7B-Instruct-v0.2",
    task="text-generation",
    max_new_tokens=250,
    temperature=0.1, 
)

# 2. Crear el Prompt Template adaptado
template = """Eres un asistente experto en DevOps y Triage de Incidentes. 
Tu tarea es responder preguntas sobre problemas del sistema basándote ÚNICAMENTE en el contexto proporcionado.
Si la respuesta no está en el contexto, di "No tengo información suficiente en la base de datos de incidentes."
Sé conciso y profesional.

Contexto (Incidentes recuperados de Weaviate):
{context}

Pregunta del usuario: {question}

Respuesta experta:"""

prompt = PromptTemplate.from_template(template)

# 3. Construir la cadena
chain = prompt | llm

# 4. Función principal de RAG
def ask_devops_assistant(question: str) -> str:
    search_results = search_incidents_semantic(question, limit=3)
    
    context_text = ""
    for inc in search_results:
        context_text += f"- Título: {inc['title']}\n  Estado: {inc['status']}\n  Descripción: {inc['description']}\n\n"
        
    if not context_text:
        return "No se encontraron incidentes relacionados en la base de datos para analizar."

    response = chain.invoke({
        "context": context_text,
        "question": question
    })
    
    return response.strip()