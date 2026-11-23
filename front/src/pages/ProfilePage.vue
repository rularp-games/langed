<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { KeyRound, LogOut, Pencil } from '@lucide/vue'
import { useQueryParam } from '@/composables/useQueryParam'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import ProfileEvents from '@/components/profile/ProfileEvents.vue'
import ProfileGames from '@/components/profile/ProfileGames.vue'
import ProfileNameDialog from '@/components/profile/ProfileNameDialog.vue'
import ProfilePasswordDialog from '@/components/profile/ProfilePasswordDialog.vue'
import ProfileRuns from '@/components/profile/ProfileRuns.vue'
import AppAvatar from '@/components/ui/AppAvatar.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppTabs from '@/components/ui/AppTabs.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'

const TABS = [
  { value: 'runs', label: 'Мои записи' },
  { value: 'events', label: 'Мои конвенты' },
  { value: 'games', label: 'Мои игры' },
]
const TIME_OPTIONS = [
  { value: 'upcoming', label: 'Предстоящие' },
  { value: 'past', label: 'Прошедшие' },
]

const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

// Вкладка и период живут в адресной строке: /profile?tab=events&time=past
const tabParam = useQueryParam('tab', { default: 'runs', resets: ['page'] })
const tab = computed({
  get: () => (TABS.some((item) => item.value === tabParam.value) ? tabParam.value : 'runs'),
  set: (value) => (tabParam.value = value),
})
const timeParam = useQueryParam('time', { default: 'upcoming', replace: true, resets: ['page'] })
const time = computed({
  get: () => (timeParam.value === 'past' ? 'past' : 'upcoming'),
  set: (value) => (timeParam.value = value),
})

// Почту не дублируем, если она же служит именем.
const email = computed(() => {
  const user = auth.user
  return user?.email && user.email !== user.displayName ? user.email : ''
})

const loggingOut = ref(false)
const nameDialogOpen = ref(false)
const passwordDialogOpen = ref(false)

async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await auth.logout()
    toast.info('Вы вышли из аккаунта')
    router.push({ name: 'afisha' })
  } catch (err) {
    toast.apiError(err, 'Не удалось выйти. Попробуйте ещё раз.')
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <div v-if="auth.user" class="container profile">
    <header class="profile__header">
      <AppAvatar :name="auth.user.displayName" :size="56" />
      <div class="profile__identity">
        <h1>{{ auth.user.displayName }}</h1>
        <p v-if="email || auth.user.isStaff" class="profile__meta">
          <span v-if="email" class="profile__email">{{ email }}</span>
          <AppBadge v-if="auth.user.isStaff" tone="accent">Администратор</AppBadge>
        </p>
      </div>
      <div class="profile__actions">
        <AppButton @click="nameDialogOpen = true">
          <Pencil :size="16" aria-hidden="true" />
          Изменить имя
        </AppButton>
        <!-- Пароль есть только у вошедших по почте и паролю; у входа через соцсеть его меняют там. -->
        <AppButton v-if="auth.user.hasPasswordLogin" @click="passwordDialogOpen = true">
          <KeyRound :size="16" aria-hidden="true" />
          Сменить пароль
        </AppButton>
        <AppButton variant="ghost" :loading="loggingOut" @click="logout">
          <LogOut :size="16" aria-hidden="true" />
          Выйти
        </AppButton>
      </div>
    </header>

    <div class="profile__bar">
      <AppTabs v-model="tab" :tabs="TABS" label="Разделы профиля" class="profile__tabs" />
      <SegmentedControl v-if="tab !== 'games'" v-model="time" :options="TIME_OPTIONS" label="Период" size="sm" />
    </div>

    <div class="profile__panel" role="tabpanel" :aria-label="TABS.find((item) => item.value === tab).label">
      <ProfileRuns v-if="tab === 'runs'" :time="time" />
      <ProfileEvents v-else-if="tab === 'events'" :time="time" />
      <ProfileGames v-else />
    </div>

    <ProfileNameDialog v-model:open="nameDialogOpen" />
    <ProfilePasswordDialog v-model:open="passwordDialogOpen" />
  </div>
</template>

<style scoped>
.profile {
  padding-bottom: var(--space-10);
}
.profile__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3) var(--space-4);
  padding-block: var(--space-5) var(--space-4);
}
.profile__identity {
  flex: 1 1 200px;
  min-width: 0;
}
.profile__identity h1 {
  overflow-wrap: anywhere;
}
.profile__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.profile__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1) var(--space-3);
  margin-top: var(--space-1);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.profile__email {
  min-width: 0;
  overflow-wrap: anywhere;
}
.profile__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}
.profile__tabs {
  flex: 1 1 auto;
  min-width: 0;
}
</style>
