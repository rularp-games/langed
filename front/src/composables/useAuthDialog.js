import { useAuthStore } from '@/stores/auth'

/**
 * Диалог входа из любой точки приложения.
 *   const { open, requireAuth } = useAuthDialog()
 *   open({ reason: 'Войдите, чтобы записаться на игру' })       // Promise<boolean>
 *   requireAuth(() => signUp(run), { reason: '…' })             // действие продолжится после входа
 */
export function useAuthDialog() {
  const auth = useAuthStore()
  return {
    open: auth.openDialog,
    close: () => auth.closeDialog(false),
    requireAuth: auth.requireAuth,
  }
}
