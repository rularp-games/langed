# Langed — фронтенд

Vue 3 (`<script setup>`) + Vite + vue-router + Pinia.

```
npm install
npm run dev        # dev-сервер; /api, /oidc, /media, /admin, /static проксируются на VITE_API_TARGET (http://localhost:8000)
npm run lint
VUE_BUILD_MODE=standalone npm run build   # сборка в front/dist, base "/" (контейнер frontend)
npm run build                             # сборка в ../langed/static/vue, base "/static/vue/" (Django отдаёт index.html)
```

Переменные окружения — в `.env.example`.

Структура `src/`: `styles/` (токены и базовые стили), `api/` (клиент и модули ресурсов), `stores/`,
`composables/`, `components/ui/` (примитивы), `components/` (составные), `pages/`, `router/`.
