<script setup>
import { computed, watch } from 'vue'
import { CalendarDays } from '@lucide/vue'
import { runsApi } from '@/api/runs'
import { useAsyncData } from '@/composables/useAsyncData'
import { useQueryParam } from '@/composables/useQueryParam'
import { useAuthStore } from '@/stores/auth'
import RunCard from '@/components/RunCard.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'

/** Вкладка профиля «Мои записи»: прогоны, где пользователь играет и где он мастер. */
const props = defineProps({
  /** upcoming | past */
  time: { type: String, required: true },
})

const PAGE_SIZE = 48

const auth = useAuthStore()
const page = useQueryParam('page', { number: true, default: 1 })

const { data, error, loading, reload } = useAsyncData(
  (signal) => runsApi.list({ mine: true, time: props.time, page: page.value, pageSize: PAGE_SIZE }, { signal }),
  { watch: [page, () => props.time] },
)

watch(error, (value) => {
  if (value?.status === 404 && page.value > 1) page.value = 1
})

const groups = computed(() => {
  const items = data.value?.items ?? []
  const userId = auth.user?.id
  return [
    { key: 'player', title: 'Я играю', runs: items.filter((run) => run.myRegistration) },
    {
      key: 'master',
      title: 'Я мастер',
      runs: items.filter((run) => !run.myRegistration && run.masters.some((master) => master.id === userId)),
    },
  ].filter((group) => group.runs.length)
})
</script>

<template>
  <ErrorState v-if="error" :error="error" title="Не удалось загрузить записи" @retry="reload" />

  <ul v-else-if="!data" class="profile-list" aria-busy="true" aria-label="Загрузка записей">
    <li v-for="n in 3" :key="n"><AppSkeleton height="120px" radius="lg" /></li>
  </ul>

  <EmptyState
    v-else-if="!groups.length"
    :icon="CalendarDays"
    :title="time === 'past' ? 'Прошедших игр нет' : 'Предстоящих игр нет'"
    :description="
      time === 'past'
        ? 'Здесь появятся прогоны, в которых вы участвовали или которые вели.'
        : 'Запишитесь на прогон в афише или назначьте свой — он появится здесь.'
    "
  >
    <AppButton variant="primary" :to="{ name: 'afisha' }">Открыть афишу</AppButton>
  </EmptyState>

  <div v-else class="profile-groups" :class="{ 'is-loading': loading }" :aria-busy="loading">
    <section v-for="group in groups" :key="group.key" :aria-labelledby="`profile-runs-${group.key}`">
      <h2 :id="`profile-runs-${group.key}`" class="profile-groups__title">
        {{ group.title }}
        <span class="profile-groups__count">{{ group.runs.length }}</span>
      </h2>
      <ul class="profile-list">
        <li v-for="run in group.runs" :key="run.id">
          <RunCard :run="run" />
        </li>
      </ul>
    </section>
    <AppPagination v-model:page="page" :count="data.count" :page-size="PAGE_SIZE" :disabled="loading" />
  </div>
</template>

<style scoped>
.profile-groups {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  transition: opacity var(--duration);
}
.profile-groups.is-loading {
  opacity: 0.6;
}
.profile-groups__title {
  margin-bottom: var(--space-3);
  font-size: var(--text-md);
}
.profile-groups__count {
  margin-left: var(--space-1);
  color: var(--text-subtle);
  font-weight: 400;
}
.profile-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
}
.profile-list > li {
  min-width: 0;
}

@media (max-width: 519px) {
  .profile-list {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-3);
  }
}
</style>
