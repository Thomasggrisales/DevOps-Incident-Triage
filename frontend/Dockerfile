FROM node:20-alpine

# Establecemos el directorio de trabajo
WORKDIR /app

# Copiamos los archivos de configuración de npm
COPY package*.json ./

# Instalamos las dependencias de Node
RUN npm install

# Copiamos el resto del código del frontend
COPY . .

# Exponemos el puerto por defecto de Vite
EXPOSE 5173

# Comando para iniciar Vite (necesitamos --host para que se exponga a nuestra máquina real)
CMD ["npm", "run", "dev", "--", "--host"]