<script setup>
import { Globe, Link, MessagesSquare, Play, Send, Users } from '@lucide/vue'

/** Ссылки конвента (convention.links / event.links) с иконкой по типу. Пустой список не рендерится. */
defineProps({
  /** [{id, url, type, displayTitle}] */
  links: { type: Array, default: () => [] },
})

// Нейтральные иконки по смыслу площадки, без фирменных знаков.
const icons = { website: Globe, vk: Users, telegram: Send, discord: MessagesSquare, youtube: Play, other: Link }
</script>

<template>
  <ul v-if="links.length" class="links">
    <li v-for="link in links" :key="link.id">
      <a :href="link.url" target="_blank" rel="noopener noreferrer" class="links__item">
        <component :is="icons[link.type] || Link" :size="16" class="links__icon" aria-hidden="true" />
        <span class="links__title">{{ link.displayTitle }}</span>
      </a>
    </li>
  </ul>
</template>

<style scoped>
.links {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-5);
}
.links__item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  max-width: 100%;
  min-height: 1.75rem;
}
.links__icon {
  flex: none;
  color: var(--text-muted);
}
.links__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
