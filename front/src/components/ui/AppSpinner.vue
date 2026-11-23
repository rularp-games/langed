<script setup>
import { LoaderCircle } from '@lucide/vue'

defineProps({
  size: { type: [Number, String], default: 18 },
  /** Текст для экранных дикторов; пусто — индикатор декоративный. */
  label: { type: String, default: '' },
})
</script>

<template>
  <span class="spinner" :role="label ? 'status' : undefined">
    <LoaderCircle :size="size" aria-hidden="true" />
    <span v-if="label" class="visually-hidden">{{ label }}</span>
  </span>
</template>

<style scoped>
.spinner {
  display: inline-flex;
}
.spinner svg {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
