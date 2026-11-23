<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { Trash2 } from '@lucide/vue'
import { ApiError } from '@/api/client'
import { eventsApi } from '@/api/events'
import { useToast } from '@/composables/useToast'
import { dateKey, formatDate, formatDuration } from '@/utils/datetime'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import AppTextarea from '@/components/ui/AppTextarea.vue'
import FormField from '@/components/ui/FormField.vue'
import { DEFAULT_COMMON_DURATION, eventDays, formatMinutes, minutesOf, toLocalDateTime } from './schedule'

/** Диалог добавления и изменения общего события расписания (открытие, обед, закрытие). */
const props = defineProps({
  /** Проведение с расписанием (eventsApi.schedule). */
  event: { type: Object, required: true },
  /** Изменяемое событие; null — добавление. */
  item: { type: Object, default: null },
  /** Предзаполнение при добавлении: {day}. */
  preset: { type: Object, default: null },
})
const emit = defineEmits(['saved', 'remove'])
const open = defineModel('open', { type: Boolean, default: false })

const toast = useToast()
const formEl = ref(null)
const form = reactive({ name: '', day: '', time: '', duration: DEFAULT_COMMON_DURATION, description: '' })
const errors = ref({})
const formError = ref('')
const saving = ref(false)

const isEdit = computed(() => Boolean(props.item))
const days = computed(() => eventDays(props.event))
const dayOptions = computed(() =>
  days.value.map((key) => ({ value: key, label: formatDate(key, { weekday: true, year: true }) })),
)

watch(
  open,
  (value) => {
    if (!value) return
    errors.value = {}
    formError.value = ''
    const item = props.item
    if (item) {
      Object.assign(form, {
        name: item.name,
        day: dateKey(item.dateLocal),
        time: formatMinutes(minutesOf(item.dateLocal)),
        duration: item.duration ?? DEFAULT_COMMON_DURATION,
        description: item.description,
      })
    } else {
      const day = props.preset?.day
      Object.assign(form, {
        name: '',
        day: days.value.includes(day) ? day : (days.value[0] ?? ''),
        time: '10:00',
        duration: DEFAULT_COMMON_DURATION,
        description: '',
      })
    }
  },
  { immediate: true },
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

function validate() {
  const result = {}
  if (!form.name.trim()) result.name = 'Укажите название события'
  if (!form.day) result.day = 'Выберите день'
  if (timeMinutes.value === null) result.time = 'Укажите время начала'
  if (!durationNumber.value) result.duration = 'Укажите длительность в минутах'
  errors.value = result
  return Object.keys(result).length === 0
}

function applyError(err) {
  if (!(err instanceof ApiError)) {
    console.error(err)
    formError.value = 'Что-то пошло не так. Попробуйте ещё раз.'
    return
  }
  if (err.hasFieldErrors) {
    errors.value = {
      name: err.field('name'),
      day: err.field('date'),
      duration: err.field('duration'),
      description: err.field('description'),
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
  const data = {
    name: form.name.trim(),
    date: toLocalDateTime(form.day, timeMinutes.value),
    duration: durationNumber.value,
    description: form.description.trim(),
  }
  saving.value = true
  try {
    const saved = isEdit.value
      ? await eventsApi.updateCommonEvent(props.event.id, props.item.id, data)
      : await eventsApi.addCommonEvent(props.event.id, data)
    toast.success(isEdit.value ? 'Событие сохранено' : 'Событие добавлено в расписание')
    open.value = false
    emit('saved', saved)
  } catch (err) {
    applyError(err)
    await focusFirstError()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppDialog v-model:open="open" :title="isEdit ? 'Общее событие' : 'Новое общее событие'" size="md" :dismissible="!saving">
    <form :id="`common-form-${event.id}`" ref="formEl" class="common-form" novalidate @submit.prevent="submit">
      <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>

      <FormField label="Название" :error="errors.name" hint="Например: открытие, обед, закрытие" required>
        <AppInput v-model="form.name" maxlength="255" autocomplete="off" autofocus />
      </FormField>

      <div class="common-form__row">
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

      <FormField label="Описание" :error="errors.description">
        <AppTextarea v-model="form.description" rows="3" />
      </FormField>
    </form>

    <template #footer>
      <AppButton v-if="isEdit" variant="ghost" class="common-form__remove" :disabled="saving" @click="emit('remove', item)">
        <Trash2 :size="16" aria-hidden="true" />
        Удалить
      </AppButton>
      <AppButton :disabled="saving" @click="open = false">Отмена</AppButton>
      <AppButton variant="primary" type="submit" :form="`common-form-${event.id}`" :loading="saving">
        {{ isEdit ? 'Сохранить' : 'Добавить' }}
      </AppButton>
    </template>
  </AppDialog>
</template>

<style scoped>
.common-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.common-form__row {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--space-3);
  align-items: start;
}
.common-form__remove {
  margin-right: auto;
}
@media (max-width: 519px) {
  .common-form__row {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
  .common-form__row > :first-child {
    grid-column: 1 / -1;
  }
}
</style>
