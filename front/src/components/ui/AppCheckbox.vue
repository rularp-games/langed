<script setup>
defineOptions({ inheritAttrs: false })

/** v-model — boolean либо массив значений (как у нативного чекбокса). Подпись — в слоте. */
const model = defineModel({ type: [Boolean, Array], default: false })
</script>

<template>
  <label class="checkbox">
    <input v-model="model" v-bind="$attrs" type="checkbox" class="checkbox__input" />
    <span class="checkbox__label"><slot /></span>
  </label>
</template>

<style scoped>
.checkbox {
  display: inline-flex;
  align-items: flex-start;
  gap: var(--space-2);
  cursor: pointer;
}
.checkbox__input {
  flex: none;
  width: 1.125rem;
  height: 1.125rem;
  margin: 0.15em 0 0;
  accent-color: var(--accent);
  cursor: pointer;
}
.checkbox:has(:disabled) {
  color: var(--text-subtle);
  cursor: not-allowed;
}
</style>
