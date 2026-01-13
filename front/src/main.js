import { createApp } from 'vue'
import * as Sentry from '@sentry/vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// Initialize Sentry for error tracking
// Set SENTRY_DSN environment variable or replace with your DSN
const SENTRY_DSN = process.env.VUE_APP_SENTRY_DSN || ''

if (SENTRY_DSN) {
  Sentry.init({
    app,
    dsn: SENTRY_DSN,
    integrations: [
      Sentry.browserTracingIntegration({ router }),
    ],
    // Set tracesSampleRate to capture performance data
    // Adjust this value in production (0.0 to 1.0)
    tracesSampleRate: 0.1,
    // Set the environment
    environment: process.env.NODE_ENV || 'development',
  })
}

app.use(router).mount('#app')
