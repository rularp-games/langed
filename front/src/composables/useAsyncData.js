import { onScopeDispose, ref, shallowRef, watch } from 'vue'
import { ApiError, isAbortError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

/**
 * Загрузка данных с состояниями и отменой устаревших запросов.
 *
 *   const { data, error, loading, reload } = useAsyncData(
 *     (signal) => gamesApi.list({ page: page.value, search: search.value }, { signal }),
 *     { watch: [page, search] },
 *   )
 *
 * - data сохраняет прошлое значение на время перезагрузки (скелет — только при !data);
 * - error — всегда ApiError (или null);
 * - при входе/выходе пользователя данные перезапрашиваются (меняются can_edit и т.п.).
 *
 * @param {(signal: AbortSignal) => Promise<*>} fetcher
 * @param {object} [options]
 * @param {import('vue').WatchSource | import('vue').WatchSource[]} [options.watch]
 * @param {boolean} [options.immediate=true]
 * @param {boolean} [options.reloadOnAuthChange=true]
 */
export function useAsyncData(fetcher, options = {}) {
  const { watch: sources, immediate = true, reloadOnAuthChange = true } = options
  const data = shallowRef(null)
  const error = shallowRef(null)
  const loading = ref(false)
  let controller = null

  async function reload() {
    controller?.abort()
    const current = new AbortController()
    controller = current
    loading.value = true
    error.value = null
    try {
      const result = await fetcher(current.signal)
      if (controller === current) data.value = result
    } catch (err) {
      if (isAbortError(err) || controller !== current) return
      if (!(err instanceof ApiError)) console.error(err)
      error.value = err instanceof ApiError ? err : new ApiError({ status: -1 })
      data.value = null
    } finally {
      if (controller === current) loading.value = false
    }
  }

  if (sources) watch(sources, reload)
  if (reloadOnAuthChange) {
    const auth = useAuthStore()
    watch(
      () => auth.user?.id ?? null,
      () => reload(),
    )
  }
  if (immediate) reload()
  onScopeDispose(() => controller?.abort())

  return { data, error, loading, reload }
}
