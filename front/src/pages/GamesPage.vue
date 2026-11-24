<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Dices, Plus, Upload } from '@lucide/vue'
import { gamesApi } from '@/api/games'
import { useAsyncData } from '@/composables/useAsyncData'
import { useAuthDialog } from '@/composables/useAuthDialog'
import { useQueryParam } from '@/composables/useQueryParam'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { plural } from '@/utils/format'
import { DEFAULT_GAME_KIND, GAME_KINDS, gameKind } from '@/utils/game'
import GameCard from '@/components/GameCard.vue'
import GameImportDialog from '@/components/game/GameImportDialog.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'

const PAGE_SIZE = 24
const SORT_OPTIONS = [
  { value: 'new', label: 'Новые' },
  { value: 'name', label: 'По названию' },
]
const ORDERING = { new: '-created_at', name: 'name' }
// Тип игры: по умолчанию каталог показывает только КРИ; «Все» — без фильтра.
const KIND_OPTIONS = [...GAME_KINDS.map(({ value, label }) => ({ value, label })), { value: 'all', label: 'Все' }]

const router = useRouter()
const auth = useAuthStore()
const toast = useToast()
const { requireAuth } = useAuthDialog()

// Состояние списка живёт в адресной строке: /games?search=…&page=2
const page = useQueryParam('page', { number: true, default: 1 })
const search = useQueryParam('search', { replace: true, resets: ['page'] })
// Сортировка: /games?ordering=name; по умолчанию — новые первыми.
const ordering = useQueryParam('ordering', { default: 'new', resets: ['page'] })
const sort = computed({
  get: () => (ordering.value in ORDERING ? ordering.value : 'new'),
  set: (value) => (ordering.value = value),
})
// Тип: /games?kind=ttrpg, /games?kind=all; по умолчанию — КРИ.
const kindParam = useQueryParam('kind', { default: DEFAULT_GAME_KIND, resets: ['page'] })
const kind = computed({
  get: () => (KIND_OPTIONS.some((option) => option.value === kindParam.value) ? kindParam.value : DEFAULT_GAME_KIND),
  set: (value) => (kindParam.value = value),
})
const kindLabel = computed(() => (kind.value === 'all' ? '' : gameKind(kind.value).label))

const { data, error, loading, reload } = useAsyncData(
  (signal) =>
    gamesApi.list(
      {
        page: page.value,
        pageSize: PAGE_SIZE,
        search: search.value,
        ordering: ORDERING[sort.value],
        kind: kind.value === 'all' ? undefined : kind.value,
      },
      { signal },
    ),
  { watch: [page, search, sort, kind] },
)

// Страница за пределами списка (устаревшая ссылка) — возвращаемся на первую.
watch(error, (value) => {
  if (value?.status === 404 && page.value > 1) page.value = 1
})

const countLabel = computed(() => {
  if (!data.value) return ''
  const { count } = data.value
  return `${count} ${plural(count, ['игра', 'игры', 'игр'])}`
})

const importOpen = ref(false)

function onImported(result) {
  toast.success(`Импортировано игр: ${result.created}`)
  reload()
}

function addGame() {
  requireAuth(() => router.push({ name: 'game-new' }), {
    reason: 'Войдите, чтобы добавить игру в каталог.',
  })
}
</script>

<template>
  <div class="container">
    <PageHeader title="Игры">
      <template v-if="countLabel" #meta>{{ countLabel }}</template>
      <template #actions>
        <AppButton v-if="auth.user?.isStaff" @click="importOpen = true">
          <Upload :size="16" aria-hidden="true" />
          Импорт из CSV
        </AppButton>
        <AppButton variant="primary" @click="addGame">
          <Plus :size="16" aria-hidden="true" />
          Добавить игру
        </AppButton>
      </template>
      <SearchInput v-model="search" label="Поиск по играм" placeholder="Название игры" />
      <SegmentedControl v-model="kind" :options="KIND_OPTIONS" label="Тип игры" size="sm" />
      <SegmentedControl v-model="sort" :options="SORT_OPTIONS" label="Сортировка" size="sm" />
    </PageHeader>

    <GameImportDialog v-if="auth.user?.isStaff" v-model:open="importOpen" @imported="onImported" />

    <ErrorState v-if="error" :error="error" title="Не удалось загрузить игры" @retry="reload" />

    <ul v-else-if="!data" class="games-grid" aria-busy="true" aria-label="Загрузка игр">
      <li v-for="n in 8" :key="n" class="games-grid__skeleton">
        <AppSkeleton height="100%" radius="lg" />
      </li>
    </ul>

    <EmptyState
      v-else-if="!data.items.length"
      :icon="Dices"
      :title="search ? 'Ничего не нашлось' : kindLabel ? 'Игр этого типа пока нет' : 'Игр пока нет'"
      :description="
        search
          ? `По запросу «${search}»${kindLabel ? ` среди «${kindLabel}»` : ''} игр нет. Проверьте написание или попробуйте другое название.`
          : kindLabel
            ? `В каталоге пока нет игр типа «${kindLabel}».`
            : 'Добавьте первую игру в каталог.'
      "
    >
      <AppButton v-if="search" @click="search = ''">Сбросить поиск</AppButton>
      <AppButton v-if="kindLabel" @click="kind = 'all'">Показать все типы</AppButton>
    </EmptyState>

    <template v-else>
      <ul class="games-grid" :class="{ 'is-loading': loading }" :aria-busy="loading">
        <li v-for="game in data.items" :key="game.id">
          <GameCard :game="game" />
        </li>
      </ul>
      <AppPagination
        v-model:page="page"
        class="games-pagination"
        :count="data.count"
        :page-size="PAGE_SIZE"
        :disabled="loading"
      />
    </template>
  </div>
</template>

<style scoped>
.games-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-4);
  transition: opacity var(--duration);
}
.games-grid > li {
  min-width: 0;
}
.games-grid.is-loading {
  opacity: 0.6;
}
.games-grid__skeleton {
  height: 180px;
}
.games-pagination {
  margin-top: var(--space-8);
}

@media (max-width: 519px) {
  .games-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-3);
  }
  .games-grid__skeleton {
    height: 116px;
  }
}
</style>
