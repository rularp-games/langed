import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// Режимы сборки (переменная окружения VUE_BUILD_MODE):
//   standalone — в front/dist с base "/" (контейнер frontend, вызывается из werf);
//   иначе      — в ../langed/static/vue с base "/static/vue/" (Django отдаёт index.html сам).
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const standalone = process.env.VUE_BUILD_MODE === 'standalone'
  const serving = command === 'serve'
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:8000'

  // Заголовок Host не подменяем (changeOrigin: false): Django сверяет его с Origin при проверке
  // CSRF и строит по нему абсолютные адреса постеров.
  const proxy = {}
  for (const prefix of ['/api', '/oidc', '/media', '/admin', '/static']) {
    proxy[prefix] = { target: apiTarget, changeOrigin: false }
  }

  return {
    plugins: [vue()],
    base: serving || standalone ? '/' : '/static/vue/',
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    build: {
      outDir: standalone ? 'dist' : '../langed/static/vue',
      // В django-режиме каталог лежит вне front/ и содержит отслеживаемый .gitkeep — не очищаем.
      emptyOutDir: standalone,
      assetsDir: 'assets',
    },
    server: { proxy },
  }
})
