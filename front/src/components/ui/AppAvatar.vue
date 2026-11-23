<script setup>
import { computed, ref, watch } from 'vue'
import { initials } from '@/utils/format'

/** Аватар: картинка либо инициалы. Декоративен — имя должно быть написано рядом. */
const props = defineProps({
  name: { type: String, default: '' },
  src: { type: String, default: '' },
  /** Размер в пикселях. */
  size: { type: Number, default: 28 },
})

const failed = ref(false)
watch(
  () => props.src,
  () => (failed.value = false),
)
const letters = computed(() => initials(props.name))
</script>

<template>
  <span class="avatar" :style="{ width: `${size}px`, height: `${size}px`, fontSize: `${size * 0.4}px` }" aria-hidden="true">
    <img v-if="src && !failed" :src="src" alt="" loading="lazy" @error="failed = true" />
    <template v-else>{{ letters }}</template>
  </span>
</template>

<style scoped>
.avatar {
  display: inline-grid;
  place-items: center;
  flex: none;
  border-radius: var(--radius-full);
  background: var(--accent-soft);
  color: var(--accent-text);
  font-weight: 600;
  line-height: 1;
  overflow: hidden;
  user-select: none;
}
.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
