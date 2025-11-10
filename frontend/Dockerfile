# Dev stage
FROM node:20-alpine AS dev
WORKDIR /app

# Установка curl для healthcheck
RUN apk add --no-cache curl

# Копируем package.json и устанавливаем зависимости
COPY package.json ./
RUN npm install

# Копируем остальные файлы
COPY vite.config.js ./
COPY index.html ./
COPY src/ ./src/
COPY public/ ./public/

EXPOSE 5173

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:5173/ || exit 1

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
