<script setup>
import { watch } from 'vue'
import { Dices, Plus } from '@lucide/vue'
import { gamesApi } from '@/api/games'
import { useAsyncData } from '@/composables/useAsyncData'
import { useQueryParam } from '@/composables/useQueryParam'
import GameCard from '@/components/GameCard.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'

/** Вкладка профиля «Мои игры»: игры, где пользователь указан автором. */
const PAGE_SIZE = 24

const page = useQueryParam('page', { number: true, default: 1 })

const { data, error, loading, reload } = useAsyncData(
  (signal) => gamesApi.list({ mine: true, page: page.value, pageSize: PAGE_SIZE }, { signal }),
  { watch: [page] },
)

watch(error, (value) => {
  if (value?.status === 404 && page.value > 1) page.value = 1
})
</script>

<template>
  <ErrorState v-if="error" :error="error" title="Не удалось загрузить игры" @retry="reload" />

  <ul v-else-if="!data" class="profile-games" aria-busy="true" aria-label="Загрузка игр">
    <li v-for="n in 3" :key="n"><AppSkeleton height="160px" radius="lg" /></li>
  </ul>

  <EmptyState
    v-else-if="!data.items.length"
    :icon="Dices"
    title="У вас пока нет игр"
    description="Добавьте свою игру в каталог — её смогут находить игроки и ставить в расписание мастера."
  >
    <AppButton variant="primary" :to="{ name: 'game-new' }">
      <Plus :size="16" aria-hidden="true" />
      Добавить игру
    </AppButton>
    <AppButton :to="{ name: 'games' }">Каталог игр</AppButton>
  </EmptyState>

  <template v-else>
    <ul class="profile-games" :class="{ 'is-loading': loading }" :aria-busy="loading">
      <li v-for="game in data.items" :key="game.id">
        <GameCard :game="game" />
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
.profile-games {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-4);
  transition: opacity var(--duration);
}
.profile-games > li {
  min-width: 0;
}
.profile-games.is-loading {
  opacity: 0.6;
}
.profile-pagination {
  margin-top: var(--space-8);
}

@media (max-width: 519px) {
  .profile-games {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-3);
  }
}
</style>
