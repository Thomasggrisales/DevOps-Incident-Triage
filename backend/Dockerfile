FROM python:3.10-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Dependencias de compilación para paquetes como cryptography, bcrypt, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libpq-dev git && \
    rm -rf /var/lib/apt/lists/*

# Copiamos el archivo de dependencias primero (para optimizar la caché de Docker)
COPY requirements.txt .

# Instalamos las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código del backend
COPY . .

# Exponemos el puerto 8000
EXPOSE 8000

# Comando para iniciar FastAPI (usamos 0.0.0.0 para que sea accesible desde fuera del contenedor)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]