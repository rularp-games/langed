<script setup>
import AppAvatar from './AppAvatar.vue'

/** Аватар + имя в одну строку (автор игры, мастер, участник). */
defineProps({
  name: { type: String, required: true },
  src: { type: String, default: '' },
  /** Размер аватара в пикселях. */
  size: { type: Number, default: 24 },
})
</script>

<template>
  <span class="user-chip">
    <AppAvatar :name="name" :src="src" :size="size" />
    <span class="user-chip__name">{{ name }}</span>
  </span>
</template>

<style scoped>
.user-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  max-width: 100%;
}
.user-chip__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
