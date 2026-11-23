<script setup>
import { ref } from 'vue'
import { moveFocus } from '@/utils/roving'

/**
 * Переключатель из 2–4 взаимоисключающих вариантов (вид списка, период и т.п.).
 *   <SegmentedControl v-model="view" :options="[{ value: 'grid', label: 'Сетка' }, { value: 'list', label: 'Список' }]" label="Вид" />
 */
defineProps({
  options: { type: Array, required: true },
  /** Подпись группы для экранных дикторов. */
  label: { type: String, required: true },
  /** sm | md */
  size: { type: String, default: 'md' },
})
const model = defineModel({ type: [String, Number], required: true })
const group = ref(null)

function onKeydown(event) {
  const target = moveFocus(event, group.value, '[role="radio"]')
  if (target) target.click()
}
</script>

<template>
  <div ref="group" class="segmented" :class="`segmented--${size}`" role="radiogroup" :aria-label="label" @keydown="onKeydown">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      role="radio"
      class="segmented__option"
      :aria-checked="option.value === model"
      :tabindex="option.value === model ? 0 : -1"
      @click="model = option.value"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.segmented {
  display: inline-flex;
  padding: 2px;
  border-radius: var(--radius-md);
  background: var(--surface-2);
  border: 1px solid var(--border);
}
.segmented__option {
  min-height: calc(var(--control-h-md) - 6px);
  padding: 0 var(--space-3);
  border: 0;
  border-radius: calc(var(--radius-md) - 2px);
  background: transparent;
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: 550;
  white-space: nowrap;
}
.segmented--sm .segmented__option {
  min-height: calc(var(--control-h-sm) - 6px);
}
.segmented__option:hover {
  color: var(--text);
}
.segmented__option[aria-checked='true'] {
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow-sm);
}
</style>
