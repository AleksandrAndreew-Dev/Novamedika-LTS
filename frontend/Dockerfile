FROM node:20-alpine as builder

WORKDIR /app

# Аргументы сборки
ARG VITE_API_URL
ARG VITE_TELEGRAM_BOT_TOKEN

# Копируем package files
COPY package*.json ./
# Устанавливаем ВСЕ зависимости для сборки
RUN npm ci

# Копируем исходный код
COPY . .

# Собираем приложение с переменными окружения
RUN VITE_API_URL=${VITE_API_URL} VITE_TELEGRAM_BOT_TOKEN=${VITE_TELEGRAM_BOT_TOKEN} npm run build

FROM nginx:alpine as prod

# Копируем собранное приложение в nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Копируем кастомную конфигурацию nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
