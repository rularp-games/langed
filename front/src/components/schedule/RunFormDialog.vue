<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { ExternalLink, Trash2 } from '@lucide/vue'
import { ApiError } from '@/api/client'
import { eventsApi } from '@/api/events'
import { useToast } from '@/composables/useToast'
import { formatDate, formatDuration, dateKey } from '@/utils/datetime'
import { formatRange } from '@/utils/format'
import GamePicker from '@/components/GamePicker.vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppCheckbox from '@/components/ui/AppCheckbox.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import FormField from '@/components/ui/FormField.vue'
import {
  DEFAULT_RUN_DURATION,
  NO_ROOM,
  eventDays,
  findConflicts,
  formatMinutes,
  minutesOf,
  toLocalDateTime,
} from './schedule'

/**
 * Диалог добавления и изменения прогона в расписании проведения.
 *   <RunFormDialog v-model:open="open" :event="event" :run="run" :preset="{ day, roomId, minutes }"
 *     :rooms="rooms" @saved="reload" @remove="removeRun" />
 */
const props = defineProps({
  /** Проведение с расписанием (eventsApi.schedule). */
  event: { type: Object, required: true },
  /** Изменяемый прогон; null — добавление. */
  run: { type: Object, default: null },
  /** Предзаполнение при добавлении: {day, roomId, minutes}. */
  preset: { type: Object, default: null },
  /** Помещения на выбор: [{id, name, venueName?}]. */
  rooms: { type: Array, default: () => [] },
})
const emit = defineEmits(['saved', 'remove'])
const open = defineModel('open', { type: Boolean, default: false })

const toast = useToast()
const formEl = ref(null)
const form = reactive({
  game: null,
  day: '',
  time: '',
  duration: DEFAULT_RUN_DURATION,
  roomIds: [],
  maxPlayers: '',
  registrationOpen: true,
})
const errors = ref({})
const formError = ref('')
const saving = ref(false)

const isEdit = computed(() => Boolean(props.run))
const days = computed(() => eventDays(props.event))
const dayOptions = computed(() =>
  days.value.map((key) => ({ value: key, label: formatDate(key, { weekday: true, year: true }) })),
)

/** Помещения на выбор плюс уже назначенные прогону, которых в списке нет. */
const roomOptions = computed(() => {
  const list = [...props.rooms]
  for (const room of props.run?.rooms ?? []) {
    if (!list.some((item) => item.id === room.id)) list.push(room)
  }
  return list
})

watch(
  open,
  (value) => {
    if (!value) return
    errors.value = {}
    formError.value = ''
    const run = props.run
    if (run) {
      Object.assign(form, {
        game: run.game,
        day: dateKey(run.dateLocal),
        time: formatMinutes(minutesOf(run.dateLocal)),
        duration: run.duration ?? DEFAULT_RUN_DURATION,
        roomIds: run.rooms.map((room) => room.id),
        maxPlayers: run.maxPlayers ?? '',
        registrationOpen: run.registrationOpen,
      })
    } else {
      const preset = props.preset ?? {}
      Object.assign(form, {
        game: null,
        day: days.value.includes(preset.day) ? preset.day : (days.value[0] ?? ''),
        time: preset.minutes === undefined ? '12:00' : formatMinutes(preset.minutes),
        duration: DEFAULT_RUN_DURATION,
        roomIds: preset.roomId && preset.roomId !== NO_ROOM ? [preset.roomId] : [],
        maxPlayers: '',
        registrationOpen: true,
      })
    }
  },
  { immediate: true },
)

// Выбор игры снимает ошибку «Выберите игру», не дожидаясь повторной отправки.
watch(
  () => form.game,
  (game) => {
    if (game && errors.value.game) errors.value = { ...errors.value, game: '' }
  },
)

const timeMinutes = computed(() => {
  const match = /^(\d{2}):(\d{2})/.exec(form.time)
  return match ? Number(match[1]) * 60 + Number(match[2]) : null
})
const durationNumber = computed(() => {
  const value = Number(form.duration)
  return Number.isInteger(value) && value > 0 ? value : null
})
const durationHint = computed(() => {
  if (!durationNumber.value) return 'В минутах'
  const end = timeMinutes.value === null ? '' : `, до ${formatMinutes(timeMinutes.value + durationNumber.value)}`
  return `${formatDuration(durationNumber.value)}${end}`
})
const playersHint = computed(() => {
  const players = form.game ? formatRange(form.game.playersMin, form.game.playersMax) : null
  return players
    ? `Пусто — по максимуму игры (игроков в игре: ${players})`
    : 'Пусто — по максимальному числу игроков игры'
})

/** Пересечения с другими прогонами в выбранных помещениях — предупреждение, сохранить можно. */
const conflicts = computed(() => {
  if (!form.day || timeMinutes.value === null || !durationNumber.value || !form.roomIds.length) return []
  const draft = {
    id: -1,
    dateLocal: toLocalDateTime(form.day, timeMinutes.value),
    duration: durationNumber.value,
    rooms: roomOptions.value.filter((room) => form.roomIds.includes(room.id)),
  }
  const others = props.event.runs.filter((run) => run.id !== props.run?.id)
  return findConflicts([...others, draft]).get(-1) ?? []
})

function validate() {
  const result = {}
  if (!form.game) result.game = 'Выберите игру'
  if (!form.day) result.day = 'Выберите день'
  if (timeMinutes.value === null) result.time = 'Укажите время начала'
  if (!durationNumber.value) result.duration = 'Укажите длительность в минутах'
  if (form.maxPlayers !== '' && form.maxPlayers !== null) {
    const limit = Number(form.maxPlayers)
    if (!Number.isInteger(limit) || limit < 1) result.maxPlayers = 'Укажите целое число не меньше 1'
  }
  errors.value = result
  return Object.keys(result).length === 0
}

function payload() {
  return {
    gameId: form.game.id,
    date: toLocalDateTime(form.day, timeMinutes.value),
    duration: durationNumber.value,
    roomIds: form.roomIds,
    maxPlayers: form.maxPlayers === '' || form.maxPlayers === null ? null : Number(form.maxPlayers),
    registrationOpen: form.registrationOpen,
  }
}

function applyError(err) {
  if (!(err instanceof ApiError)) {
    console.error(err)
    formError.value = 'Что-то пошло не так. Попробуйте ещё раз.'
    return
  }
  if (err.hasFieldErrors) {
    errors.value = {
      game: err.field('gameId'),
      day: err.field('date'),
      duration: err.field('duration'),
      rooms: err.field('roomIds'),
      maxPlayers: err.field('maxPlayers'),
    }
  }
  if (!Object.values(errors.value).some(Boolean)) formError.value = err.detail
}

async function focusFirstError() {
  await nextTick()
  formEl.value?.querySelector('[aria-invalid="true"]')?.focus()
}

async function submit() {
  if (saving.value) return
  formError.value = ''
  if (!validate()) {
    await focusFirstError()
    return
  }
  saving.value = true
  try {
    const saved = isEdit.value
      ? await eventsApi.updateRun(props.event.id, props.run.id, payload())
      : await eventsApi.addRun(props.event.id, payload())
    toast.success(isEdit.value ? 'Прогон сохранён' : 'Прогон добавлен в расписание')
    open.value = false
    emit('saved', saved)
  } catch (err) {
    applyError(err)
    await focusFirstError()
  } finally {
    saving.value = false
  }
}

const roomLabel = (room) => (room.venueName ? `${room.name} — ${room.venueName}` : room.name)
</script>

<template>
  <AppDialog v-model:open="open" :title="isEdit ? 'Прогон в расписании' : 'Новый прогон'" size="md" :dismissible="!saving">
    <form :id="`run-form-${event.id}`" ref="formEl" class="run-form" novalidate @submit.prevent="submit">
      <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>

      <FormField label="Игра" :error="errors.game" required>
        <GamePicker v-model="form.game" label="Игра" required :disabled="saving" />
      </FormField>

      <div class="run-form__row">
        <FormField label="День" :error="errors.day" required>
          <AppSelect v-model="form.day" :options="dayOptions" />
        </FormField>
        <FormField label="Начало" :error="errors.time" required>
          <AppInput v-model="form.time" type="time" step="300" />
        </FormField>
        <FormField label="Длительность" :error="errors.duration" :hint="durationHint" required>
          <AppInput v-model="form.duration" type="number" min="5" step="5" inputmode="numeric" />
        </FormField>
      </div>

      <fieldset class="run-form__rooms">
        <legend>Помещения</legend>
        <div v-if="roomOptions.length" class="run-form__room-list">
          <AppCheckbox v-for="room in roomOptions" :key="room.id" v-model="form.roomIds" :value="room.id">
            {{ roomLabel(room) }}
          </AppCheckbox>
        </div>
        <p v-else class="run-form__note">
          Помещений на выбор нет: у проведения не указана площадка или у неё нет помещений. Прогон попадёт в столбец
          «Без помещения».
        </p>
        <p v-if="errors.rooms" class="run-form__error" role="alert">{{ errors.rooms }}</p>
      </fieldset>

      <AppAlert v-if="conflicts.length" tone="warning" title="Помещение в это время занято">
        <ul>
          <li v-for="conflict in conflicts" :key="`${conflict.run.id}-${conflict.room.id}`">
            {{ conflict.room.name }}: «{{ conflict.run.game?.name }}»
          </li>
        </ul>
      </AppAlert>

      <div class="run-form__row run-form__row--two">
        <FormField label="Лимит игроков" :error="errors.maxPlayers" :hint="playersHint">
          <AppInput v-model="form.maxPlayers" type="number" min="1" step="1" inputmode="numeric" />
        </FormField>
        <AppCheckbox v-model="form.registrationOpen" class="run-form__check">Запись на прогон открыта</AppCheckbox>
      </div>

      <p v-if="isEdit" class="run-form__note">
        Мастера и заявки игроков — на
        <RouterLink :to="{ name: 'run', params: { id: run.id } }" class="run-form__link">
          странице прогона
          <ExternalLink :size="14" aria-hidden="true" />
        </RouterLink>
      </p>
      <p v-else class="run-form__note">
        Вы станете мастером прогона. Назначить других мастеров можно на странице прогона после сохранения.
      </p>
    </form>

    <template #footer>
      <AppButton v-if="isEdit" variant="ghost" class="run-form__remove" :disabled="saving" @click="emit('remove', run)">
        <Trash2 :size="16" aria-hidden="true" />
        Удалить
      </AppButton>
      <AppButton :disabled="saving" @click="open = false">Отмена</AppButton>
      <AppButton variant="primary" type="submit" :form="`run-form-${event.id}`" :loading="saving">
        {{ isEdit ? 'Сохранить' : 'Добавить' }}
      </AppButton>
    </template>
  </AppDialog>
</template>

<style scoped>
.run-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.run-form__row {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--space-3);
  align-items: start;
}
.run-form__row--two {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}
.run-form__check {
  /* На одной линии с полем ввода, а не с его подписью. */
  margin-top: calc(var(--text-sm) * 1.5 + var(--space-1) + var(--space-2));
}
.run-form__rooms {
  min-width: 0;
  padding: 0;
  border: 0;
}
.run-form__rooms legend {
  margin-bottom: var(--space-2);
  padding: 0;
  font-size: var(--text-sm);
  font-weight: 550;
}
.run-form__room-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-5);
}
.run-form__note {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.run-form__link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}
.run-form__error {
  margin-top: var(--space-1);
  color: var(--danger-text);
  font-size: var(--text-sm);
}
.run-form__remove {
  margin-right: auto;
}

@media (max-width: 519px) {
  .run-form__row {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
  .run-form__row > :first-child {
    grid-column: 1 / -1;
  }
  .run-form__row--two {
    grid-template-columns: minmax(0, 1fr);
  }
  .run-form__check {
    margin-top: 0;
  }
}
</style>
