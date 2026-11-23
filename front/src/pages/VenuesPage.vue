<script setup>
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { MapPinned, Plus } from '@lucide/vue'
import { venuesApi } from '@/api/venues'
import { useAsyncData } from '@/composables/useAsyncData'
import { useQueryParam } from '@/composables/useQueryParam'
import { useAuthStore } from '@/stores/auth'
import { useCitiesStore } from '@/stores/cities'
import { plural } from '@/utils/format'
import CitySelect from '@/components/CitySelect.vue'
import VenueCard from '@/components/venue/VenueCard.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'

const PAGE_SIZE = 24

const router = useRouter()
const auth = useAuthStore()
const cities = useCitiesStore()

// Состояние списка живёт в адресной строке: /venues?search=…&city=3&page=2
const page = useQueryParam('page', { number: true, default: 1 })
const search = useQueryParam('search', { replace: true, resets: ['page'] })
const city = useQueryParam('city', { number: true, default: '', resets: ['page'] })

const { data, error, loading, reload } = useAsyncData(
  (signal) =>
    venuesApi.list({ page: page.value, pageSize: PAGE_SIZE, search: search.value, city: city.value || undefined }, { signal }),
  { watch: [page, search, city] },
)

// Страница за пределами списка (устаревшая ссылка) — возвращаемся на первую.
watch(error, (value) => {
  if (value?.status === 404 && page.value > 1) page.value = 1
})

const filtered = computed(() => Boolean(search.value || city.value))
const cityName = computed(() => cities.byId(city.value)?.name ?? '')

const countLabel = computed(() => {
  if (!data.value) return ''
  const { count } = data.value
  return `${count} ${plural(count, ['площадка', 'площадки', 'площадок'])}`
})

const emptyDescription = computed(() => {
  if (!filtered.value) return 'Добавьте первую площадку — её можно будет выбрать при создании конвента или прогона.'
  const parts = []
  if (search.value) parts.push(`по запросу «${search.value}»`)
  if (cityName.value) parts.push(`в городе ${cityName.value}`)
  return `Площадок ${parts.join(' ') || 'с такими условиями'} нет. Измените условия поиска.`
})

function resetFilters() {
  // Один переход вместо двух последовательных записей в query.
  router.replace({ query: {} })
}
</script>

<template>
  <div class="container">
    <PageHeader title="Площадки">
      <template v-if="countLabel" #meta>{{ countLabel }}</template>
      <template v-if="auth.isAuthenticated" #actions>
        <AppButton variant="primary" :to="{ name: 'venue-new' }">
          <Plus :size="16" aria-hidden="true" />
          Добавить площадку
        </AppButton>
      </template>
      <SearchInput v-model="search" label="Поиск по площадкам" placeholder="Название или адрес" />
      <CitySelect v-model="city" class="venues-city" aria-label="Город" />
    </PageHeader>

    <ErrorState v-if="error" :error="error" title="Не удалось загрузить площадки" @retry="reload" />

    <ul v-else-if="!data" class="venues-grid" aria-busy="true" aria-label="Загрузка площадок">
      <li v-for="n in 6" :key="n" class="venues-grid__skeleton">
        <AppSkeleton height="100%" radius="lg" />
      </li>
    </ul>

    <EmptyState
      v-else-if="!data.items.length"
      :icon="MapPinned"
      :title="filtered ? 'Ничего не нашлось' : 'Площадок пока нет'"
      :description="emptyDescription"
    >
      <AppButton v-if="filtered" @click="resetFilters">Сбросить фильтры</AppButton>
    </EmptyState>

    <template v-else>
      <ul class="venues-grid" :class="{ 'is-loading': loading }" :aria-busy="loading">
        <li v-for="venue in data.items" :key="venue.id">
          <VenueCard :venue="venue" />
        </li>
      </ul>
      <AppPagination
        v-model:page="page"
        class="venues-pagination"
        :count="data.count"
        :page-size="PAGE_SIZE"
        :disabled="loading"
      />
    </template>
  </div>
</template>

<style scoped>
.venues-city {
  flex: 0 1 220px;
  min-width: 0;
}
.venues-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
  transition: opacity var(--duration);
}
.venues-grid > li {
  min-width: 0;
}
.venues-grid.is-loading {
  opacity: 0.6;
}
.venues-grid__skeleton {
  height: 112px;
}
.venues-pagination {
  margin-top: var(--space-8);
}

@media (max-width: 519px) {
  .venues-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-3);
  }
  .venues-city {
    flex-basis: 100%;
  }
}
</style>
