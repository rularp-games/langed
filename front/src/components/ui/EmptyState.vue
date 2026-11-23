<script setup>
import { Inbox } from '@lucide/vue'

/** Пустое состояние списка или раздела. Кнопки действий — в слот по умолчанию. */
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  /** Компонент иконки из @lucide/vue. */
  icon: { type: [Object, Function], default: () => Inbox },
})
</script>

<template>
  <div class="state">
    <component :is="icon" :size="32" class="state__icon" aria-hidden="true" />
    <p class="state__title">{{ title }}</p>
    <p v-if="description" class="state__description">{{ description }}</p>
    <div v-if="$slots.default" class="state__actions"><slot /></div>
  </div>
</template>

<style scoped>
.state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-12) var(--space-4);
  text-align: center;
}
.state__icon {
  color: var(--text-subtle);
  margin-bottom: var(--space-1);
}
.state__title {
  font-size: var(--text-md);
  font-weight: 600;
}
.state__description {
  max-width: 44ch;
  color: var(--text-muted);
}
.state__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-2);
  margin-top: var(--space-3);
}
</style>
