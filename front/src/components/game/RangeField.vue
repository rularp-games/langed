<script setup>
import { useId } from 'vue'
import AppInput from '@/components/ui/AppInput.vue'

/**
 * Пара числовых полей «от — до» с общей подписью (игроки, женские и мужские роли).
 *   <RangeField v-model:min="form.playersMin" v-model:max="form.playersMax" label="Игроки" :error="errors.players" />
 */
defineProps({
  label: { type: String, required: true },
  error: { type: String, default: '' },
  required: Boolean,
})
const min = defineModel('min', { type: [Number, String], default: '' })
const max = defineModel('max', { type: [Number, String], default: '' })

const uid = useId()
const labelId = `range-${uid}`
const errorId = `${labelId}-error`
</script>

<template>
  <div class="range" role="group" :aria-labelledby="labelId">
    <p :id="labelId" class="range__label">
      {{ label }}<span v-if="required" class="range__required" aria-hidden="true"> *</span>
    </p>
    <div class="range__inputs">
      <AppInput
        v-model="min"
        type="number"
        min="0"
        step="1"
        inputmode="numeric"
        placeholder="от"
        :aria-label="`${label}: от`"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="error ? errorId : undefined"
      />
      <span class="range__dash" aria-hidden="true">–</span>
      <AppInput
        v-model="max"
        type="number"
        min="0"
        step="1"
        inputmode="numeric"
        placeholder="до"
        :aria-label="`${label}: до`"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="error ? errorId : undefined"
      />
    </div>
    <p v-if="error" :id="errorId" class="range__error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.range {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}
.range__label {
  font-size: var(--text-sm);
  font-weight: 550;
}
.range__required {
  color: var(--danger-text);
}
.range__inputs {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: var(--space-2);
}
.range__dash {
  color: var(--text-subtle);
}
.range__error {
  color: var(--danger-text);
  font-size: var(--text-sm);
}
</style>
