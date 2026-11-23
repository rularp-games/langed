<script setup>
import { MapPin, Pencil, Trash2, TriangleAlert, UserRound, Users } from '@lucide/vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import { formatMinutes, runBadges, runMastersLabel, runRoomsLabel, runSeatsShort } from './schedule'

/**
 * Расписание одного дня списком по времени — основной вид на телефоне.
 * Прогон ведёт на /runs/:id; в режиме editable у каждой записи есть «Изменить» и «Удалить».
 */
const props = defineProps({
  /** Результат buildDay(). */
  day: { type: Object, required: true },
  editable: Boolean,
  /** {myRuns: Map, userId} — отметки текущего пользователя. */
  context: { type: Object, default: () => ({}) },
  /** Map id прогона → конфликты по помещению (показываются только в редакторе). */
  conflicts: { type: Map, default: () => new Map() },
  /** Текущее время в минутах от полуночи, если этот день — сегодня; иначе null. */
  now: { type: Number, default: null },
})
const emit = defineEmits(['run', 'common', 'remove-run', 'remove-common'])

const isNow = (entry) => props.now !== null && props.now >= entry.start && props.now < entry.end
const isConflict = (run) => props.editable && props.conflicts.has(run.id)

function conflictText(run) {
  return props.conflicts
    .get(run.id)
    .map(({ run: other, room }) => `«${other.game?.name}» (${room.name})`)
    .join(', ')
}
</script>

<template>
  <ol class="slist">
    <li
      v-for="entry in day.items"
      :key="entry.key"
      class="slist__item"
      :class="{
        'slist__item--common': entry.type === 'common',
        'is-mine': entry.type === 'run' && context.myRuns?.has(entry.item.id),
        'is-conflict': entry.type === 'run' && isConflict(entry.item),
        'is-link': entry.type === 'run' && !editable,
      }"
    >
      <p class="slist__time">
        <span class="slist__start">{{ formatMinutes(entry.start) }}</span>
        <span class="slist__end">до {{ formatMinutes(entry.end) }}</span>
      </p>

      <div v-if="entry.type === 'run'" class="slist__body">
        <h4 class="slist__title">
          <RouterLink :to="{ name: 'run', params: { id: entry.item.id } }" class="slist__link">
            {{ entry.item.game?.name }}
          </RouterLink>
        </h4>
        <ul class="slist__meta">
          <li v-if="runRoomsLabel(entry.item)">
            <MapPin :size="14" aria-hidden="true" />
            <span><span class="visually-hidden">Помещение: </span>{{ runRoomsLabel(entry.item) }}</span>
          </li>
          <li v-if="runMastersLabel(entry.item)">
            <UserRound :size="14" aria-hidden="true" />
            <span><span class="visually-hidden">Мастера: </span>{{ runMastersLabel(entry.item) }}</span>
          </li>
          <li v-if="runSeatsShort(entry.item)">
            <Users :size="14" aria-hidden="true" />
            <span><span class="visually-hidden">Занято мест: </span>{{ runSeatsShort(entry.item) }}</span>
          </li>
        </ul>
        <p v-if="isNow(entry) || isConflict(entry.item) || runBadges(entry.item, context).length" class="slist__badges">
          <AppBadge v-if="isNow(entry)" tone="accent">Идёт сейчас</AppBadge>
          <AppBadge v-for="badge in runBadges(entry.item, context)" :key="badge.key" :tone="badge.tone">
            {{ badge.label }}
          </AppBadge>
          <AppBadge v-if="isConflict(entry.item)" tone="danger">
            <TriangleAlert :size="12" aria-hidden="true" />
            Конфликт
          </AppBadge>
        </p>
        <p v-if="isConflict(entry.item)" class="slist__conflict">
          Пересекается по помещению: {{ conflictText(entry.item) }}
        </p>
      </div>

      <div v-else class="slist__body">
        <h4 class="slist__title">{{ entry.item.name }}</h4>
        <p v-if="entry.item.description" class="slist__description prose">{{ entry.item.description }}</p>
        <p v-if="isNow(entry)" class="slist__badges">
          <AppBadge tone="accent">Идёт сейчас</AppBadge>
        </p>
      </div>

      <div v-if="editable" class="slist__actions">
        <AppButton
          size="sm"
          icon-only
          :aria-label="`Изменить: ${entry.type === 'run' ? entry.item.game?.name : entry.item.name}`"
          @click="emit(entry.type === 'run' ? 'run' : 'common', entry.item)"
        >
          <Pencil :size="16" aria-hidden="true" />
        </AppButton>
        <AppButton
          size="sm"
          variant="ghost"
          icon-only
          :aria-label="`Удалить: ${entry.type === 'run' ? entry.item.game?.name : entry.item.name}`"
          @click="emit(entry.type === 'run' ? 'remove-run' : 'remove-common', entry.item)"
        >
          <Trash2 :size="16" aria-hidden="true" />
        </AppButton>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.slist {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  overflow: hidden;
}
.slist__item {
  position: relative;
  display: grid;
  grid-template-columns: 3.75rem minmax(0, 1fr) auto;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-left: 3px solid transparent;
}
.slist__item + .slist__item {
  border-top: 1px solid var(--border);
}
.slist__item--common {
  background: var(--surface-2);
}
.slist__item.is-mine {
  border-left-color: var(--success-text);
}
.slist__item.is-conflict {
  border-left-color: var(--danger-text);
}
.slist__item.is-link:hover {
  background: var(--surface-hover);
}
.slist__time {
  display: flex;
  flex-direction: column;
  font-variant-numeric: tabular-nums;
  line-height: 1.3;
}
.slist__start {
  font-weight: 600;
}
.slist__end {
  color: var(--text-muted);
  font-size: var(--text-xs);
}
.slist__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}
.slist__title {
  font-size: var(--text-base);
  font-weight: 600;
  overflow-wrap: anywhere;
}
.slist__link {
  color: var(--text);
  text-decoration: none;
}
.slist__link:hover {
  color: var(--accent-text);
}
/* Вне редактора вся строка — область ссылки на прогон. */
.is-link .slist__link::after {
  content: '';
  position: absolute;
  inset: 0;
}
.slist__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-4);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.slist__meta li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-1);
  min-width: 0;
}
.slist__meta svg {
  flex: none;
  margin-top: 0.2em;
  color: var(--text-subtle);
}
.slist__badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}
.slist__description {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.slist__conflict {
  color: var(--danger-text);
  font-size: var(--text-sm);
}
.slist__actions {
  display: flex;
  align-items: flex-start;
  gap: var(--space-1);
}

@media (max-width: 519px) {
  .slist__item {
    grid-template-columns: 3rem minmax(0, 1fr) auto;
    gap: var(--space-2);
    padding: var(--space-3);
  }
}
</style>
