<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { eventsApi } from '@/api/events'
import { gamesApi } from '@/api/games'
import { runsApi } from '@/api/runs'
import { venuesApi } from '@/api/venues'
import { useAsyncData } from '@/composables/useAsyncData'
import { usePageTitle } from '@/composables/usePageTitle'
import { useToast } from '@/composables/useToast'
import { useCitiesStore } from '@/stores/cities'
import { formatDateRange, formatDuration, fromDateTimeInput, toDateTimeInput } from '@/utils/datetime'
import CitySelect from '@/components/CitySelect.vue'
import GamePicker from '@/components/GamePicker.vue'
import CityDialog from '@/components/venue/CityDialog.vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppCheckbox from '@/components/ui/AppCheckbox.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import FormField from '@/components/ui/FormField.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

// Один компонент на создание (/runs/new, без id) и редактирование (/runs/:id/edit).
const props = defineProps({
  id: { type: String, default: null },
})

const route = useRoute()
const router = useRouter()
const toast = useToast()
const citiesStore = useCitiesStore()

const isEdit = computed(() => Boolean(props.id))
const queryId = (name) => {
  const value = [route.query[name]].flat()[0]
  return value && /^\d+$/.test(value) ? value : null
}

/**
 * Исходные данные формы: при редактировании — прогон и его проведение; при создании —
 * игра из ?game=<id> и проведение из ?event=<id> (если переданы и доступны).
 */
const { data: initial, error, reload } = useAsyncData(
  async (signal) => {
    const optional = (promise) => promise.catch(() => null)
    if (props.id) {
      const run = await runsApi.get(props.id, { signal })
      const event = run.eventId ? await optional(eventsApi.get(run.eventId, { signal })) : null
      return { run, game: run.game, event, eventDenied: false }
    }
    const gameId = queryId('game')
    const eventId = queryId('event')
    const [game, event] = await Promise.all([
      gameId ? optional(gamesApi.get(gameId, { signal })) : null,
      eventId ? optional(eventsApi.get(eventId, { signal })) : null,
    ])
    // Включать прогон в расписание конвента может только организатор или staff.
    const allowed = event?.canEdit ? event : null
    return { run: null, game, event: allowed, eventDenied: Boolean(eventId) && !allowed }
  },
  { watch: () => props.id },
)

const run = computed(() => initial.value?.run ?? null)
const event = computed(() => initial.value?.event ?? null)
const forbidden = computed(() => Boolean(run.value) && !run.value.canEdit)

usePageTitle(() => (run.value?.game ? `Редактирование: ${run.value.game.name}` : ''))

const form = reactive({
  game: null,
  cityId: '',
  date: '',
  duration: 180,
  venueId: '',
  roomIds: [],
  maxPlayers: '',
  registrationOpen: true,
})
const errors = ref({})
const formError = ref('')
const saving = ref(false)
const formEl = ref(null)

watch(
  initial,
  (value) => {
    if (!value) return
    const source = value.run
    Object.assign(form, {
      game: value.game ?? null,
      cityId: source?.cityId ?? value.event?.city?.id ?? '',
      date: source ? toDateTimeInput(source.dateLocal) : '',
      duration: source?.duration ?? 180,
      venueId: source?.rooms[0]?.venueId ?? value.event?.venue?.id ?? '',
      roomIds: source ? source.rooms.map((room) => room.id) : [],
      maxPlayers: source?.maxPlayers ?? '',
      registrationOpen: source ? source.registrationOpen : true,
    })
    errors.value = {}
    formError.value = ''
    citiesStore.load().catch(() => {})
  },
  { immediate: true },
)

// --- Город ---
const cityLocked = computed(() => Boolean(event.value))
const city = computed(() => citiesStore.byId(form.cityId) ?? (event.value?.city?.id === form.cityId ? event.value.city : null))
const cityName = computed(() => city.value?.name ?? run.value?.cityName ?? '')

function onCityChange() {
  form.venueId = ''
  form.roomIds = []
}

// --- Площадка и помещения ---
const { data: venues, loading: venuesLoading } = useAsyncData(
  async (signal) => (form.cityId ? (await venuesApi.list({ city: form.cityId, pageSize: 100 }, { signal })).items : []),
  { watch: () => form.cityId, reloadOnAuthChange: false },
)
const venueOptions = computed(() => (venues.value ?? []).map((venue) => ({ value: venue.id, label: venue.name })))
const venue = computed(() => (venues.value ?? []).find((item) => item.id === form.venueId) ?? null)
// Площадку проведения менять нельзя: прогон идёт там же, где конвент.
const venueLocked = computed(() => Boolean(event.value?.venue) && form.venueId === event.value.venue.id)

function onVenueChange() {
  form.roomIds = []
}

// --- Дата ---
const dateMin = computed(() => (event.value?.dateStart ? `${event.value.dateStart}T00:00` : undefined))
const dateMax = computed(() => (event.value?.dateEnd ? `${event.value.dateEnd}T23:59` : undefined))
const dateHint = computed(() => {
  const parts = []
  if (cityName.value) parts.push(`По времени города ${cityName.value}.`)
  if (event.value) parts.push(`Конвент проходит ${formatDateRange(event.value.dateStart, event.value.dateEnd)}.`)
  return parts.join(' ')
})

const durationHint = computed(() => {
  const text = formatDuration(form.duration)
  return text && Number(form.duration) >= 60 ? `В минутах: ${text}` : 'В минутах'
})
const maxPlayersHint = computed(() =>
  form.game?.playersMax
    ? `Пусто — по игре: до ${form.game.playersMax}`
    : 'Пусто — максимум игроков берётся из игры',
)

// --- Новый город ---
const cityDialog = ref(false)

function onCityCreated(city) {
  form.cityId = city.id
  onCityChange()
  toast.success(`Город «${city.name}» добавлен`)
}

// --- Сохранение ---
const cancelTo = computed(() => {
  if (run.value) return { name: 'run', params: { id: run.value.id } }
  if (event.value) return { name: 'event', params: { id: event.value.id } }
  if (form.game && queryId('game')) return { name: 'game', params: { id: form.game.id } }
  return { name: 'afisha' }
})
const back = computed(() => {
  if (run.value) return { to: cancelTo.value, label: run.value.game?.name ?? 'Прогон' }
  if (event.value) return { to: cancelTo.value, label: event.value.conventionName || 'Конвент' }
  return { to: { name: 'afisha' }, label: 'Афиша' }
})

function validate() {
  const result = {}
  if (!form.game) result.game = 'Выберите игру'
  if (!form.cityId) result.city = 'Выберите город'
  const date = fromDateTimeInput(form.date)
  if (!date) result.date = 'Укажите дату и время начала'
  else if (dateMin.value && (form.date < dateMin.value || form.date > dateMax.value)) {
    result.date = `Дата должна попадать в даты конвента: ${formatDateRange(event.value.dateStart, event.value.dateEnd)}`
  }
  const duration = Number(form.duration)
  if (!Number.isInteger(duration) || duration < 1) result.duration = 'Укажите длительность в минутах'
  if (form.maxPlayers !== '' && form.maxPlayers !== null) {
    const max = Number(form.maxPlayers)
    if (!Number.isInteger(max) || max < 1) result.maxPlayers = 'Укажите целое число от 1 или оставьте поле пустым'
  }
  if (venue.value?.rooms.length && !form.roomIds.length && !venueLocked.value) {
    result.rooms = 'Отметьте хотя бы одно помещение или уберите площадку'
  }
  errors.value = result
  return Object.keys(result).length === 0
}

async function focusFirstError() {
  await nextTick()
  formEl.value?.querySelector('[aria-invalid="true"]')?.focus()
}

async function submit() {
  if (saving.value) return
  formError.value = ''
  if (!validate()) {
    focusFirstError()
    return
  }
  const roomIds = venue.value ? form.roomIds.filter((id) => venue.value.rooms.some((room) => room.id === id)) : []
  const payload = {
    gameId: form.game.id,
    cityId: form.cityId,
    date: fromDateTimeInput(form.date),
    duration: Number(form.duration),
    roomIds,
    maxPlayers: form.maxPlayers === '' || form.maxPlayers === null ? null : Number(form.maxPlayers),
    registrationOpen: form.registrationOpen,
  }
  if (!isEdit.value && event.value) payload.eventId = event.value.id
  saving.value = true
  try {
    const saved = isEdit.value ? await runsApi.update(props.id, payload) : await runsApi.create(payload)
    toast.success(isEdit.value ? 'Прогон сохранён' : 'Прогон добавлен')
    router.push({ name: 'run', params: { id: saved.id } })
  } catch (err) {
    errors.value = {
      game: err.field?.('gameId'),
      city: err.field?.('cityId'),
      date: err.field?.('date'),
      duration: err.field?.('duration'),
      rooms: err.field?.('roomIds'),
      maxPlayers: err.field?.('maxPlayers'),
    }
    const known = Object.values(errors.value).some(Boolean)
    if (!known) formError.value = err.detail || 'Не удалось сохранить прогон. Попробуйте ещё раз.'
    else focusFirstError()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="container container--narrow">
    <template v-if="error">
      <PageHeader :back="{ to: { name: 'afisha' }, label: 'Афиша' }" />
      <ErrorState :error="error" title="Не удалось загрузить прогон" not-found-title="Прогон не найден" @retry="reload" />
    </template>

    <template v-else-if="!initial">
      <PageHeader :title="isEdit ? 'Редактирование прогона' : 'Новый прогон'" />
      <div class="run-form" aria-busy="true" aria-label="Загрузка формы">
        <AppSkeleton v-for="n in 5" :key="n" height="2.5rem" radius="md" />
      </div>
    </template>

    <template v-else-if="forbidden">
      <PageHeader :back="back" />
      <ErrorState
        error="Изменять прогон могут его мастера, организаторы конвента и администраторы."
        title="Недостаточно прав"
      />
    </template>

    <template v-else>
      <PageHeader :title="isEdit ? 'Редактирование прогона' : 'Новый прогон'" :back="back" />

      <form ref="formEl" class="run-form" novalidate @submit.prevent="submit">
        <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>
        <AppAlert v-if="initial.eventDenied" tone="warning">
          Добавлять прогоны в расписание конвента могут только его организаторы. Этот прогон будет создан
          отдельным, вне конвента.
        </AppAlert>

        <FormField
          v-if="event"
          label="Конвент"
          :hint="isEdit ? 'Прогон стоит в расписании этого проведения.' : 'Прогон войдёт в расписание этого проведения.'"
        >
          <p class="run-form__static">
            <RouterLink :to="{ name: 'event', params: { id: event.id } }">{{ event.conventionName }}</RouterLink>
            <span class="text-muted"> · {{ formatDateRange(event.dateStart, event.dateEnd) }}</span>
          </p>
        </FormField>

        <FormField label="Игра" required :error="errors.game">
          <GamePicker v-model="form.game" label="Игра" required />
        </FormField>

        <FormField
          label="Город"
          required
          :error="errors.city"
          :hint="cityLocked ? 'Город определяется проведением конвента.' : ''"
        >
          <template v-if="!cityLocked" #labelAside>
            <button type="button" class="run-form__link" @click="cityDialog = true">Добавить город</button>
          </template>
          <CitySelect
            v-model="form.cityId"
            placeholder="Выберите город"
            :disabled="cityLocked"
            @change="onCityChange"
          />
        </FormField>

        <div class="run-form__row">
          <FormField label="Дата и время начала" required :error="errors.date" :hint="dateHint">
            <AppInput v-model="form.date" type="datetime-local" :min="dateMin" :max="dateMax" />
          </FormField>
          <FormField label="Длительность" required :error="errors.duration" :hint="durationHint">
            <AppInput v-model="form.duration" type="number" inputmode="numeric" min="1" step="5" />
          </FormField>
        </div>

        <FormField
          v-if="form.cityId"
          label="Площадка"
          :hint="
            venueLocked
              ? 'Площадка определяется проведением конвента.'
              : !venuesLoading && !venueOptions.length
                ? 'В этом городе площадок пока нет — добавить их можно в разделе «Площадки».'
                : ''
          "
        >
          <AppSelect
            v-model="form.venueId"
            :options="venueOptions"
            placeholder="Не указана"
            :disabled="venueLocked || (!venueOptions.length && !form.venueId)"
            @change="onVenueChange"
          />
        </FormField>

        <FormField v-if="venue" label="Помещения" :error="errors.rooms">
          <template #default="{ id: fieldId, describedBy }">
            <div
              v-if="venue.rooms.length"
              :id="fieldId"
              class="run-form__rooms"
              role="group"
              aria-label="Помещения"
              :aria-describedby="describedBy"
            >
              <AppCheckbox
                v-for="(room, index) in venue.rooms"
                :key="room.id"
                v-model="form.roomIds"
                :value="room.id"
                :aria-invalid="errors.rooms && index === 0 ? 'true' : undefined"
              >
                {{ room.name }}<span v-if="room.blackbox && !/blackbox|бл[эе]кбокс/i.test(room.name)" class="text-muted"> · блэкбокс</span>
              </AppCheckbox>
            </div>
            <p v-else class="text-muted">
              У этой площадки ещё нет помещений, а прогон привязывается к площадке через них. Добавьте помещение на
              <RouterLink :to="{ name: 'venue', params: { id: venue.id } }">странице площадки</RouterLink>.
            </p>
          </template>
        </FormField>

        <FormField label="Лимит игроков" :error="errors.maxPlayers" :hint="maxPlayersHint" class="run-form__short">
          <AppInput v-model="form.maxPlayers" type="number" inputmode="numeric" min="1" />
        </FormField>

        <AppCheckbox v-model="form.registrationOpen">Регистрация открыта</AppCheckbox>

        <div class="run-form__actions">
          <AppButton type="submit" variant="primary" :loading="saving">
            {{ isEdit ? 'Сохранить' : 'Добавить прогон' }}
          </AppButton>
          <AppButton :to="cancelTo" :disabled="saving">Отмена</AppButton>
        </div>
      </form>
    </template>

    <CityDialog v-model:open="cityDialog" @created="onCityCreated" />
  </div>
</template>

<style scoped>
.run-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding-bottom: var(--space-10);
}
.run-form__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 220px);
  gap: var(--space-4);
  align-items: start;
}
.run-form__short {
  max-width: 320px;
}
.run-form__static {
  overflow-wrap: anywhere;
}
.run-form__link {
  padding: 0;
  border: 0;
  background: none;
  color: var(--accent-text);
  font-size: var(--text-sm);
  text-decoration: underline;
}
.run-form__rooms {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-5);
  padding-block: var(--space-1);
}
.run-form__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

@media (max-width: 519px) {
  .run-form__row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
