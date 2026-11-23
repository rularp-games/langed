<script setup>
import { reactive, ref, watch } from 'vue'
import { citiesApi } from '@/api/cities'
import { useCitiesStore } from '@/stores/cities'
import { DEFAULT_TIMEZONE, TIMEZONES } from '@/utils/timezones'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import FormField from '@/components/ui/FormField.vue'

/**
 * Добавление города в справочник (любой вошедший) или правка существующего (staff, prop city).
 * События: created — с новым городом, saved — с изменённым; useCitiesStore уже обновлён.
 */
const props = defineProps({
  /** Город для правки; не задан — диалог создаёт новый. */
  city: { type: Object, default: null },
})
const emit = defineEmits(['created', 'saved'])
const open = defineModel('open', { type: Boolean, default: false })

const cities = useCitiesStore()
const form = reactive({ name: '', timezone: DEFAULT_TIMEZONE })
const errors = ref({})
const formError = ref('')
const saving = ref(false)

watch(open, (value) => {
  if (!value) return
  form.name = props.city?.name ?? ''
  form.timezone = props.city?.timezone ?? DEFAULT_TIMEZONE
  errors.value = {}
  formError.value = ''
  saving.value = false
})

async function submit() {
  if (saving.value) return
  errors.value = {}
  formError.value = ''
  const name = form.name.trim()
  if (!name) {
    errors.value = { name: 'Укажите название города' }
    return
  }
  const lower = name.toLocaleLowerCase('ru')
  if (cities.items.some((city) => city.id !== props.city?.id && city.name.toLocaleLowerCase('ru') === lower)) {
    errors.value = { name: props.city ? 'Город с таким названием уже есть' : 'Такой город уже есть в списке — выберите его' }
    return
  }
  saving.value = true
  try {
    if (props.city) {
      const city = await citiesApi.update(props.city.id, { name, timezone: form.timezone })
      cities.replace(city)
      emit('saved', city)
    } else {
      const city = await citiesApi.create({ name, timezone: form.timezone })
      cities.add(city)
      emit('created', city)
    }
    open.value = false
  } catch (err) {
    errors.value = { name: err?.field?.('name'), timezone: err?.field?.('timezone') }
    if (!errors.value.name && !errors.value.timezone) {
      formError.value = err?.detail || 'Не удалось сохранить город. Попробуйте ещё раз.'
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppDialog v-model:open="open" :title="city ? 'Изменить город' : 'Новый город'" :dismissible="!saving">
    <form id="city-form" class="city-form" novalidate @submit.prevent="submit">
      <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>
      <FormField label="Название" :error="errors.name" required>
        <AppInput v-model="form.name" maxlength="255" autocomplete="off" autofocus />
      </FormField>
      <FormField
        label="Часовой пояс"
        :error="errors.timezone"
        hint="По нему показывается время прогонов и расписание конвентов в этом городе."
        required
      >
        <AppSelect v-model="form.timezone" :options="TIMEZONES" />
      </FormField>
    </form>
    <template #footer>
      <AppButton :disabled="saving" @click="open = false">Отмена</AppButton>
      <AppButton type="submit" form="city-form" variant="primary" :loading="saving">
        {{ city ? 'Сохранить' : 'Добавить' }}
      </AppButton>
    </template>
  </AppDialog>
</template>

<style scoped>
.city-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
</style>
