<script setup>
import { computed } from 'vue'
import { CalendarDays, Dices, MapPin } from '@lucide/vue'
import { formatDateRange } from '@/utils/datetime'
import { plural } from '@/utils/format'
import { eventAvailability, eventSeatsLabel } from '@/utils/registration'
import AppBadge from './ui/AppBadge.vue'
import AppCard from './ui/AppCard.vue'
import RegistrationStatusBadge from './RegistrationStatusBadge.vue'

/** Проведение конвента — карточка для афиши, списка конвентов и профиля; ведёт на /events/:id. */
const props = defineProps({
  /** Проведение из eventsApi (normalizeEvent). */
  event: { type: Object, required: true },
  /** false — без названия конвента (на странице самого конвента). */
  showName: { type: Boolean, default: true },
})

const dates = computed(() => formatDateRange(props.event.dateStart, props.event.dateEnd))
const place = computed(() => [props.event.cityName, props.event.venueName].filter(Boolean).join(' · '))
const runs = computed(() => {
  const count = props.event.runsCount
  return count ? `${count} ${plural(count, ['прогон', 'прогона', 'прогонов'])}` : ''
})
const availability = computed(() => eventAvailability(props.event))
const seats = computed(() => (availability.value.key === 'open' ? eventSeatsLabel(props.event) : ''))
</script>

<template>
  <AppCard as="article" :to="{ name: 'event', params: { id: event.id } }" class="event-card">
    <p class="event-card__dates">
      <CalendarDays :size="16" aria-hidden="true" />
      {{ dates }}
    </p>
    <h3 v-if="showName" class="event-card__title">{{ event.conventionName }}</h3>
    <ul class="event-card__meta">
      <li v-if="place">
        <MapPin :size="14" aria-hidden="true" />
        <span>{{ place }}</span>
      </li>
      <li v-if="runs">
        <Dices :size="14" aria-hidden="true" />
        <span>{{ runs }}</span>
      </li>
    </ul>
    <div class="event-card__status">
      <RegistrationStatusBadge v-if="event.myRegistration" :status="event.myRegistration.status" mine />
      <AppBadge :tone="availability.tone">{{ availability.label }}</AppBadge>
      <span v-if="seats" class="event-card__seats">{{ seats }}</span>
    </div>
  </AppCard>
</template>

<style scoped>
.event-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  height: 100%;
}
.event-card__dates {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--accent-text);
  font-size: var(--text-sm);
  font-weight: 600;
}
.event-card__title {
  font-size: var(--text-md);
}
.event-card__meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.event-card__meta li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
}
.event-card__meta svg {
  flex: none;
  margin-top: 0.2em;
  color: var(--text-subtle);
}
.event-card__status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-top: auto;
  padding-top: var(--space-1);
}
.event-card__seats {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
</style>
