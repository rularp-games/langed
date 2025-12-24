const { defineConfig } = require('@vue/cli-service')
const path = require('path')

// Определяем режим сборки через переменную окружения
const isStandalone = process.env.VUE_BUILD_MODE === 'standalone'

module.exports = defineConfig({
  transpileDependencies: true,
  
  // Билд: standalone (для K8s контейнера) или django (интегрированный)
  outputDir: isStandalone 
    ? path.resolve(__dirname, 'dist')
    : path.resolve(__dirname, '../langed/static/vue'),
  
  // Путь для статики
  publicPath: isStandalone ? '/' : '/static/vue/',
  
  // Отключаем хэши в именах файлов для упрощения
  filenameHashing: false,
  
  // Dev server proxy для API
  devServer: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
