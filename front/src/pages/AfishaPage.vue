<script setup>
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { CalendarDays, Plus } from '@lucide/vue'
import { eventsApi } from '@/api/events'
import { runsApi } from '@/api/runs'
import { useAsyncData } from '@/composables/useAsyncData'
import { useAuthDialog } from '@/composables/useAuthDialog'
import { useQueryParam } from '@/composables/useQueryParam'
import { useAuthStore } from '@/stores/auth'
import { dateKey, formatDate, relativeDay } from '@/utils/datetime'
import { plural } from '@/utils/format'
import CitySelect from '@/components/CitySelect.vue'
import EventCard from '@/components/EventCard.vue'
import RunCard from '@/components/RunCard.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppCheckbox from '@/components/ui/AppCheckbox.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'

const PAGE_SIZE = 24
const EVENTS_LIMIT = 4
const RECENT_LIMIT = 6
const TIME_OPTIONS = [
  { value: 'upcoming', label: 'Предстоящие' },
  { value: 'past', label: 'Прошедшие' },
]

const router = useRouter()
const auth = useAuthStore()
const { requireAuth } = useAuthDialog()

// Состояние афиши живёт в адресной строке: /?time=past&city=1&standalone=1&page=2
const page = useQueryParam('page', { number: true, default: 1 })
const timeParam = useQueryParam('time', { default: 'upcoming', resets: ['page'] })
const cityParam = useQueryParam('city', { number: true, resets: ['page'] })
const standaloneParam = useQueryParam('standalone', { resets: ['page'] })

const time = computed({
  get: () => (timeParam.value === 'past' ? 'past' : 'upcoming'),
  set: (value) => (timeParam.value = value),
})
// <select> отдаёт выбранный id как есть (число) либо '' для «Все города».
const city = computed({
  get: () => cityParam.value,
  set: (value) => (cityParam.value = value),
})
const standalone = computed({
  get: () => standaloneParam.value === '1',
  set: (value) => (standaloneParam.value = value ? '1' : ''),
})
const hasFilters = computed(() => Boolean(city.value) || standalone.value)

const { data: cities } = useAsyncData((signal) => runsApi.cities({ signal }), { reloadOnAuthChange: false })

// Ближайшие конвенты — вспомогательный блок: при ошибке просто не показывается.
const { data: events } = useAsyncData(
  (signal) =>
    eventsApi.list({ time: 'upcoming', pageSize: EVENTS_LIMIT, city: city.value || undefined }, { signal }),
  { watch: [city] },
)

const { data, error, loading, reload } = useAsyncData(
  async (signal) => {
    const filters = { city: city.value || undefined, standalone: standalone.value }
    const result = await runsApi.list(
      { ...filters, time: time.value, page: page.value, pageSize: PAGE_SIZE },
      { signal },
    )
    // Предстоящих нет — показываем вместо пустоты последние прошедшие прогоны.
    let recent = []
    if (time.value === 'upcoming' && !result.count) {
      recent = (await runsApi.list({ ...filters, time: 'past', pageSize: RECENT_LIMIT }, { signal })).items
    }
    return { ...result, time: time.value, recent }
  },
  { watch: [page, time, city, standalone] },
)

// Страница за пределами списка (устаревшая ссылка) — возвращаемся на первую.
watch(error, (value) => {
  if (value?.status === 404 && page.value > 1) page.value = 1
})

const countLabel = computed(() => {
  if (!data.value?.count) return ''
  const { count } = data.value
  return `${count} ${plural(count, ['прогон', 'прогона', 'прогонов'])}`
})

/** Прогоны страницы по дням (в поясе города каждого прогона): [{ key, relative, date, runs }]. */
const days = computed(() => {
  const groups = new Map()
  for (const run of data.value?.items ?? []) {
    const key = dateKey(run.dateLocal)
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        relative: relativeDay(run.dateLocal, { timeZone: run.cityTimezone }),
        date: formatDate(run.dateLocal, { weekday: true }),
        runs: [],
      })
    }
    groups.get(key).runs.push(run)
  }
  return [...groups.values()]
})

const emptyUpcoming = computed(() => {
  if (hasFilters.value) {
    return {
      title: 'По этим условиям предстоящих прогонов нет',
      description: 'Попробуйте другой город или посмотрите, что уже прошло.',
    }
  }
  return {
    title: 'Новых прогонов пока не объявлено',
    description: auth.isAuthenticated
      ? 'Как только мастера назначат даты, игры появятся здесь. Собираетесь провести игру сами — добавьте прогон.'
      : 'Как только мастера назначат даты, игры появятся здесь. А пока можно посмотреть, что проходило раньше.',
  }
})

function resetFilters() {
  router.push({ query: time.value === 'past' ? { time: 'past' } : {} })
}

function addRun() {
  requireAuth(() => router.push({ name: 'run-new' }), {
    reason: 'Войдите, чтобы добавить прогон.',
  })
}
</script>

<template>
  <div class="container">
    <PageHeader title="Афиша">
      <template v-if="countLabel" #meta>{{ countLabel }}</template>
      <template #actions>
        <AppButton variant="primary" @click="addRun">
          <Plus :size="16" aria-hidden="true" />
          Добавить прогон
        </AppButton>
      </template>
    </PageHeader>

    <section v-if="events?.items.length && page === 1" class="afisha-events" aria-labelledby="afisha-events-title">
      <div class="afisha-section-head">
        <h2 id="afisha-events-title">Ближайшие конвенты</h2>
        <RouterLink :to="{ name: 'conventions' }">Все конвенты</RouterLink>
      </div>
      <ul class="afisha-events__list">
        <li v-for="event in events.items" :key="event.id">
          <EventCard :event="event" />
        </li>
      </ul>
    </section>

    <section aria-labelledby="afisha-runs-title">
      <h2 id="afisha-runs-title" class="visually-hidden">Прогоны</h2>
      <div class="afisha-filters">
        <SegmentedControl v-model="time" :options="TIME_OPTIONS" label="Период" />
        <CitySelect v-model="city" :cities="cities ?? []" class="afisha-filters__city" aria-label="Город" />
        <AppCheckbox v-model="standalone" class="afisha-filters__standalone">Без прогонов конвентов</AppCheckbox>
      </div>

      <ErrorState v-if="error" :error="error" title="Не удалось загрузить афишу" @retry="reload" />

      <ul v-else-if="!data" class="afisha-grid" aria-busy="true" aria-label="Загрузка прогонов">
        <li v-for="n in 6" :key="n" class="afisha-grid__skeleton">
          <AppSkeleton height="100%" radius="lg" />
        </li>
      </ul>

      <template v-else-if="!data.items.length">
        <EmptyState
          v-if="data.time === 'upcoming'"
          :icon="CalendarDays"
          :title="emptyUpcoming.title"
          :description="emptyUpcoming.description"
        >
          <AppButton variant="primary" @click="time = 'past'">Посмотреть прошедшие</AppButton>
          <AppButton v-if="hasFilters" @click="resetFilters">Сбросить фильтры</AppButton>
          <AppButton v-else-if="auth.isAuthenticated" :to="{ name: 'run-new' }">
            <Plus :size="16" aria-hidden="true" />
            Добавить прогон
          </AppButton>
        </EmptyState>
        <EmptyState
          v-else
          :icon="CalendarDays"
          title="Прошедших прогонов нет"
          :description="hasFilters ? 'По выбранным условиям ничего не нашлось.' : ''"
        >
          <AppButton v-if="hasFilters" @click="resetFilters">Сбросить фильтры</AppButton>
        </EmptyState>

        <section v-if="data.recent.length" class="afisha-recent" aria-labelledby="afisha-recent-title">
          <div class="afisha-section-head">
            <h2 id="afisha-recent-title">Недавно прошли</h2>
            <RouterLink :to="{ query: { ...$route.query, time: 'past', page: undefined } }">Все прошедшие</RouterLink>
          </div>
          <ul class="afisha-grid">
            <li v-for="run in data.recent" :key="run.id">
              <RunCard :run="run" />
            </li>
          </ul>
        </section>
      </template>

      <template v-else>
        <div class="afisha-days" :class="{ 'is-loading': loading }" :aria-busy="loading">
          <section v-for="day in days" :key="day.key" :aria-labelledby="`afisha-day-${day.key}`">
            <h3 :id="`afisha-day-${day.key}`" class="afisha-day__title">
              <template v-if="day.relative">
                {{ day.relative }} <span class="afisha-day__date">{{ day.date }}</span>
              </template>
              <template v-else>{{ day.date }}</template>
            </h3>
            <ul class="afisha-grid">
              <li v-for="run in day.runs" :key="run.id">
                <RunCard :run="run" />
              </li>
            </ul>
          </section>
        </div>
        <AppPagination
          v-model:page="page"
          class="afisha-pagination"
          :count="data.count"
          :page-size="PAGE_SIZE"
          :disabled="loading"
        />
      </template>
    </section>
  </div>
</template>

<style scoped>
.afisha-section-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-1) var(--space-4);
  margin-bottom: var(--space-3);
}
.afisha-section-head h2 {
  font-size: var(--text-md);
}
.afisha-section-head a {
  font-size: var(--text-sm);
}
.afisha-events {
  margin-bottom: var(--space-8);
}
.afisha-events__list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-4);
}
.afisha-events__list > li,
.afisha-grid > li {
  min-width: 0;
}
.afisha-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3) var(--space-4);
  margin-bottom: var(--space-5);
}
.afisha-filters__city {
  width: 220px;
  max-width: 100%;
}
.afisha-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--space-4);
}
.afisha-grid__skeleton {
  height: 148px;
}
.afisha-days {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  transition: opacity var(--duration);
}
.afisha-days.is-loading {
  opacity: 0.6;
}
.afisha-day__title {
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border);
  font-size: var(--text-md);
}
.afisha-day__title::first-letter {
  text-transform: uppercase;
}
.afisha-day__date {
  margin-left: var(--space-1);
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: 400;
}
.afisha-recent {
  margin-top: var(--space-2);
}
.afisha-pagination {
  margin-top: var(--space-8);
}

@media (max-width: 519px) {
  .afisha-events__list,
  .afisha-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-3);
  }
  .afisha-filters__city {
    flex: 1;
    width: auto;
    min-width: 160px;
  }
  .afisha-grid__skeleton {
    height: 132px;
  }
}
</style>
