import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/**
 * Параметр адресной строки как записываемый ref — состояние списка живёт в URL.
 *
 *   const page = useQueryParam('page', { number: true, default: 1 })
 *   const search = useQueryParam('search', { replace: true, resets: ['page'] })
 *
 * Значение по умолчанию в URL не пишется.
 *
 * @param {string} name
 * @param {object} [options]
 * @param {string|number} [options.default='']
 * @param {boolean} [options.number]   целое положительное число
 * @param {boolean} [options.replace]  не создавать запись в истории (ввод в поиске)
 * @param {string[]} [options.resets]  параметры, сбрасываемые при изменении (обычно page)
 */
export function useQueryParam(name, options = {}) {
  const { default: fallback = '', number = false, replace = false, resets = [] } = options
  const route = useRoute()
  const router = useRouter()

  return computed({
    get() {
      const raw = route.query[name]
      const value = Array.isArray(raw) ? raw[0] : raw
      if (value === undefined || value === null || value === '') return fallback
      if (!number) return value
      const parsed = Number.parseInt(value, 10)
      return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
    },
    set(value) {
      const query = { ...route.query }
      if (value === fallback || value === '' || value === null || value === undefined) {
        delete query[name]
      } else {
        query[name] = String(value)
      }
      for (const key of resets) delete query[key]
      router[replace ? 'replace' : 'push']({ query })
    },
  })
}
