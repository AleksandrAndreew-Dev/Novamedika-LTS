# 🚀 Автоматический Деплой Pharmacist WebApp

## ✅ Настроено CI/CD

GitHub Actions workflow автоматически собирает и деплоит Pharmacist WebApp при каждом `git push` в ветку `main`.

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
│    - Pharmacist WebApp  │ ← НОВОЕ
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 3. Push в GHCR          │
│    ghcr.io/.../backend  │
│    ghcr.io/.../frontend │
│    ghcr.io/.../         │ ← НОВОЕ
│       pharmacist-webapp │
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
│    - Pharmacist WebApp  │ ← НОВОЕ
│    - Celery Worker      │
└───────────┬─────────────┘
            ↓
✅ Деплой завершен!
```

---

## 🔧 Что было добавлено в workflow

### 1. Сборка Pharmacist WebApp образа

```yaml
- name: Extract metadata for Docker Pharmacist WebApp
  id: meta-pharmacist
  uses: docker/metadata-action@v5
  with:
    images: ghcr.io/aleksandrandreew-dev/novamedika-lts/pharmacist-webapp
    tags: |
      type=sha,prefix=
      type=raw,value=latest
```

### 2. Build & Push с retry логикой

```yaml
- name: Build and push pharmacist webapp image
  uses: docker/build-push-action@v6
  with:
    context: ./frontend
    file: ./frontend/Dockerfile.pharmacist
    push: true
    tags: ${{ steps.meta-pharmacist.outputs.tags }}
```

### 3. Health Check при деплое

```bash
docker exec pharmacist-webapp-prod curl -f http://localhost:80/ || exit 5
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
curl -I https://pharmacist.spravka.novamedika.com
curl -I https://spravka.novamedika.com
curl -I https://api.spravka.novamedika.com/health

# Или откройте в браузере
open https://pharmacist.spravka.novamedika.com
```

---

## 📊 Версионирование образов

### Теги Docker образов

При push в `main`:
```
ghcr.io/aleksandrandreew-dev/novamedika-lts/pharmacist-webapp:latest
ghcr.io/aleksandrandreew-dev/novamedika-lts/pharmacist-webapp:<commit-sha>
```

При создании тега `v1.0.0`:
```
ghcr.io/aleksandrandreew-dev/novamedika-lts/pharmacist-webapp:latest
ghcr.io/aleksandrandreew-dev/novamedika-lts/pharmacist-webapp:v1.0.0
ghcr.io/aleksandrandreew-dev/novamedika-lts/pharmacist-webapp:<commit-sha>
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
2. Проверьте логи: `docker logs pharmacist-webapp-prod`
3. Проверьте Traefik routing: `docker logs traefik-prod | grep pharmacist`

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
# Pharmacist WebApp
ssh user@server "docker logs -f pharmacist-webapp-prod"

# Traefik (routing)
ssh user@server "docker logs -f traefik-prod | grep pharmacist"

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
1. ✅ Автоматически собирается Pharmacist WebApp
2. ✅ Pushится в GitHub Container Registry
3. ✅ Деплоится на production сервер
4. ✅ Проверяется health check
5. ✅ Доступен по адресу `https://pharmacist.spravka.novamedika.com`

**Просто делайте `git push` - всё остальное автоматизировано!** 🚀
