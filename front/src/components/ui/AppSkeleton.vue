<script setup>
/** Заглушка на время загрузки. Декоративна: статус загрузки объявляет контейнер (aria-busy). */
defineProps({
  width: { type: String, default: '100%' },
  height: { type: String, default: '1em' },
  /** Радиус: sm | md | lg | full */
  radius: { type: String, default: 'sm' },
})
</script>

<template>
  <span
    class="skeleton"
    :style="{ width, height, borderRadius: `var(--radius-${radius})` }"
    aria-hidden="true"
  ></span>
</template>

<style scoped>
.skeleton {
  display: block;
  background: var(--surface-2);
  animation: skeleton-pulse 1.4s ease-in-out infinite;
}
@keyframes skeleton-pulse {
  50% {
    opacity: 0.5;
  }
}
</style>
