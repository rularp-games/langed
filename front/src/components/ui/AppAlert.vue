<script setup>
import { computed } from 'vue'
import { CircleAlert, CircleCheck, Info, TriangleAlert } from '@lucide/vue'

/** Встроенное сообщение в форме или на странице (общая ошибка формы, подсказка, успех). */
const props = defineProps({
  /** info | success | warning | danger */
  tone: { type: String, default: 'info' },
  title: { type: String, default: '' },
})

const icons = { info: Info, success: CircleCheck, warning: TriangleAlert, danger: CircleAlert }
const icon = computed(() => icons[props.tone] || Info)
</script>

<template>
  <div class="alert" :class="`alert--${tone}`" :role="tone === 'danger' ? 'alert' : 'status'">
    <component :is="icon" :size="18" class="alert__icon" aria-hidden="true" />
    <div class="alert__body">
      <p v-if="title" class="alert__title">{{ title }}</p>
      <slot />
    </div>
  </div>
</template>

<style scoped>
.alert {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--info-soft);
  color: var(--text);
}
.alert__icon {
  flex: none;
  margin-top: 1px;
  color: var(--info-text);
}
.alert__body {
  min-width: 0;
}
.alert__title {
  font-weight: 600;
}
.alert--success {
  background: var(--success-soft);
}
.alert--success .alert__icon {
  color: var(--success-text);
}
.alert--warning {
  background: var(--warning-soft);
}
.alert--warning .alert__icon {
  color: var(--warning-text);
}
.alert--danger {
  background: var(--danger-soft);
}
.alert--danger .alert__icon {
  color: var(--danger-text);
}
</style>
