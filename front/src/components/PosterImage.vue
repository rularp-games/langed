<script setup>
import { ref, watch } from 'vue'
import { ImageOff } from '@lucide/vue'

/**
 * Постер с ленивой загрузкой и заглушкой, если картинки нет или она не загрузилась.
 * Размер и пропорции задаёт родитель (класс/стиль на компоненте).
 */
const props = defineProps({
  src: { type: String, default: null },
  alt: { type: String, default: '' },
  /** cover — обрезать под рамку; contain — показать целиком. */
  fit: { type: String, default: 'cover' },
  /** false — для картинки в первом экране (страница игры). */
  lazy: { type: Boolean, default: true },
})

const failed = ref(false)
watch(
  () => props.src,
  () => (failed.value = false),
)
</script>

<template>
  <div class="poster">
    <img
      v-if="src && !failed"
      :src="src"
      :alt="alt"
      :loading="lazy ? 'lazy' : 'eager'"
      decoding="async"
      :style="{ objectFit: fit }"
      @error="failed = true"
    />
    <ImageOff v-else class="poster__placeholder" :size="24" aria-hidden="true" />
  </div>
</template>

<style scoped>
.poster {
  display: grid;
  place-items: center;
  background: var(--surface-2);
  color: var(--border-strong);
  overflow: hidden;
}
.poster img {
  width: 100%;
  height: 100%;
}
</style>
