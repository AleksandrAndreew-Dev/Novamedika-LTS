FROM node:20-alpine as builder

WORKDIR /app

# Аргументы сборки
ARG VITE_API_URL

# Копируем package files
COPY package*.json ./
# Устанавливаем ВСЕ зависимости для сборки
RUN npm ci

# Копируем исходный код
COPY . .

# Собираем приложение с переменными окружения
RUN VITE_API_URL=${VITE_API_URL} npm run build

FROM nginx:alpine as prod

# Создаём непривилегированного пользователя
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Копируем собранное приложение в nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Копируем кастомную конфигурацию nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Передаём права на файлы nginx пользователю
RUN chown -R appuser:appgroup /usr/share/nginx/html && \
    chown -R appuser:appgroup /var/cache/nginx && \
    chown -R appuser:appgroup /var/log/nginx && \
    chown -R appuser:appgroup /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R appuser:appgroup /var/run/nginx.pid

# Переключаемся на непривилегированного пользователя
USER appuser

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
