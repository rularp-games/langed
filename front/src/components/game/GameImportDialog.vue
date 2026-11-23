<script setup>
import { ref, watch } from 'vue'
import { gamesApi } from '@/api/games'
import { plural } from '@/utils/format'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppDialog from '@/components/ui/AppDialog.vue'

/**
 * Импорт игр из CSV (только staff). Событие imported — после успешной загрузки,
 * чтобы страница обновила список.
 */
const open = defineModel('open', { type: Boolean, default: false })
const emit = defineEmits(['imported'])

const file = ref(null)
const fileError = ref('')
const formError = ref('')
const result = ref(null)
const loading = ref(false)

watch(open, (value) => {
  if (!value) return
  file.value = null
  fileError.value = ''
  formError.value = ''
  result.value = null
  loading.value = false
})

function onChange(event) {
  const picked = event.target.files?.[0] ?? null
  file.value = picked
  result.value = null
  formError.value = ''
  // Backend проверяет расширение с учётом регистра — повторяем его правило.
  fileError.value = picked && !picked.name.endsWith('.csv') ? 'Нужен файл с расширением .csv' : ''
}

const created = (n) => `${plural(n, ['Создана', 'Создано', 'Создано'])} ${n} ${plural(n, ['игра', 'игры', 'игр'])}`
const skipped = (n) => `${plural(n, ['пропущена', 'пропущено', 'пропущено'])} ${n}`

async function submit() {
  if (loading.value) return
  if (!file.value) {
    fileError.value = 'Выберите файл'
    return
  }
  if (fileError.value) return
  loading.value = true
  formError.value = ''
  try {
    result.value = await gamesApi.importCsv(file.value)
    if (result.value.created) emit('imported', result.value)
  } catch (err) {
    formError.value = err?.detail || 'Не удалось импортировать файл. Попробуйте ещё раз.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AppDialog v-model:open="open" title="Импорт игр из CSV" size="md" :dismissible="!loading">
    <form id="game-import-form" class="import" novalidate @submit.prevent="submit">
      <p>
        Файл в кодировке UTF-8, первая строка — заголовки колонок. Используются три колонки
        (регистр букв в заголовках не важен):
      </p>
      <dl class="import__columns">
        <div>
          <dt>Название</dt>
          <dd>обязательная; строки без названия пропускаются</dd>
        </div>
        <div>
          <dt>Анонс</dt>
          <dd>описание игры для игроков</dd>
        </div>
        <div>
          <dt>Красные флаги</dt>
          <dd>предупреждения о содержании</dd>
        </div>
      </dl>
      <p class="text-muted">
        Игры, название которых уже есть в каталоге, не изменяются и считаются пропущенными. Остальные колонки
        файла игнорируются.
      </p>

      <div class="import__file">
        <label for="game-import-file" class="import__label">Файл CSV</label>
        <input
          id="game-import-file"
          type="file"
          accept=".csv,text/csv"
          class="import__input"
          :disabled="loading"
          :aria-invalid="fileError ? 'true' : undefined"
          :aria-describedby="fileError ? 'game-import-file-error' : undefined"
          @change="onChange"
        />
        <p v-if="fileError" id="game-import-file-error" class="import__error" role="alert">{{ fileError }}</p>
      </div>

      <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>
      <AppAlert v-if="result" :tone="result.created ? 'success' : 'info'">
        {{ created(result.created) }}, {{ skipped(result.skipped) }}.
      </AppAlert>
    </form>
    <template #footer>
      <AppButton :disabled="loading" @click="open = false">{{ result ? 'Закрыть' : 'Отмена' }}</AppButton>
      <AppButton type="submit" form="game-import-form" variant="primary" :loading="loading">Импортировать</AppButton>
    </template>
  </AppDialog>
</template>

<style scoped>
.import {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.import__columns {
  border-top: 1px solid var(--border);
}
.import__columns div {
  display: grid;
  grid-template-columns: 9.5rem minmax(0, 1fr);
  gap: var(--space-3);
  padding-block: var(--space-2);
  border-bottom: 1px solid var(--border);
}
.import__columns dt {
  font-weight: 550;
}
.import__columns dd {
  color: var(--text-muted);
}
.import__file {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}
.import__label {
  font-size: var(--text-sm);
  font-weight: 550;
}
.import__input {
  max-width: 100%;
  font: inherit;
  color: var(--text);
}
.import__error {
  color: var(--danger-text);
  font-size: var(--text-sm);
}

@media (max-width: 519px) {
  .import__columns div {
    grid-template-columns: minmax(0, 1fr);
    gap: 0;
  }
}
</style>
