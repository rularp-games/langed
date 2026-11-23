<script setup>
import { watch } from 'vue'
import { Ticket } from '@lucide/vue'
import { eventsApi } from '@/api/events'
import { useAsyncData } from '@/composables/useAsyncData'
import { useQueryParam } from '@/composables/useQueryParam'
import EventCard from '@/components/EventCard.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'

/** Вкладка профиля «Мои конвенты»: проведения, где пользователь участник или организатор. */
const props = defineProps({
  /** upcoming | past */
  time: { type: String, required: true },
})

const PAGE_SIZE = 24

const page = useQueryParam('page', { number: true, default: 1 })

const { data, error, loading, reload } = useAsyncData(
  (signal) => eventsApi.list({ mine: true, time: props.time, page: page.value, pageSize: PAGE_SIZE }, { signal }),
  { watch: [page, () => props.time] },
)

watch(error, (value) => {
  if (value?.status === 404 && page.value > 1) page.value = 1
})
</script>

<template>
  <ErrorState v-if="error" :error="error" title="Не удалось загрузить конвенты" @retry="reload" />

  <ul v-else-if="!data" class="profile-list" aria-busy="true" aria-label="Загрузка конвентов">
    <li v-for="n in 3" :key="n"><AppSkeleton height="120px" radius="lg" /></li>
  </ul>

  <EmptyState
    v-else-if="!data.items.length"
    :icon="Ticket"
    :title="time === 'past' ? 'Прошедших конвентов нет' : 'Предстоящих конвентов нет'"
    :description="
      time === 'past'
        ? 'Здесь появятся конвенты, на которые вы регистрировались или которые организовали.'
        : 'Зарегистрируйтесь на конвент — он появится здесь вместе со статусом заявки.'
    "
  >
    <AppButton variant="primary" :to="{ name: 'conventions' }">Смотреть конвенты</AppButton>
  </EmptyState>

  <template v-else>
    <ul class="profile-list" :class="{ 'is-loading': loading }" :aria-busy="loading">
      <li v-for="event in data.items" :key="event.id">
        <EventCard :event="event" />
      </li>
    </ul>
    <AppPagination
      v-model:page="page"
      class="profile-pagination"
      :count="data.count"
      :page-size="PAGE_SIZE"
      :disabled="loading"
    />
  </template>
</template>

<style scoped>
.profile-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
  transition: opacity var(--duration);
}
.profile-list > li {
  min-width: 0;
}
.profile-list.is-loading {
  opacity: 0.6;
}
.profile-pagination {
  margin-top: var(--space-8);
}

@media (max-width: 519px) {
  .profile-list {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-3);
  }
}
</style>
