<script setup>
import { watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { socialErrorMessage } from '@/api/auth'
import { useToast } from '@/composables/useToast'
import AppFooter from '@/components/AppFooter.vue'
import AppHeader from '@/components/AppHeader.vue'
import AuthDialog from '@/components/AuthDialog.vue'
import ConfirmHost from '@/components/ConfirmHost.vue'
import ToastHost from '@/components/ui/ToastHost.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

// Возврат из соцсети с ошибкой: /games?auth_error=<code> — показываем и убираем из адреса.
watch(
  () => route.query.auth_error,
  (code) => {
    if (!code) return
    toast.error(socialErrorMessage([code].flat()[0]))
    const query = { ...route.query }
    delete query.auth_error
    router.replace({ path: route.path, query, hash: route.hash })
  },
  { immediate: true },
)
</script>

<template>
  <a href="#main" class="skip-link">Перейти к содержимому</a>
  <AppHeader />
  <main id="main" class="main" tabindex="-1">
    <RouterView />
  </main>
  <AppFooter />
  <AuthDialog />
  <ConfirmHost />
  <ToastHost />
</template>

<style scoped>
.main {
  flex: 1;
  outline: none;
}
.skip-link {
  position: absolute;
  top: var(--space-2);
  left: var(--space-2);
  z-index: 100;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--shadow-md);
  transform: translateY(-200%);
}
.skip-link:focus {
  transform: none;
}
</style>
