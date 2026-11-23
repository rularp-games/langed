<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Plus, TriangleAlert, UserRound, Users } from '@lucide/vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import {
  PX_PER_MINUTE,
  blockBox,
  formatMinutes,
  runBadges,
  runMastersLabel,
  runSeatsShort,
} from './schedule'

/**
 * Сетка одного дня: столбцы — помещения, ось времени слева, блоки прогонов по длительности,
 * общие события — полосой на всю ширину. Прокручивается по горизонтали внутри себя,
 * колонка времени «липкая».
 * В режиме editable блоки — кнопки (событие run / common), пустые ячейки добавляют прогон (add).
 */
const props = defineProps({
  /** Результат buildDay(). */
  day: { type: Object, required: true },
  /** Подпись области для экранных дикторов: «Расписание на сб, 13 декабря». */
  label: { type: String, required: true },
  editable: Boolean,
  /** {myRuns: Map, userId} — отметки текущего пользователя. */
  context: { type: Object, default: () => ({}) },
  /** Map id прогона → конфликты по помещению (показываются только в редакторе). */
  conflicts: { type: Map, default: () => new Map() },
  /** Текущее время в минутах от полуночи, если этот день — сегодня; иначе null. */
  now: { type: Number, default: null },
})
const emit = defineEmits(['run', 'common', 'add'])

const SLOT = 30

const height = computed(() => (props.day.end - props.day.start) * PX_PER_MINUTE)
const slots = computed(() => {
  const list = []
  for (let minute = props.day.start; minute < props.day.end; minute += SLOT) list.push(minute)
  return list
})
const nowTop = computed(() => {
  if (props.now === null || props.now < props.day.start || props.now > props.day.end) return null
  return (props.now - props.day.start) * PX_PER_MINUTE
})

const px = (value) => `${value}px`
const offset = (minute) => px((minute - props.day.start) * PX_PER_MINUTE)

function blockStyle(block) {
  const { top, height: blockHeight } = blockBox(props.day, block.start, block.end)
  return {
    top: px(top),
    height: px(blockHeight),
    left: `${(block.lane / block.lanes) * 100}%`,
    width: `${100 / block.lanes}%`,
  }
}

function bandStyle(band) {
  const { top, height: bandHeight } = blockBox(props.day, band.start, band.end)
  return { top: px(top), height: px(bandHeight) }
}

const timeRange = (item) => `${formatMinutes(item.start)}–${formatMinutes(item.end)}`

function blockTitle(block) {
  const masters = runMastersLabel(block.run)
  return [timeRange(block), block.run.game?.name, masters && `Мастера: ${masters}`].filter(Boolean).join('\n')
}

function isConflict(run) {
  return props.editable && props.conflicts.has(run.id)
}

/** Общее событие открывается, если его можно править или у него есть описание. */
const bandClickable = (band) => props.editable || Boolean(band.item.description)
</script>

<template>
  <div class="sgrid-scroll" role="region" :aria-label="label" tabindex="0">
    <div class="sgrid" :style="{ '--cols': day.columns.length, '--body-height': px(height) }">
      <div class="sgrid__corner" aria-hidden="true"></div>
      <div
        v-for="(column, index) in day.columns"
        :key="column.room.id"
        class="sgrid__room"
        :style="{ gridColumn: index + 2 }"
      >
        <span class="sgrid__room-name">{{ column.room.name }}</span>
        <AppBadge v-if="column.room.blackbox">Blackbox</AppBadge>
      </div>

      <div class="sgrid__times" aria-hidden="true">
        <span v-for="hour in day.hours" :key="hour" class="sgrid__hour" :style="{ top: offset(hour) }">
          {{ formatMinutes(hour) }}
        </span>
      </div>

      <div
        v-for="(column, index) in day.columns"
        :key="column.room.id"
        class="sgrid__col"
        :style="{ gridColumn: index + 2 }"
      >
        <template v-if="editable">
          <button
            v-for="slot in slots"
            :key="slot"
            type="button"
            class="sgrid__cell"
            tabindex="-1"
            :style="{ top: offset(slot), height: px(SLOT * PX_PER_MINUTE) }"
            :aria-label="`Добавить прогон: ${column.room.name}, ${formatMinutes(slot)}`"
            @click="emit('add', { roomId: column.room.id, minutes: slot })"
          >
            <Plus :size="14" aria-hidden="true" />
            <span>{{ formatMinutes(slot) }}</span>
          </button>
        </template>

        <component
          :is="editable ? 'button' : RouterLink"
          v-for="block in column.blocks"
          :key="block.run.id"
          v-bind="editable ? { type: 'button' } : { to: { name: 'run', params: { id: block.run.id } } }"
          class="sgrid__block"
          :class="{
            'is-mine': context.myRuns?.has(block.run.id),
            'is-conflict': isConflict(block.run),
            'is-narrow': block.lanes > 1,
          }"
          :style="blockStyle(block)"
          :title="blockTitle(block)"
          @click="editable && emit('run', block.run)"
        >
          <span class="sgrid__block-time">
            {{ timeRange(block) }}
            <span v-if="runSeatsShort(block.run)" class="sgrid__block-seats">
              <Users :size="12" aria-hidden="true" />
              <span class="visually-hidden">Занято мест: </span>{{ runSeatsShort(block.run) }}
            </span>
          </span>
          <span class="sgrid__block-name">{{ block.run.game?.name }}</span>
          <span v-if="runMastersLabel(block.run)" class="sgrid__block-masters">
            <UserRound :size="12" aria-hidden="true" />
            <span class="visually-hidden">Мастера: </span>{{ runMastersLabel(block.run) }}
          </span>
          <span class="sgrid__block-badges">
            <AppBadge v-if="isConflict(block.run)" tone="danger">
              <TriangleAlert :size="12" aria-hidden="true" />
              Конфликт
            </AppBadge>
            <AppBadge v-for="badge in runBadges(block.run, context)" :key="badge.key" :tone="badge.tone">
              {{ badge.label }}
            </AppBadge>
          </span>
        </component>
      </div>

      <div class="sgrid__overlay">
        <component
          :is="bandClickable(band) ? 'button' : 'div'"
          v-for="band in day.bands"
          :key="band.item.id"
          :type="bandClickable(band) ? 'button' : undefined"
          class="sgrid__band"
          :class="{ 'is-clickable': bandClickable(band) }"
          :style="bandStyle(band)"
          @click="bandClickable(band) && emit('common', band.item)"
        >
          <span class="sgrid__band-label">
            <span class="sgrid__band-time">{{ timeRange(band) }}</span>
            <span class="sgrid__band-name">{{ band.item.name }}</span>
          </span>
        </component>

        <div v-if="nowTop !== null" class="sgrid__now" :style="{ top: px(nowTop) }">
          <span class="sgrid__now-label">{{ formatMinutes(now) }}</span>
          <span class="visually-hidden">— текущее время</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sgrid-scroll {
  /* Опора для абсолютно позиционированных потомков (.visually-hidden), иначе они растягивают страницу. */
  position: relative;
  max-width: 100%;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  overflow-x: auto;
  overscroll-behavior-x: contain;
}
.sgrid {
  --time-col: 3.25rem;
  display: grid;
  grid-template-columns: var(--time-col) repeat(var(--cols), minmax(9.5rem, 1fr));
  grid-template-rows: auto var(--body-height);
  min-width: max-content;
}
.sgrid__corner,
.sgrid__times {
  position: sticky;
  left: 0;
  z-index: 5;
  grid-column: 1;
  background: var(--surface);
  border-right: 1px solid var(--border);
}
.sgrid__corner {
  grid-row: 1;
  border-bottom: 1px solid var(--border);
}
.sgrid__room {
  grid-row: 1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1) var(--space-2);
  min-width: 0;
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border);
  background: var(--surface-2);
  font-size: var(--text-sm);
  font-weight: 600;
}
.sgrid__room + .sgrid__room {
  border-left: 1px solid var(--border);
}
.sgrid__room-name {
  min-width: 0;
  overflow-wrap: anywhere;
}
.sgrid__times {
  grid-row: 2;
}
.sgrid__hour {
  position: absolute;
  right: var(--space-2);
  padding-top: 2px;
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.sgrid__col {
  position: relative;
  grid-row: 2;
  min-width: 0;
  /* Линии часов: одна на каждые 60 минут (72px при 1.2px за минуту). */
  background-image: repeating-linear-gradient(to bottom, var(--border) 0 1px, transparent 1px 72px);
}
.sgrid__col + .sgrid__col {
  border-left: 1px solid var(--border);
}
.sgrid__cell {
  position: absolute;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-2);
  border: 0;
  background: transparent;
  color: transparent;
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
  text-align: left;
}
.sgrid__cell:hover,
.sgrid__cell:focus-visible {
  background: var(--accent-soft);
  color: var(--accent-text);
}
.sgrid__block {
  position: absolute;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--border-strong);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius-sm);
  /* Зазор между соседними блоками и линиями сетки. */
  background: var(--surface) padding-box;
  box-shadow: 0 0 0 1px var(--surface);
  color: var(--text);
  font: inherit;
  font-size: var(--text-xs);
  line-height: 1.3;
  text-align: left;
  text-decoration: none;
  overflow: hidden;
  transition:
    border-color var(--duration),
    box-shadow var(--duration);
}
.sgrid__block:hover {
  color: var(--text);
  box-shadow:
    0 0 0 1px var(--surface),
    var(--shadow-md);
  z-index: 3;
}
.sgrid__block.is-mine {
  background-color: var(--success-soft);
  border-left-color: var(--success-text);
}
.sgrid__block.is-conflict {
  border-color: var(--danger-text);
  background-color: var(--danger-soft);
}
.sgrid__block-time {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0 var(--space-2);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.sgrid__block-seats {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.sgrid__block-name {
  font-size: var(--text-sm);
  font-weight: 600;
  overflow-wrap: anywhere;
}
.sgrid__block-masters {
  display: flex;
  align-items: flex-start;
  gap: var(--space-1);
  color: var(--text-muted);
}
.sgrid__block-masters svg {
  flex: none;
  margin-top: 2px;
}
.sgrid__block-badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}
.sgrid__block-badges:empty {
  display: none;
}
.sgrid__overlay {
  position: relative;
  grid-column: 2 / -1;
  grid-row: 2;
  min-width: 0;
  pointer-events: none;
}
.sgrid__band {
  position: absolute;
  left: 0;
  right: 0;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  padding: 0;
  border: 0;
  border-block: 1px solid var(--border-strong);
  background: var(--surface-2);
  color: var(--text);
  font: inherit;
  font-size: var(--text-xs);
  text-align: left;
  overflow: clip;
  pointer-events: auto;
}
.sgrid__band.is-clickable:hover {
  background: var(--surface-hover);
}
.sgrid__band-label {
  position: sticky;
  left: var(--time-col);
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0 var(--space-2);
  padding: var(--space-1) var(--space-3);
}
.sgrid__band-time {
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.sgrid__band-name {
  font-size: var(--text-sm);
  font-weight: 600;
}
.sgrid__now {
  position: absolute;
  left: 0;
  right: 0;
  z-index: 4;
  height: 0;
  border-top: 2px solid var(--danger-text);
}
.sgrid__now-label {
  position: sticky;
  left: var(--time-col);
  display: inline-block;
  padding: 0 var(--space-1);
  border-radius: 0 0 var(--radius-sm) 0;
  background: var(--danger-text);
  color: var(--surface);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
  line-height: 1.4;
  vertical-align: top;
}
</style>
