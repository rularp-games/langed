# Langed

## Описание

**Langed** — веб‑приложение для ведения базы **игр**, а также информации о **конвентах** и их проведениях в городах/регионах.  
Состоит из backend‑API и админки на Django и SPA‑фронтенда на Vue 3.

## Стек

- **Backend**: Django + Django REST Framework, uWSGI, nginx
- **Frontend**: Vue 3 + Vue Router (SPA)
- **Авторизация**: OIDC (`mozilla-django-oidc`) + Keycloak
- **Хранилище**: любое поддерживаемое SQL (вообще Postgresql)

## Структура репозитория

- `langed/` — Django‑проект (settings/urls), приложение `server/`, конфиги nginx/uWSGI
- `front/` — фронтенд (Vue 3)
