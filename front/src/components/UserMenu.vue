<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Building2, ChevronDown, LogOut, UserRound } from '@lucide/vue'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import AppAvatar from './ui/AppAvatar.vue'
import AppMenu from './ui/AppMenu.vue'
import AppMenuItem from './ui/AppMenuItem.vue'

const auth = useAuthStore()
const toast = useToast()
const route = useRoute()
const router = useRouter()
const loggingOut = ref(false)

async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await auth.logout()
    toast.info('Вы вышли из аккаунта')
    if (route.meta.requiresAuth) router.push('/')
  } catch (error) {
    toast.apiError(error, 'Не удалось выйти. Попробуйте ещё раз.')
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <AppMenu label="Аккаунт">
    <template #trigger="{ attrs, toggle }">
      <button v-bind="attrs" type="button" class="user-trigger" @click="toggle">
        <AppAvatar :name="auth.user.displayName" :size="28" />
        <span class="user-trigger__name">{{ auth.user.displayName }}</span>
        <ChevronDown :size="16" class="user-trigger__chevron" aria-hidden="true" />
      </button>
    </template>
    <AppMenuItem to="/profile">
      <UserRound :size="16" aria-hidden="true" />
      Профиль
    </AppMenuItem>
    <AppMenuItem v-if="auth.user.isStaff" :to="{ name: 'cities' }">
      <Building2 :size="16" aria-hidden="true" />
      Города
    </AppMenuItem>
    <AppMenuItem @select="logout">
      <LogOut :size="16" aria-hidden="true" />
      Выйти
    </AppMenuItem>
  </AppMenu>
</template>

<style scoped>
.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: var(--control-h-md);
  padding: 0 var(--space-2) 0 var(--space-1);
  border: 0;
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--text);
  font-weight: 550;
}
.user-trigger:hover {
  background: var(--surface-hover);
}
.user-trigger__name {
  max-width: 14ch;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-trigger__chevron {
  color: var(--text-subtle);
}

@media (max-width: 639px) {
  .user-trigger__name {
    display: none;
  }
}
</style>
