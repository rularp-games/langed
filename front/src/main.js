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

async function bootstrap() {
  const app = createApp(App)
  app.use(createPinia())
  app.use(router)

  // Sentry подключается, только если задан DSN (VITE_SENTRY_DSN на этапе сборки);
  // без него библиотека не загружается вовсе.
  const dsn = import.meta.env.VITE_SENTRY_DSN
  if (dsn) {
    try {
      const Sentry = await import('@sentry/vue')
      Sentry.init({
        app,
        dsn,
        integrations: [Sentry.browserTracingIntegration({ router })],
        tracesSampleRate: 0.1,
        environment: import.meta.env.MODE,
      })
    } catch (error) {
      console.error('Sentry не инициализирован', error)
    }
  }

  useUiStore() // применяет сохранённую тему
  useAuthStore().init() // текущий пользователь + CSRF-cookie

  app.mount('#app')
}

bootstrap()
