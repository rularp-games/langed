import { createApp } from 'vue'
import { createPinia } from 'pinia'
import '@fontsource-variable/inter/wght.css'
import './styles/tokens.css'
import './styles/base.css'
import './styles/controls.css'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import { useUiStore } from './stores/ui'

/**
 * Sentry: DSN и окружение отдаёт бэкенд (/api/config/) — у dev и prod они свои, а образ один.
 * Без DSN библиотека не загружается вовсе.
 */
async function initSentry(app) {
  try {
    const response = await fetch('/api/config/', { credentials: 'same-origin' })
    if (!response.ok) return
    const { sentry } = await response.json()
    if (!sentry?.dsn) return
    const Sentry = await import('@sentry/vue')
    Sentry.init({
      app,
      dsn: sentry.dsn,
      environment: sentry.environment,
      integrations: [Sentry.browserTracingIntegration({ router })],
      tracesSampleRate: 0.1,
    })
  } catch (error) {
    console.error('Sentry не инициализирован', error)
  }
}

async function bootstrap() {
  const app = createApp(App)
  app.use(createPinia())
  app.use(router)

  initSentry(app) // не задерживает первую отрисовку

  useUiStore() // применяет сохранённую тему
  useAuthStore().init() // текущий пользователь + CSRF-cookie

  app.mount('#app')
}

bootstrap()
