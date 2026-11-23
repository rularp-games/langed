import { useUiStore } from '@/stores/ui'

/**
 * Подтверждение действия (замена confirm() и DeleteConfirmModal).
 *   const confirm = useConfirm()
 *   if (await confirm({ title: 'Удалить игру?', message: '…', confirmText: 'Удалить', danger: true })) …
 */
export function useConfirm() {
  const ui = useUiStore()
  return (options) => ui.askConfirm(options)
}
