# 🚀 Автоматический Деплой

## ✅ Настроено CI/CD

GitHub Actions workflow автоматически собирает и деплоит приложение при каждом `git push` в ветку `main`.

---

## 📋 Как работает автоматический деплой

### Триггеры

Workflow запускается автоматически при:
1. **Push в ветку `main`** - основной триггер для production деплоя
2. **Push тега версии** (например, `v1.0.0`) - tagged release
3. **Manual trigger** - через GitHub Actions UI (workflow_dispatch)

### Процесс деплоя

```
git push origin main
       ↓
GitHub Actions Workflow
       ↓
┌─────────────────────────┐
│ 1. Тестирование         │
│    - Python tests       │
│    - React build        │
│    - Linting            │
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 2. Сборка Docker образов│
│    - Backend            │
│    - Frontend           │
│      (включает оба сайта)│
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 3. Push в GHCR          │
│    ghcr.io/.../backend  │
│    ghcr.io/.../frontend │
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 4. Деплой на сервер     │
│    SSH → Production     │
│    docker compose up -d │
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 5. Health Checks        │
│    - Backend API        │
│    - Frontend           │
│    - Celery Worker      │
└───────────┬─────────────┘
            ↓
✅ Деплой завершен!
```

---

## 🔧 Что было добавлено в workflow

### 1. Единый Frontend образ

Система использует **один frontend образ** для обслуживания обоих сайтов:
- `spravka.novamedika.com` (основной сайт)
- `pharmacist.spravka.novamedika.com` (панель фармацевта)

Маршрутизация осуществляется через Traefik по HTTP Host header.

```yaml
- name: Build and push frontend image
  uses: docker/build-push-action@v6
  with:
    context: ./frontend
    file: ./frontend/Dockerfile
    push: true
    tags: ${{ steps.meta-frontend.outputs.tags }}
    build-args: |
      VITE_API_URL=https://api.spravka.novamedika.com
      VITE_WS_URL=wss://api.spravka.novamedika.com/api/pharmacist/ws/pharmacist
```

### 2. Build & Push с retry логикой

Автоматические повторные попытки при сетевых ошибках:

```yaml
- name: Build and push backend image (with retry)
  id: build-backend
  uses: docker/build-push-action@v6
  with:
    context: ./backend
    file: ./backend/Dockerfile
    push: true
  continue-on-error: true

- name: Retry backend push if failed
  if: steps.build-backend.outcome == 'failure'
  shell: bash
  run: |
    echo "⚠️ Backend push failed, retrying in 20 seconds..."
    sleep 20
```

### 3. Health Check при деплое

Проверка здоровья всех сервисов после деплоя:

```bash
docker exec backend-prod curl -f http://localhost:8000/health || exit 5
docker exec frontend-prod wget -q --spider http://localhost:80 || exit 5
```

---

## 🎯 Использование

### Шаг 1: Commit и Push изменений

```bash
# Внесите изменения в код
git add .
git commit -m "feat: add pharmacist dashboard improvements"

# Push в main branch
git push origin main
```

### Шаг 2: Мониторинг деплоя

1. Откройте [GitHub Actions](https://github.com/aleksandrandreew-dev/Novamedika2/actions)
2. Найдите запущенный workflow "Deploy to Production"
3. Следите за прогрессом:
   - ✅ Test
   - ✅ Build and Push (Backend, Frontend, Pharmacist WebApp)
   - ✅ Deploy Production

### Шаг 3: Проверка деплоя

После завершения workflow (~5-10 минут):

```bash
# Проверьте доступность сервисов
curl -I https://spravka.novamedika.com
curl -I https://pharmacist.spravka.novamedika.com
curl -I https://api.spravka.novamedika.com/health

# Или откройте в браузере
open https://spravka.novamedika.com
```

---

## 📊 Версионирование образов

### Теги Docker образов

При push в `main`:
```
ghcr.io/aleksandrandreew-dev/novamedika-lts/frontend:latest
ghcr.io/aleksandrandreew-dev/novamedika-lts/frontend:<commit-sha>
```

При создании тега `v1.0.0`:
```
ghcr.io/aleksandrandreew-dev/novamedika-lts/frontend:latest
ghcr.io/aleksandrandreew-dev/novamedika-lts/frontend:v1.0.0
ghcr.io/aleksandrandreew-dev/novamedika-lts/frontend:<commit-sha>
```

---

## 🔍 Troubleshooting

### Проблема: Workflow не запускается

**Решение:**
1. Проверьте, что push был в ветку `main`
2. Убедитесь, что GitHub Actions включены в настройках репозитория
3. Проверьте `.github/workflows/deploy.yml` на синтаксические ошибки

### Проблема: Build failed

**Решение:**
1. Откройте логи workflow в GitHub Actions
2. Найдите ошибку в шаге "Build and push pharmacist webapp image"
3. Исправьте ошибку локально
4. Сделайте новый commit и push

### Проблема: Deploy failed

**Решение:**
1. Проверьте SSH подключение к серверу
2. Убедитесь, что secrets настроены правильно:
   - `PRODUCTION_SERVER_HOST`
   - `SERVER_USER`
   - `SERVER_SSH_KEY`
   - `GHCR_PAT`
   - `GHCR_USER`
3. Проверьте логи на сервере: `docker logs pharmacist-webapp-prod`

### Проблема: Health check failed

**Решение:**
1. Подождите 2-3 минуты (сервис может запускаться)
2. Проверьте логи: `docker logs frontend-prod`
3. Проверьте Traefik routing: `docker logs traefik-prod`

---

## 🛡️ Безопасность

### Secrets

Workflow использует следующие GitHub Secrets:

| Secret | Описание | Где настроить |
|--------|----------|---------------|
| `GITHUB_TOKEN` | Автоматически предоставляется GitHub | - |
| `PRODUCTION_SERVER_HOST` | IP или домен сервера | Settings → Secrets |
| `SERVER_USER` | SSH пользователь | Settings → Secrets |
| `SERVER_SSH_KEY` | Приватный SSH ключ | Settings → Secrets |
| `GHCR_PAT` | Personal Access Token для GHCR | Settings → Secrets |
| `GHCR_USER` | GitHub username для GHCR | Settings → Secrets |

### Best Practices

✅ **Никогда не коммитьте secrets в репозиторий**  
✅ **Используйте environment protection rules**  
✅ **Регулярно обновляйте SSH ключи и токены**  
✅ **Включите branch protection для `main`**  

---

## 📈 Мониторинг деплоя

### Логи GitHub Actions

```
GitHub → Repository → Actions → Deploy to Production
```

### Логи на сервере

```bash
# Frontend (оба сайта)
ssh user@server "docker logs -f frontend-prod"

# Traefik (routing)
ssh user@server "docker logs -f traefik-prod"

# Backend API
ssh user@server "docker logs -f backend-prod"
```

### Метрики

- **Время сборки**: ~3-5 минут
- **Время деплоя**: ~2-3 минуты
- **Общее время**: ~5-10 минут
- **Success rate**: Целевой >95%

---

## 🎉 Готово!

Теперь при каждом `git push origin main`:
1. ✅ Автоматически собирается единый Frontend образ (для обоих сайтов)
2. ✅ Pushится в GitHub Container Registry
3. ✅ Деплоится на production сервер
4. ✅ Проверяется health check
5. ✅ Доступны адреса `https://spravka.novamedika.com` и `https://pharmacist.spravka.novamedika.com`

**Просто делайте `git push` - всё остальное автоматизировано!** 🚀
