import { ApiError } from '@/api/client'
import { useUiStore } from '@/stores/ui'

/**
 * Уведомления (замена alert()).
 *   const toast = useToast()
 *   toast.success('Игра сохранена')
 *   toast.apiError(error, 'Не удалось сохранить игру')
 */
export function useToast() {
  const ui = useUiStore()
  const push = (type) => (message, options = {}) => ui.pushToast({ ...options, type, message })
  const error = push('error')
  return {
    success: push('success'),
    info: push('info'),
    warning: push('warning'),
    error,
    /** Показывает сообщение из ApiError либо запасной текст. */
    apiError(err, fallback = 'Что-то пошло не так. Попробуйте ещё раз.') {
      return error(err instanceof ApiError ? err.detail : fallback)
    },
    dismiss: ui.dismissToast,
  }
}
