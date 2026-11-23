<script setup>
import { ref, watch } from 'vue'
import { conventionsApi } from '@/api/conventions'
import { plural } from '@/utils/format'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import FormField from '@/components/ui/FormField.vue'

/** Импорт конвентов и проведений из CSV (только staff). Событие `imported` — после успешной загрузки. */
const emit = defineEmits(['imported'])
const open = defineModel('open', { type: Boolean, default: false })

const file = ref(null)
const error = ref('')
const result = ref(null)
const loading = ref(false)

watch(open, (value) => {
  if (!value) return
  file.value = null
  error.value = ''
  result.value = null
})

function onFile(event) {
  file.value = event.target.files?.[0] ?? null
  error.value = ''
  result.value = null
}

async function submit() {
  if (loading.value) return
  if (!file.value) {
    error.value = 'Выберите файл CSV'
    return
  }
  if (!file.value.name.toLowerCase().endsWith('.csv')) {
    error.value = 'Нужен файл с расширением .csv'
    return
  }
  loading.value = true
  error.value = ''
  try {
    result.value = await conventionsApi.importCsv(file.value)
    emit('imported', result.value)
  } catch (err) {
    error.value = err.detail || 'Не удалось импортировать файл'
  } finally {
    loading.value = false
  }
}

const count = (n, forms) => `${n} ${plural(n, forms)}`
</script>

<template>
  <AppDialog v-model:open="open" title="Импорт конвентов из CSV" size="md" :dismissible="!loading">
    <AppAlert v-if="result" tone="success" title="Импорт завершён">
      Создано конвентов: {{ result.conventionsCreated }}, проведений: {{ result.eventsCreated }}, пропущено
      {{ count(result.eventsSkipped, ['проведение', 'проведения', 'проведений']) }} (уже есть в базе).
    </AppAlert>

    <form v-else id="conventions-import-form" class="import" novalidate @submit.prevent="submit">
      <p class="import__note">
        Файл в кодировке UTF-8 со столбцами «Название мероприятия», «Город», «Дата начала», «Дата конца». Даты — в виде
        ДД.ММ.ГГГГ или ГГГГ-ММ-ДД. Недостающие конвенты и города создаются, уже существующие проведения пропускаются.
      </p>
      <FormField label="Файл CSV" :error="error" required>
        <template #default="{ id, describedBy, invalid }">
          <input
            :id="id"
            type="file"
            accept=".csv,text/csv"
            class="import__file"
            :aria-describedby="describedBy"
            :aria-invalid="invalid ? 'true' : undefined"
            :disabled="loading"
            @change="onFile"
          />
        </template>
      </FormField>
    </form>

    <template #footer>
      <AppButton v-if="result" variant="primary" @click="open = false">Готово</AppButton>
      <template v-else>
        <AppButton :disabled="loading" @click="open = false">Отмена</AppButton>
        <AppButton variant="primary" type="submit" form="conventions-import-form" :loading="loading">Импортировать</AppButton>
      </template>
    </template>
  </AppDialog>
</template>

<style scoped>
.import {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.import__note {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.import__file {
  max-width: 100%;
  font-size: var(--text-sm);
}
</style>
