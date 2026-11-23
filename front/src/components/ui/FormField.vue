<script setup>
import { computed, provide, useId } from 'vue'

/**
 * Обёртка поля формы: подпись, подсказка, ошибка. Вложенные AppInput / AppTextarea /
 * AppSelect сами получают id, aria-describedby, aria-invalid и required.
 */
const props = defineProps({
  label: { type: String, default: '' },
  hint: { type: String, default: '' },
  /** Текст ошибки; пусто — ошибки нет. */
  error: { type: String, default: '' },
  required: Boolean,
})

const uid = useId()
const id = `field-${uid}`
const hintId = `${id}-hint`
const errorId = `${id}-error`

const describedBy = computed(
  () => [props.error && errorId, props.hint && hintId].filter(Boolean).join(' ') || undefined,
)

const field = {
  id,
  describedBy,
  invalid: computed(() => Boolean(props.error)),
  required: computed(() => props.required),
}
provide('formField', field)
</script>

<template>
  <div class="field">
    <div v-if="label || $slots.labelAside" class="field__head">
      <label v-if="label" :for="id" class="field__label">
        {{ label }}<span v-if="required" class="field__required" aria-hidden="true"> *</span>
      </label>
      <span v-if="$slots.labelAside" class="field__aside"><slot name="labelAside" /></span>
    </div>
    <slot :id="id" :described-by="describedBy" :invalid="Boolean(error)" />
    <p v-if="error" :id="errorId" class="field__error" role="alert">{{ error }}</p>
    <p v-if="hint" :id="hintId" class="field__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}
.field__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
}
.field__label {
  font-size: var(--text-sm);
  font-weight: 550;
}
.field__required {
  color: var(--danger-text);
}
.field__aside {
  font-size: var(--text-sm);
}
.field__hint {
  font-size: var(--text-sm);
  color: var(--text-muted);
}
.field__error {
  font-size: var(--text-sm);
  color: var(--danger-text);
}
</style>
