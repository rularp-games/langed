import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'

const THEME_KEY = 'langed:theme'
export const THEMES = ['system', 'light', 'dark']

function readStoredTheme() {
  try {
    const value = localStorage.getItem(THEME_KEY)
    return THEMES.includes(value) ? value : 'system'
  } catch {
    return 'system'
  }
}

function applyTheme(theme) {
  const root = document.documentElement
  if (theme === 'system') delete root.dataset.theme
  else root.dataset.theme = theme
}

let nextToastId = 1

/** Состояние интерфейса: тема, уведомления, глобальный диалог подтверждения. */
export const useUiStore = defineStore('ui', () => {
  // --- Тема ---
  const theme = ref(readStoredTheme())
  applyTheme(theme.value)

  function setTheme(value) {
    if (!THEMES.includes(value)) return
    theme.value = value
    applyTheme(value)
    try {
      if (value === 'system') localStorage.removeItem(THEME_KEY)
      else localStorage.setItem(THEME_KEY, value)
    } catch {
      // Хранилище недоступно (приватный режим) — тема действует до перезагрузки.
    }
  }

  // --- Уведомления ---
  const toasts = ref([])

  function pushToast({ type = 'info', message, title = '', timeout } = {}) {
    const id = nextToastId++
    const duration = timeout ?? (type === 'error' ? 8000 : 4500)
    toasts.value.push({ id, type, message, title })
    if (duration > 0) setTimeout(() => dismissToast(id), duration)
    return id
  }

  function dismissToast(id) {
    toasts.value = toasts.value.filter((toast) => toast.id !== id)
  }

  // --- Подтверждение ---
  const confirmState = ref({ open: false, options: {} })
  let confirmResolve = null

  function askConfirm(options = {}) {
    confirmResolve?.(false)
    confirmState.value = { open: true, options }
    return new Promise((resolve) => {
      confirmResolve = resolve
    })
  }

  function settleConfirm(result) {
    confirmState.value = { ...confirmState.value, open: false }
    confirmResolve?.(result)
    confirmResolve = null
  }

  // --- Открытые модальные диалоги (их регистрирует AppDialog) ---
  // Всё вне открытого <dialog> браузер делает неактивным, поэтому уведомления
  // переносятся внутрь верхнего диалога (см. ToastHost).
  const modals = shallowRef([])
  const topModal = computed(() => modals.value[modals.value.length - 1] ?? null)

  function registerModal(element) {
    if (!modals.value.includes(element)) modals.value = [...modals.value, element]
  }

  function unregisterModal(element) {
    modals.value = modals.value.filter((item) => item !== element)
  }

  return {
    topModal,
    registerModal,
    unregisterModal,
    theme,
    setTheme,
    toasts,
    pushToast,
    dismissToast,
    confirmState,
    askConfirm,
    settleConfirm,
  }
})
