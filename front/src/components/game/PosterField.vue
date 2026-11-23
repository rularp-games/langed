<script setup>
import { computed, onBeforeUnmount, ref, useId, watch } from 'vue'
import { ImagePlus, RefreshCw, Trash2 } from '@lucide/vue'
import AppButton from '@/components/ui/AppButton.vue'

/**
 * Постер игры в форме: выбор файла с предпросмотром, замена и удаление.
 *   <PosterField v-model:file="posterFile" v-model:removed="posterRemoved" :current="game?.poster" />
 * file — выбранный File (или null), removed — пользователь убрал сохранённый постер.
 * Backend принимает любое изображение, которое распознаёт Pillow, и не ограничивает размер;
 * ограничения ниже — клиентские (те же, что были в прежнем интерфейсе).
 */
const ACCEPT = ['image/jpeg', 'image/png', 'image/webp']
const MAX_SIZE_MB = 5

const props = defineProps({
  /** Адрес сохранённого постера (при редактировании). */
  current: { type: String, default: null },
  disabled: Boolean,
})
const file = defineModel('file', { type: [Object, null], default: null })
const removed = defineModel('removed', { type: Boolean, default: false })

const uid = useId()
const inputId = `poster-${uid}`
const hintId = `${inputId}-hint`
const errorId = `${inputId}-error`
const input = ref(null)
const error = ref('')
const previewUrl = ref(null)

function revoke() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = null
}

watch(file, (value) => {
  revoke()
  if (value) previewUrl.value = URL.createObjectURL(value)
})
onBeforeUnmount(revoke)

const shown = computed(() => previewUrl.value || (removed.value ? null : props.current))

function pick() {
  input.value?.click()
}

function onChange(event) {
  const picked = event.target.files?.[0]
  // Сбрасываем значение, чтобы повторный выбор того же файла снова вызвал change.
  event.target.value = ''
  if (!picked) return
  if (!ACCEPT.includes(picked.type)) {
    error.value = 'Подойдёт изображение в формате JPG, PNG или WebP.'
    return
  }
  if (picked.size > MAX_SIZE_MB * 1024 * 1024) {
    error.value = `Файл больше ${MAX_SIZE_MB} МБ. Уменьшите изображение и выберите его снова.`
    return
  }
  error.value = ''
  file.value = picked
  removed.value = false
}

function remove() {
  error.value = ''
  file.value = null
  removed.value = true
}
</script>

<template>
  <div class="poster-field" role="group" :aria-labelledby="`${inputId}-label`">
    <p :id="`${inputId}-label`" class="poster-field__label">Постер</p>
    <div class="poster-field__row">
      <img v-if="shown" :src="shown" alt="Выбранный постер" class="poster-field__preview" />
      <div v-else class="poster-field__empty" aria-hidden="true">
        <ImagePlus :size="24" />
      </div>
      <div class="poster-field__side">
        <div class="poster-field__actions">
          <AppButton size="sm" :disabled="disabled" :aria-describedby="hintId" @click="pick">
            <component :is="shown ? RefreshCw : ImagePlus" :size="16" aria-hidden="true" />
            {{ shown ? 'Заменить' : 'Выбрать файл' }}
          </AppButton>
          <AppButton v-if="shown" size="sm" variant="ghost" :disabled="disabled" @click="remove">
            <Trash2 :size="16" aria-hidden="true" />
            Убрать
          </AppButton>
        </div>
        <p v-if="file" class="poster-field__name">{{ file.name }}</p>
        <p v-if="error" :id="errorId" class="poster-field__error" role="alert">{{ error }}</p>
        <p :id="hintId" class="poster-field__hint">
          JPG, PNG или WebP, до {{ MAX_SIZE_MB }} МБ. Постер показывается в каталоге и на афише.
        </p>
      </div>
    </div>
    <input
      :id="inputId"
      ref="input"
      type="file"
      class="visually-hidden"
      tabindex="-1"
      aria-hidden="true"
      :accept="ACCEPT.join(',')"
      :disabled="disabled"
      @change="onChange"
    />
  </div>
</template>

<style scoped>
.poster-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}
.poster-field__label {
  font-size: var(--text-sm);
  font-weight: 550;
}
.poster-field__row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  min-width: 0;
}
.poster-field__preview,
.poster-field__empty {
  flex: none;
  width: 120px;
  height: 160px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-2);
}
.poster-field__preview {
  object-fit: contain;
}
.poster-field__empty {
  display: grid;
  place-items: center;
  border-style: dashed;
  border-color: var(--border-strong);
  color: var(--text-subtle);
}
.poster-field__side {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}
.poster-field__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.poster-field__name {
  overflow-wrap: anywhere;
  font-size: var(--text-sm);
}
.poster-field__hint {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.poster-field__error {
  color: var(--danger-text);
  font-size: var(--text-sm);
}

@media (max-width: 519px) {
  .poster-field__preview,
  .poster-field__empty {
    width: 90px;
    height: 120px;
  }
}
</style>
