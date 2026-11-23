<script setup>
import { computed } from 'vue'
import { CalendarDays, MapPin, Ticket, UserRound } from '@lucide/vue'
import { formatDateTime, formatDuration } from '@/utils/datetime'
import { runAvailability, runSeatsLabel } from '@/utils/registration'
import AppBadge from './ui/AppBadge.vue'
import AppCard from './ui/AppCard.vue'
import PosterImage from './PosterImage.vue'
import RegistrationStatusBadge from './RegistrationStatusBadge.vue'

/**
 * Прогон — строка-карточка для афиши, страницы игры, проведения и профиля; ведёт на /runs/:id.
 * Показывает только заполненное. Время — в поясе города прогона (dateLocal), без пересчёта.
 */
const props = defineProps({
  /** Прогон из runsApi (normalizeRun). */
  run: { type: Object, required: true },
  /** false — без названия и постера игры (на странице самой игры). */
  showGame: { type: Boolean, default: true },
  /** false — без названия конвента (на странице проведения). */
  showConvention: { type: Boolean, default: true },
})

const when = computed(() =>
  formatDateTime(props.run.dateLocal, { relative: true, timeZone: props.run.cityTimezone }),
)
const duration = computed(() => formatDuration(props.run.duration))
const place = computed(() => {
  const rooms = props.run.rooms.map((room) => room.name).join(', ')
  return [props.run.cityName, props.run.venueName, rooms].filter(Boolean).join(' · ')
})
const masters = computed(() => props.run.masters.map((master) => master.displayName).join(', '))
const availability = computed(() => runAvailability(props.run))
const seats = computed(() => (availability.value.key === 'past' ? '' : runSeatsLabel(props.run)))
</script>

<template>
  <AppCard as="article" :to="{ name: 'run', params: { id: run.id } }" padding="none" class="run-card">
    <!-- Пустую рамку не рисуем: у большинства игр постера нет. -->
    <PosterImage v-if="showGame && run.game?.poster" :src="run.game.poster" alt="" class="run-card__poster" />
    <div class="run-card__body">
      <p class="run-card__when">
        <CalendarDays :size="16" aria-hidden="true" />
        <span>{{ when }}</span>
        <span v-if="duration" class="run-card__duration">{{ duration }}</span>
      </p>
      <h3 v-if="showGame && run.game" class="run-card__title">{{ run.game.name }}</h3>
      <ul class="run-card__meta">
        <li v-if="place">
          <MapPin :size="14" aria-hidden="true" />
          <span>{{ place }}</span>
        </li>
        <li v-if="masters">
          <UserRound :size="14" aria-hidden="true" />
          <span><span class="visually-hidden">Мастера: </span>{{ masters }}</span>
        </li>
        <li v-if="showConvention && run.conventionName">
          <Ticket :size="14" aria-hidden="true" />
          <span><span class="visually-hidden">Конвент: </span>{{ run.conventionName }}</span>
        </li>
      </ul>
      <div class="run-card__status">
        <RegistrationStatusBadge v-if="run.myRegistration" :status="run.myRegistration.status" mine />
        <AppBadge :tone="availability.tone">{{ availability.label }}</AppBadge>
        <span v-if="seats" class="run-card__seats">{{ seats }}</span>
      </div>
    </div>
  </AppCard>
</template>

<style scoped>
.run-card {
  display: flex;
  height: 100%;
}
.run-card__poster {
  flex: none;
  width: 112px;
  border-right: 1px solid var(--border);
}
.run-card__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
  padding: var(--space-3) var(--space-4);
}
.run-card__when {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1) var(--space-2);
  color: var(--accent-text);
  font-size: var(--text-sm);
  font-weight: 600;
}
.run-card__when svg {
  flex: none;
}
.run-card__duration {
  color: var(--text-subtle);
  font-weight: 400;
}
.run-card__title {
  font-size: var(--text-md);
}
.run-card__meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.run-card__meta li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  min-width: 0;
}
.run-card__meta svg {
  flex: none;
  margin-top: 0.2em;
  color: var(--text-subtle);
}
.run-card__status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-top: auto;
  padding-top: var(--space-1);
}
.run-card__seats {
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 519px) {
  .run-card__poster {
    width: 72px;
  }
  .run-card__body {
    padding: var(--space-3);
  }
}
</style>
