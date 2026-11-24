<script setup>
import { computed } from 'vue'
import { textSegments } from '@/utils/game'

/**
 * Авторы игры, записанные текстом (ещё не зарегистрированы на портале).
 * Ссылки в тексте кликабельны; текст выводится без v-html — разбором на сегменты.
 */
const props = defineProps({
  text: { type: String, required: true },
})

const segments = computed(() => textSegments(props.text))
</script>

<template>
  <p class="authors-text">
    <template v-for="(segment, index) in segments" :key="index">
      <a
        v-if="segment.type === 'link'"
        :href="segment.href"
        target="_blank"
        rel="noopener noreferrer nofollow"
        class="authors-text__link"
      >{{ segment.text }}</a>
      <template v-else>{{ segment.text }}</template>
    </template>
  </p>
</template>

<style scoped>
.authors-text {
  white-space: pre-line;
  overflow-wrap: anywhere;
}
</style>
