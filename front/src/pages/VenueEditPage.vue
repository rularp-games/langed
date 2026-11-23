<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@lucide/vue'
import { ApiError } from '@/api/client'
import { venuesApi } from '@/api/venues'
import { useAsyncData } from '@/composables/useAsyncData'
import { usePageTitle } from '@/composables/usePageTitle'
import { useToast } from '@/composables/useToast'
import CitySelect from '@/components/CitySelect.vue'
import CityDialog from '@/components/venue/CityDialog.vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import AppTextarea from '@/components/ui/AppTextarea.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import FormField from '@/components/ui/FormField.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  /** Идентификатор площадки; не задан — создание новой. */
  id: { type: String, default: null },
})

const router = useRouter()
const toast = useToast()
const isEdit = computed(() => Boolean(props.id))

const { data: venue, error: loadError, reload } = useAsyncData(
  (signal) => (props.id ? venuesApi.get(props.id, { signal }) : Promise.resolve(null)),
  { watch: () => props.id },
)

const back = computed(() =>
  isEdit.value
    ? { to: { name: 'venue', params: { id: props.id } }, label: venue.value?.name || 'К площадке' }
    : { to: { name: 'venues' }, label: 'Все площадки' },
)
usePageTitle(() => (venue.value ? `${venue.value.name} — редактирование` : ''))

const form = reactive({ name: '', cityId: '', address: '', description: '', capacity: '' })
const errors = ref({})
const formError = ref('')
const saving = ref(false)
const formEl = ref(null)
const cityDialogOpen = ref(false)

// Форму заполняем один раз: повторная загрузка (вход/выход) не должна стирать введённое.
let filledFor = null
watch(venue, (value) => {
  if (!value || filledFor === value.id) return
  filledFor = value.id
  Object.assign(form, {
    name: value.name,
    cityId: value.city?.id ?? '',
    address: value.address,
    description: value.description,
    capacity: value.capacity ?? '',
  })
})

function onCityCreated(city) {
  form.cityId = city.id
  toast.success(`Город «${city.name}» добавлен`)
}

function validate() {
  const result = {}
  if (!form.name.trim()) result.name = 'Укажите название площадки'
  if (!form.cityId) result.cityId = 'Выберите город'
  if (form.capacity !== '' && form.capacity !== null) {
    const capacity = Number(form.capacity)
    if (!Number.isInteger(capacity) || capacity < 1) result.capacity = 'Укажите целое число больше нуля или оставьте поле пустым'
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
      name: err.field('name'),
      cityId: err.field('cityId'),
      address: err.field('address'),
      description: err.field('description'),
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
  saving.value = true
  const data = {
    name: form.name.trim(),
    cityId: Number(form.cityId),
    address: form.address.trim(),
    description: form.description.trim(),
    capacity: form.capacity === '' || form.capacity === null ? null : Number(form.capacity),
  }
  try {
    const saved = isEdit.value ? await venuesApi.update(props.id, data) : await venuesApi.create(data)
    toast.success(isEdit.value ? 'Площадка сохранена' : 'Площадка добавлена')
    router.push({ name: 'venue', params: { id: saved.id } })
  } catch (err) {
    applyError(err)
    await focusFirstError()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="container container--narrow">
    <template v-if="loadError">
      <PageHeader :back="back" />
      <ErrorState
        :error="loadError"
        title="Не удалось загрузить площадку"
        not-found-title="Площадка не найдена"
        @retry="reload"
      />
    </template>

    <template v-else-if="isEdit && !venue">
      <PageHeader :back="back">
        <template #title><AppSkeleton width="min(320px, 70vw)" height="1.2em" /></template>
      </PageHeader>
      <div aria-busy="true" aria-label="Загрузка площадки">
        <AppSkeleton v-for="n in 4" :key="n" height="2.5rem" radius="md" class="venue-form__skeleton" />
      </div>
    </template>

    <template v-else>
      <PageHeader :title="isEdit ? 'Редактирование площадки' : 'Новая площадка'" :back="back" />

      <form ref="formEl" class="venue-form" novalidate @submit.prevent="submit">
        <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>

        <FormField label="Название" :error="errors.name" required>
          <AppInput v-model="form.name" maxlength="255" autocomplete="off" />
        </FormField>

        <div class="venue-form__row">
          <FormField label="Город" :error="errors.cityId" required class="venue-form__city">
            <template #labelAside>
              <button type="button" class="venue-form__add-city" @click="cityDialogOpen = true">
                <Plus :size="14" aria-hidden="true" />
                Добавить город
              </button>
            </template>
            <CitySelect v-model="form.cityId" placeholder="Выберите город" />
          </FormField>

          <FormField label="Вместимость" :error="errors.capacity" hint="Сколько человек помещается. Необязательно.">
            <AppInput v-model="form.capacity" type="number" min="1" step="1" inputmode="numeric">
              <template #suffix>чел.</template>
            </AppInput>
          </FormField>
        </div>

        <FormField label="Адрес" :error="errors.address" hint="Улица, дом, этаж или название здания.">
          <AppTextarea v-model="form.address" rows="2" />
        </FormField>

        <FormField
          label="Описание"
          :error="errors.description"
          hint="Как добраться, что есть на площадке, условия для игр."
        >
          <AppTextarea v-model="form.description" rows="6" />
        </FormField>

        <p v-if="!isEdit" class="venue-form__note">Помещения можно будет добавить на странице площадки после сохранения.</p>

        <div class="venue-form__actions">
          <AppButton type="submit" variant="primary" :loading="saving">
            {{ isEdit ? 'Сохранить' : 'Добавить площадку' }}
          </AppButton>
          <AppButton :to="back.to" :disabled="saving">Отмена</AppButton>
        </div>
      </form>

      <CityDialog v-model:open="cityDialogOpen" @created="onCityCreated" />
    </template>
  </div>
</template>

<style scoped>
.venue-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding-bottom: var(--space-10);
}
.venue-form__skeleton {
  margin-bottom: var(--space-4);
}
.venue-form__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 220px);
  gap: var(--space-4);
  align-items: start;
}
.venue-form__add-city {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--accent-text);
  font-size: var(--text-sm);
}
.venue-form__add-city:hover {
  text-decoration: underline;
}
.venue-form__note {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.venue-form__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

@media (max-width: 519px) {
  .venue-form__row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
