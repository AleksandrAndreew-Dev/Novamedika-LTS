# Инструкция по исправлению ошибки "Нет соединения с сервером"

## Проблема

При заходе на https://spravka.novamedika.com/ появляется ошибка "Нет соединения с сервером. Проверьте интернет."

## Причина

Frontend был собран без правильной переменной окружения `VITE_API_URL`, поэтому API запросы идут по относительным путям (например `/cities/`) вместо абсолютных URL (`https://api.spravka.novamedika.com/cities/`).

Traefik не может маршрутизировать эти запросы, так как они приходят без указания хоста `api.spravka.novamedika.com`.

## Решение

### Вариант 1: Через CI/CD (рекомендуемый)

1. Закоммитить изменения в `.github/workflows/deploy.yml`
2. Создать тег или запушить в main branch
3. GitHub Actions автоматически пересоберет frontend с правильными build-args
4. Обновить production:

```bash
ssh user@server
cd /opt/novamedika-prod
docker compose -f docker-compose.traefik.prod.yml pull frontend
docker compose -f docker-compose.traefik.prod.yml up -d frontend
```

### Вариант 2: Локальная сборка и деплой (быстрый)

Если нужно исправить срочно, можно собрать образ локально:

```bash
# 1. Собрать frontend с правильным VITE_API_URL
cd frontend
docker build --build-arg VITE_API_URL=https://api.spravka.novamedika.com \
             -t ghcr.io/aleksandrandreew-dev/novamedika-lts/frontend:latest \
             -f Dockerfile .

# 2. Запушить в registry
docker push ghcr.io/aleksandrandreew-dev/novamedika-lts/frontend:latest

# 3. Обновить на сервере
ssh user@server
cd /opt/novamedika-prod
docker compose -f docker-compose.traefik.prod.yml pull frontend
docker compose -f docker-compose.traefik.prod.yml up -d frontend
```

### Вариант 3: Временное решение через nginx runtime config (если нужно быстро)

Можно модифицировать nginx.conf для использования runtime переменных через envsubst, но это требует изменений в Dockerfile и не рекомендуется для production.

## Проверка исправления

1. Открыть https://spravka.novamedika.com/ в браузере
2. Открыть DevTools → Network tab
3. Обновить страницу
4. Проверить запрос к `/cities/`:
   - ✅ Правильно: `https://api.spravka.novamedika.com/cities/` (статус 200)
   - ❌ Неправильно: `/cities/` (статус 404)

5. Страница должна загрузиться без ошибок "Нет соединения с сервером"

## Предотвращение в будущем

Изменения в `.github/workflows/deploy.yml` гарантируют, что при каждой сборке frontend будет получать правильные build-args:

```yaml
build-args: |
  VITE_API_URL=https://api.${{ env.DOMAIN }}
```

Это предотвратит повторение проблемы в будущем.

## Технические детали

### Почему environment variables не работают для Vite?

Vite обрабатывает переменные окружения `VITE_*` **во время сборки** (build time), а не во время выполнения (runtime). Они встраиваются непосредственно в JavaScript бандл.

Передача через `environment:` в docker-compose делает переменные доступными только в runtime контейнера, но к этому моменту код уже скомпилирован.

### Архитектура маршрутизации

```
Пользователь → spravka.novamedika.com (frontend)
                    ↓
            API запросы → api.spravka.novamedika.com (backend)
                    ↓
            Traefik маршрутизирует на backend-prod container
```

Без правильного `VITE_API_URL` запросы идут как относительные пути, и Traefik не знает, куда их направлять.