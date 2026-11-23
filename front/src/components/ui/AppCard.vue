<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

/** Поверхность-карточка. С `to` вся карточка — ссылка (внутри не должно быть других кнопок/ссылок). */
const props = defineProps({
  /** Тег корневого элемента, если карточка не ссылка. */
  as: { type: String, default: 'div' },
  to: { type: [String, Object], default: null },
  /** none | sm | md */
  padding: { type: String, default: 'md' },
})

const tag = computed(() => (props.to ? RouterLink : props.as))
</script>

<template>
  <component
    :is="tag"
    :to="to || undefined"
    class="card"
    :class="[`card--pad-${padding}`, { 'card--link': to }]"
  >
    <slot />
  </component>
</template>

<style scoped>
.card {
  display: block;
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  color: var(--text);
  overflow: hidden;
}
.card--pad-sm {
  padding: var(--space-3);
}
.card--pad-md {
  padding: var(--space-4);
}
.card--link {
  text-decoration: none;
  transition:
    border-color var(--duration),
    box-shadow var(--duration);
}
.card--link:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
  color: var(--text);
}
</style>
