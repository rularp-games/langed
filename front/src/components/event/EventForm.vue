<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { ApiError, isAbortError } from '@/api/client'
import { eventsApi } from '@/api/events'
import { venuesApi } from '@/api/venues'
import { useToast } from '@/composables/useToast'
import CitySelect from '@/components/CitySelect.vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppCheckbox from '@/components/ui/AppCheckbox.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import FormField from '@/components/ui/FormField.vue'

/**
 * Диалог свойств проведения конвента: создание (со страницы конвента) и изменение
 * (со страницы редактора расписания). Конвент фиксирован.
 *   <EventForm v-model:open="open" :convention-id="convention.id" :convention-name="convention.name" @saved="…" />
 *   <EventForm v-model:open="open" :event="event" @saved="reload" />
 */
const props = defineProps({
  /** Изменяемое проведение; null — создание. */
  event: { type: Object, default: null },
  conventionId: { type: Number, default: null },
  conventionName: { type: String, default: '' },
})
const emit = defineEmits(['saved'])
const open = defineModel('open', { type: Boolean, default: false })

const toast = useToast()
const formEl = ref(null)
const form = reactive({ cityId: '', venueId: '', dateStart: '', dateEnd: '', capacity: '', registrationOpen: true })
const errors = ref({})
const formError = ref('')
const saving = ref(false)

const isEdit = computed(() => Boolean(props.event))
const title = computed(() => (isEdit.value ? 'Свойства проведения' : 'Новое проведение'))
const name = computed(() => props.event?.conventionName || props.conventionName)

// Площадки выбранного города.
const venues = ref([])
const venuesLoading = ref(false)
let venuesController = null

async function loadVenues(cityId) {
  venuesController?.abort()
  venues.value = []
  if (!cityId) return
  const current = new AbortController()
  venuesController = current
  venuesLoading.value = true
  try {
    const page = await venuesApi.list({ city: cityId, pageSize: 100 }, { signal: current.signal })
    venues.value = page.items
  } catch (err) {
    if (!isAbortError(err)) toast.apiError(err, 'Не удалось загрузить площадки города')
  } finally {
    if (venuesController === current) venuesLoading.value = false
  }
}

const venueOptions = computed(() => {
  const list = venues.value.map((venue) => ({ value: venue.id, label: venue.name }))
  const current = props.event?.venue
  // Текущая площадка остаётся в списке, даже если не попала в загруженную страницу.
  if (current && form.venueId === current.id && !list.some((item) => item.value === current.id)) {
    list.unshift({ value: current.id, label: current.name })
  }
  return list
})
const venueHint = computed(() => {
  if (!form.cityId) return 'Сначала выберите город'
  if (venuesLoading.value) return 'Загружаем площадки…'
  if (!venueOptions.value.length) return 'В этом городе площадок пока нет — добавьте её в разделе «Площадки»'
  return 'От площадки зависят помещения в расписании'
})

watch(
  open,
  (value) => {
    if (!value) return
    errors.value = {}
    formError.value = ''
    const event = props.event
    Object.assign(form, {
      cityId: event?.city?.id ?? '',
      venueId: event?.venue?.id ?? '',
      dateStart: event?.dateStart ?? '',
      dateEnd: event?.dateEnd ?? '',
      capacity: event?.capacity ?? '',
      registrationOpen: event?.registrationOpen ?? true,
    })
    loadVenues(form.cityId)
  },
  { immediate: true },
)

function onCityChange(cityId) {
  form.cityId = cityId
  form.venueId = ''
  loadVenues(cityId)
}

function onStartChange(value) {
  // Однодневный конвент — частый случай: конец подставляется вслед за началом.
  if (!form.dateEnd || form.dateEnd < value) form.dateEnd = value
  form.dateStart = value
}

function validate() {
  const result = {}
  if (!form.cityId) result.cityId = 'Выберите город'
  if (!form.dateStart) result.dateStart = 'Укажите дату начала'
  if (!form.dateEnd) result.dateEnd = 'Укажите дату окончания'
  else if (form.dateStart && form.dateEnd < form.dateStart) result.dateEnd = 'Окончание не может быть раньше начала'
  if (form.capacity !== '' && form.capacity !== null) {
    const capacity = Number(form.capacity)
    if (!Number.isInteger(capacity) || capacity < 1) result.capacity = 'Укажите целое число не меньше 1'
  }
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
      cityId: err.field('cityId'),
      venueId: err.field('venueId'),
      dateStart: err.field('dateStart'),
      dateEnd: err.field('dateEnd'),
      capacity: err.field('capacity'),
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
    cityId: Number(form.cityId),
    venueId: form.venueId ? Number(form.venueId) : null,
    dateStart: form.dateStart,
    dateEnd: form.dateEnd,
    capacity: form.capacity === '' || form.capacity === null ? null : Number(form.capacity),
    registrationOpen: form.registrationOpen,
  }
  saving.value = true
  try {
    const saved = isEdit.value
      ? await eventsApi.update(props.event.id, data)
      : await eventsApi.create({ ...data, conventionId: props.conventionId })
    toast.success(isEdit.value ? 'Проведение сохранено' : 'Проведение добавлено')
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
  <AppDialog v-model:open="open" :title="title" size="md" :dismissible="!saving">
    <form id="event-form" ref="formEl" class="event-form" novalidate @submit.prevent="submit">
      <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>

      <p v-if="name" class="event-form__convention">Конвент: <strong>{{ name }}</strong></p>

      <div class="event-form__row">
        <FormField label="Город" :error="errors.cityId" required>
          <CitySelect :model-value="form.cityId" placeholder="Выберите город" @update:model-value="onCityChange" />
        </FormField>
        <FormField label="Площадка" :error="errors.venueId" :hint="venueHint">
          <AppSelect
            v-model="form.venueId"
            :options="venueOptions"
            placeholder="Не указана"
            :disabled="!form.cityId || venuesLoading"
          />
        </FormField>
      </div>

      <div class="event-form__row">
        <FormField label="Дата начала" :error="errors.dateStart" required>
          <AppInput :model-value="form.dateStart" type="date" @update:model-value="onStartChange" />
        </FormField>
        <FormField label="Дата окончания" :error="errors.dateEnd" required>
          <AppInput v-model="form.dateEnd" type="date" :min="form.dateStart || undefined" />
        </FormField>
      </div>

      <div class="event-form__row">
        <FormField label="Лимит участников" :error="errors.capacity" hint="Пусто — без ограничения">
          <AppInput v-model="form.capacity" type="number" min="1" step="1" inputmode="numeric" />
        </FormField>
        <AppCheckbox v-model="form.registrationOpen" class="event-form__check">Регистрация открыта</AppCheckbox>
      </div>

      <p v-if="isEdit && event.runsCount" class="event-form__note">
        При смене дат проверьте расписание: прогоны и события вне новых дат останутся на прежних днях.
      </p>
    </form>

    <template #footer>
      <AppButton :disabled="saving" @click="open = false">Отмена</AppButton>
      <AppButton variant="primary" type="submit" form="event-form" :loading="saving">
        {{ isEdit ? 'Сохранить' : 'Добавить проведение' }}
      </AppButton>
    </template>
  </AppDialog>
</template>

<style scoped>
.event-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.event-form__convention {
  color: var(--text-muted);
}
.event-form__convention strong {
  color: var(--text);
}
.event-form__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--space-3);
  align-items: start;
}
.event-form__check {
  /* На одной линии с полем ввода, а не с его подписью. */
  margin-top: calc(var(--text-sm) * 1.5 + var(--space-1) + var(--space-2));
}
.event-form__note {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
@media (max-width: 519px) {
  .event-form__row {
    grid-template-columns: minmax(0, 1fr);
  }
  .event-form__check {
    margin-top: 0;
  }
}
</style>
