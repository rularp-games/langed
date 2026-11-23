<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { CalendarPlus, ChevronDown } from '@lucide/vue'
import { runsApi } from '@/api/runs'
import { useAsyncData } from '@/composables/useAsyncData'
import { useAuthDialog } from '@/composables/useAuthDialog'
import RunCard from '@/components/RunCard.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import ErrorState from '@/components/ui/ErrorState.vue'

/** Блок «Прогоны» на странице игры: предстоящие, раскрываемые прошедшие и кнопка «Назначить прогон». */
const props = defineProps({
  gameId: { type: [Number, String], required: true },
})

const PAGE_SIZE = 10

const router = useRouter()
const { requireAuth } = useAuthDialog()

const upcomingPage = ref(1)
const pastPage = ref(1)
const showPast = ref(false)

const upcoming = useAsyncData(
  (signal) =>
    runsApi.list({ game: props.gameId, time: 'upcoming', page: upcomingPage.value, pageSize: PAGE_SIZE }, { signal }),
  { watch: [() => props.gameId, upcomingPage] },
)

// Прошедшие прогоны загружаются только после раскрытия.
const past = useAsyncData(
  (signal) =>
    showPast.value
      ? runsApi.list({ game: props.gameId, time: 'past', page: pastPage.value, pageSize: PAGE_SIZE }, { signal })
      : Promise.resolve(null),
  { watch: [() => props.gameId, pastPage, showPast] },
)

watch(
  () => props.gameId,
  () => {
    upcomingPage.value = 1
    pastPage.value = 1
    showPast.value = false
  },
)

function scheduleRun() {
  requireAuth(() => router.push({ name: 'run-new', query: { game: props.gameId } }), {
    reason: 'Войдите, чтобы назначить прогон игры.',
  })
}
</script>

<template>
  <section class="game-runs" aria-labelledby="game-runs-title">
    <div class="game-runs__head">
      <h2 id="game-runs-title">Прогоны</h2>
      <AppButton size="sm" @click="scheduleRun">
        <CalendarPlus :size="16" aria-hidden="true" />
        Назначить прогон
      </AppButton>
    </div>

    <ErrorState
      v-if="upcoming.error.value"
      :error="upcoming.error.value"
      title="Не удалось загрузить прогоны"
      @retry="upcoming.reload"
    />
    <div v-else-if="!upcoming.data.value" aria-busy="true" aria-label="Загрузка прогонов">
      <AppSkeleton height="96px" radius="lg" />
    </div>
    <p v-else-if="!upcoming.data.value.items.length" class="text-muted">Ближайших прогонов нет.</p>
    <template v-else>
      <ul class="game-runs__list" :aria-busy="upcoming.loading.value">
        <li v-for="run in upcoming.data.value.items" :key="run.id">
          <RunCard :run="run" :show-game="false" />
        </li>
      </ul>
      <AppPagination
        v-model:page="upcomingPage"
        :count="upcoming.data.value.count"
        :page-size="PAGE_SIZE"
        :disabled="upcoming.loading.value"
      />
    </template>

    <div class="game-runs__past">
      <button
        type="button"
        class="game-runs__toggle"
        :aria-expanded="showPast"
        aria-controls="game-runs-past"
        @click="showPast = !showPast"
      >
        <ChevronDown :size="16" aria-hidden="true" class="game-runs__chevron" :class="{ 'is-open': showPast }" />
        Прошедшие прогоны
        <span v-if="past.data.value" class="game-runs__count">{{ past.data.value.count }}</span>
      </button>
      <div v-if="showPast" id="game-runs-past" class="game-runs__past-body">
        <ErrorState
          v-if="past.error.value"
          :error="past.error.value"
          title="Не удалось загрузить прошедшие прогоны"
          @retry="past.reload"
        />
        <div v-else-if="!past.data.value" aria-busy="true" aria-label="Загрузка прошедших прогонов">
          <AppSkeleton height="96px" radius="lg" />
        </div>
        <p v-else-if="!past.data.value.items.length" class="text-muted">Эту игру ещё не проводили.</p>
        <template v-else>
          <ul class="game-runs__list" :aria-busy="past.loading.value">
            <li v-for="run in past.data.value.items" :key="run.id">
              <RunCard :run="run" :show-game="false" />
            </li>
          </ul>
          <AppPagination
            v-model:page="pastPage"
            :count="past.data.value.count"
            :page-size="PAGE_SIZE"
            :disabled="past.loading.value"
          />
        </template>
      </div>
    </div>
  </section>
</template>

<style scoped>
.game-runs {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-width: 0;
}
.game-runs__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-3);
}
.game-runs__head h2 {
  margin: 0;
  font-size: var(--text-md);
}
.game-runs__list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-3);
}
.game-runs__list > li {
  min-width: 0;
}
.game-runs__past {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border);
}
.game-runs__past-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.game-runs__toggle {
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  gap: var(--space-2);
  min-height: var(--control-h-sm);
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-weight: 550;
}
.game-runs__toggle:hover {
  color: var(--text);
}
.game-runs__chevron {
  transition: transform var(--duration);
}
.game-runs__chevron.is-open {
  transform: rotate(180deg);
}
.game-runs__count {
  color: var(--text-subtle);
  font-weight: 400;
}

@media (max-width: 519px) {
  .game-runs__list {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
