<script setup>
import { computed } from 'vue'
import { DoorOpen, MapPin, Users } from '@lucide/vue'
import { plural } from '@/utils/format'
import AppCard from '@/components/ui/AppCard.vue'

/** Площадка — карточка списка; ведёт на /venues/:id. Показывает только заполненное. */
const props = defineProps({
  /** Площадка из venuesApi (normalizeVenue). */
  venue: { type: Object, required: true },
})

const place = computed(() => [props.venue.city?.name, props.venue.address].filter(Boolean).join(', '))
const capacity = computed(() => {
  const n = props.venue.capacity
  return n ? `До ${n} ${plural(n, ['человека', 'человек', 'человек'])}` : ''
})
const rooms = computed(() => {
  const n = props.venue.rooms.length
  return n ? `${n} ${plural(n, ['помещение', 'помещения', 'помещений'])}` : ''
})
</script>

<template>
  <AppCard as="article" :to="{ name: 'venue', params: { id: venue.id } }" class="venue-card">
    <h2 class="venue-card__title">{{ venue.name }}</h2>
    <ul class="venue-card__meta">
      <li v-if="place">
        <MapPin :size="14" aria-hidden="true" />
        <span>{{ place }}</span>
      </li>
      <li v-if="capacity">
        <Users :size="14" aria-hidden="true" />
        <span><span class="visually-hidden">Вместимость: </span>{{ capacity }}</span>
      </li>
      <li v-if="rooms">
        <DoorOpen :size="14" aria-hidden="true" />
        <span>{{ rooms }}</span>
      </li>
    </ul>
  </AppCard>
</template>

<style scoped>
.venue-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  height: 100%;
}
.venue-card__title {
  font-size: var(--text-md);
  overflow-wrap: anywhere;
}
.venue-card__meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.venue-card__meta li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  min-width: 0;
}
.venue-card__meta span {
  min-width: 0;
  overflow-wrap: anywhere;
}
.venue-card__meta svg {
  flex: none;
  margin-top: 0.2em;
  color: var(--text-subtle);
}
</style>
