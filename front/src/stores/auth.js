import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authApi } from '@/api/auth'

/**
 * Пользователь и диалог входа. Компонентам удобнее composable useAuthDialog()
 * (open / requireAuth); хранилище нужно для user / isAuthenticated / logout.
 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  /** true после первого ответа /api/auth/user/ (успешного или нет). */
  const ready = ref(false)
  const providers = ref(null)
  const isAuthenticated = computed(() => user.value !== null)

  let initPromise = null

  /** Загружает текущего пользователя один раз; повторные вызовы возвращают тот же Promise. */
  function init() {
    initPromise ??= refresh()
    return initPromise
  }

  async function refresh() {
    try {
      user.value = await authApi.fetchUser()
    } catch {
      // Сеть или backend недоступны: считаем гостем, страницы покажут свои ошибки.
      user.value = null
    } finally {
      ready.value = true
    }
    return user.value
  }

  async function loadProviders() {
    if (providers.value) return providers.value
    try {
      providers.value = await authApi.fetchProviders()
    } catch {
      // Без соцсетей диалог остаётся рабочим: вход по почте и паролю.
      return []
    }
    return providers.value
  }

  async function login(credentials) {
    user.value = await authApi.login(credentials)
    return user.value
  }

  async function register(payload) {
    user.value = await authApi.register(payload)
    return user.value
  }

  async function logout() {
    await authApi.logout()
    user.value = null
  }

  async function updateProfile(payload) {
    user.value = await authApi.updateProfile(payload)
    return user.value
  }

  // --- Диалог входа ---
  const dialog = ref({ open: false, mode: 'login', reason: '' })
  let waiters = []

  /**
   * Открывает диалог входа. Promise → true, если пользователь вошёл, false — если закрыл.
   * @param {{reason?: string, mode?: 'login'|'register'}} [options]
   */
  function openDialog({ reason = '', mode = 'login' } = {}) {
    if (isAuthenticated.value) return Promise.resolve(true)
    dialog.value = { open: true, mode, reason }
    return new Promise((resolve) => waiters.push(resolve))
  }

  function closeDialog(success = false) {
    dialog.value = { ...dialog.value, open: false }
    const pending = waiters
    waiters = []
    pending.forEach((resolve) => resolve(success))
  }

  /**
   * Выполняет действие, требующее входа: гостю сначала показывает диалог и продолжает
   * после успешного входа. Возвращает результат action либо undefined, если вход отменён.
   */
  async function requireAuth(action, options) {
    await init()
    if (!isAuthenticated.value) {
      const ok = await openDialog(options)
      if (!ok) return undefined
    }
    return action()
  }

  return {
    user,
    ready,
    providers,
    isAuthenticated,
    init,
    refresh,
    loadProviders,
    login,
    register,
    logout,
    updateProfile,
    dialog,
    openDialog,
    closeDialog,
    requireAuth,
  }
})
