<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { CalendarX } from '@lucide/vue'
import { useQueryParam } from '@/composables/useQueryParam'
import { formatDate, formatTimeRange, relativeDay } from '@/utils/datetime'
import AppButton from '@/components/ui/AppButton.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import ScheduleGrid from './ScheduleGrid.vue'
import ScheduleList from './ScheduleList.vue'
import { NO_ROOM, buildDay, eventDays, findConflicts, nowInZone, scheduleRooms } from './schedule'

/**
 * Расписание проведения: переключатель «Сетка / Список», фильтры по дню и помещению, дни по порядку.
 * Вид и фильтры живут в адресной строке (?view=&day=&room=). На узком экране по умолчанию — список.
 * Используется и на странице проведения, и в редакторе расписания (editable).
 */
const props = defineProps({
  /** Проведение с расписанием (eventsApi.schedule). */
  event: { type: Object, required: true },
  editable: Boolean,
  /** id прогона → статус моей заявки (pending | confirmed | waitlist). */
  myRuns: { type: Map, default: () => new Map() },
  /** id текущего пользователя — для отметки «Вы мастер». */
  userId: { type: Number, default: null },
})
const emit = defineEmits(['add-run', 'edit-run', 'remove-run', 'edit-common', 'remove-common'])

const VIEWS = [
  { value: 'grid', label: 'Сетка' },
  { value: 'list', label: 'Список' },
]
const NARROW = '(max-width: 700px)'

const viewParam = useQueryParam('view', { replace: true })
const dayParam = useQueryParam('day', { replace: true })
const roomParam = useQueryParam('room', { replace: true })

// Узкий экран и текущее время: обновляются, пока страница открыта.
const narrow = ref(false)
const now = ref(nowInZone(props.event.cityTimezone))
let media = null
let timer = null
const onMedia = (query) => (narrow.value = query.matches)
onMounted(() => {
  media = window.matchMedia(NARROW)
  narrow.value = media.matches
  media.addEventListener('change', onMedia)
  timer = setInterval(() => (now.value = nowInZone(props.event.cityTimezone)), 30000)
})
onBeforeUnmount(() => {
  media?.removeEventListener('change', onMedia)
  clearInterval(timer)
})

const days = computed(() => eventDays(props.event))
const rooms = computed(() => scheduleRooms(props.event))
const conflicts = computed(() => (props.editable ? findConflicts(props.event.runs) : new Map()))
const context = computed(() => ({ myRuns: props.myRuns, userId: props.userId }))
const hasItems = computed(() => props.event.runs.length > 0 || props.event.commonEvents.length > 0)

const view = computed({
  get: () => (VIEWS.some((item) => item.value === viewParam.value) ? viewParam.value : narrow.value ? 'list' : 'grid'),
  set: (value) => (viewParam.value = value),
})

// День: по умолчанию участнику показываем сегодняшний день конвента, организатору — все.
const day = computed({
  get() {
    if (dayParam.value === 'all' || days.value.includes(dayParam.value)) return dayParam.value
    return !props.editable && days.value.includes(now.value.day) ? now.value.day : 'all'
  },
  set: (value) => (dayParam.value = value),
})

const roomValue = (room) => (room.id === NO_ROOM ? 'none' : String(room.id))
const room = computed({
  get: () => (rooms.value.some((item) => roomValue(item) === roomParam.value) ? roomParam.value : ''),
  set: (value) => (roomParam.value = value),
})

const dayLabel = (key) => formatDate(key, { weekday: true })
const dayOptions = computed(() => [
  { value: 'all', label: 'Все дни' },
  ...days.value.map((key) => ({ value: key, label: dayLabel(key) })),
])
const roomOptions = computed(() => rooms.value.map((item) => ({ value: roomValue(item), label: item.name })))

const shownRooms = computed(() =>
  room.value ? rooms.value.filter((item) => roomValue(item) === room.value) : rooms.value,
)

/** Дни к показу: выбранный — всегда; из всех — только непустые (в редакторе сетки — все дни проведения). */
const shownDays = computed(() => {
  const keys = day.value === 'all' ? days.value : [day.value]
  return keys
    .map((key) => buildDay(props.event, key, { rooms: shownRooms.value, editable: props.editable }))
    .filter((item) => !item.isEmpty || day.value !== 'all' || (props.editable && view.value === 'grid'))
})

const nowFor = (item) => (item.day === now.value.day ? now.value.minutes : null)
const relative = (key) => relativeDay(key, { timeZone: props.event.cityTimezone })

/** Сбрасывает по одному условию за раз: сначала помещение (чаще всего пусто из-за него), затем день. */
function resetFilters() {
  if (room.value) room.value = ''
  else day.value = 'all'
}

// Общее событие на странице проведения открывается небольшим окном с описанием.
const openedCommon = ref(null)
const commonOpen = computed({
  get: () => openedCommon.value !== null,
  set: (value) => {
    if (!value) openedCommon.value = null
  },
})

function onCommon(item) {
  if (props.editable) emit('edit-common', item)
  else openedCommon.value = item
}
</script>

<template>
  <div class="schedule">
    <EmptyState
      v-if="!hasItems && !editable"
      :icon="CalendarX"
      title="Расписание ещё не составлено"
      description="Организаторы пока не добавили прогоны и события. Загляните позже."
    >
      <slot name="empty-actions" />
    </EmptyState>

    <template v-else>
      <div class="schedule__toolbar">
        <SegmentedControl v-model="view" :options="VIEWS" label="Вид расписания" size="sm" />
        <div class="schedule__filters">
          <AppSelect v-if="days.length > 1" v-model="day" :options="dayOptions" size="sm" aria-label="День" />
          <AppSelect
            v-if="rooms.length > 1"
            v-model="room"
            :options="roomOptions"
            placeholder="Все помещения"
            size="sm"
            aria-label="Помещение"
          />
        </div>
      </div>

      <div v-if="!shownDays.length" class="schedule__nothing">
        <p>
          {{
            hasItems
              ? 'По выбранным условиям в расписании ничего нет.'
              : 'В расписании пока ничего нет. Добавьте первый прогон или общее событие.'
          }}
        </p>
        <AppButton v-if="hasItems && (room || day !== 'all')" size="sm" @click="resetFilters">Сбросить фильтр</AppButton>
      </div>

      <section v-for="item in shownDays" :key="item.day" class="schedule__day" :aria-labelledby="`day-${item.day}`">
        <h3 :id="`day-${item.day}`" class="schedule__day-title">
          {{ dayLabel(item.day) }}
          <span v-if="relative(item.day)" class="schedule__day-relative">{{ relative(item.day) }}</span>
        </h3>

        <ScheduleGrid
          v-if="view === 'grid'"
          :day="item"
          :label="`Расписание на ${dayLabel(item.day)}`"
          :editable="editable"
          :context="context"
          :conflicts="conflicts"
          :now="nowFor(item)"
          @run="emit('edit-run', $event)"
          @common="onCommon"
          @add="emit('add-run', { day: item.day, ...$event })"
        />
        <p v-else-if="item.isEmpty" class="schedule__nothing">В этот день в расписании ничего нет.</p>
        <ScheduleList
          v-else
          :day="item"
          :editable="editable"
          :context="context"
          :conflicts="conflicts"
          :now="nowFor(item)"
          @run="emit('edit-run', $event)"
          @common="onCommon"
          @remove-run="emit('remove-run', $event)"
          @remove-common="emit('remove-common', $event)"
        />
      </section>
    </template>

    <AppDialog v-model:open="commonOpen" :title="openedCommon?.name">
      <template v-if="openedCommon">
        <p class="schedule__common-time">
          {{ dayLabel(openedCommon.dateLocal) }},
          {{ formatTimeRange(openedCommon.dateLocal, openedCommon.duration) }}
        </p>
        <p v-if="openedCommon.description" class="prose">{{ openedCommon.description }}</p>
      </template>
    </AppDialog>
  </div>
</template>

<style scoped>
.schedule {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}
.schedule__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-3);
}
.schedule__filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  min-width: 0;
}
.schedule__filters > * {
  width: auto;
  min-width: 9rem;
  max-width: 100%;
}
.schedule__day {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}
.schedule__day-title {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  font-size: var(--text-md);
}
.schedule__day-relative {
  color: var(--accent-text);
  font-size: var(--text-sm);
  font-weight: 550;
}
.schedule__nothing {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-lg);
  color: var(--text-muted);
}
.schedule__common-time {
  margin-bottom: var(--space-2);
  color: var(--text-muted);
}

@media (max-width: 519px) {
  .schedule__filters {
    flex: 1 1 100%;
  }
  .schedule__filters > * {
    flex: 1 1 8rem;
    min-width: 0;
  }
}
</style>
