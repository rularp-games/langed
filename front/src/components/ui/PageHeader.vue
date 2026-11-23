<script setup>
import { ArrowLeft } from '@lucide/vue'

/**
 * Компактный заголовок страницы: необязательная ссылка «назад», h1, действия справа.
 * Слот `meta` — короткая подпись рядом с заголовком (счётчик); слот по умолчанию —
 * строка под заголовком (поиск, фильтры).
 */
defineProps({
  title: { type: String, default: '' },
  /** { to, label } — ссылка на родительский раздел. */
  back: { type: Object, default: null },
})
</script>

<template>
  <header class="page-header">
    <RouterLink v-if="back" :to="back.to" class="page-header__back">
      <ArrowLeft :size="16" aria-hidden="true" />
      {{ back.label }}
    </RouterLink>
    <div class="page-header__row">
      <div class="page-header__heading">
        <h1 v-if="title || $slots.title"><slot name="title">{{ title }}</slot></h1>
        <span v-if="$slots.meta" class="page-header__meta"><slot name="meta" /></span>
      </div>
      <div v-if="$slots.actions" class="page-header__actions"><slot name="actions" /></div>
    </div>
    <div v-if="$slots.default" class="page-header__tools"><slot /></div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-block: var(--space-5) var(--space-4);
}
.page-header__back {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  align-self: flex-start;
  color: var(--text-muted);
  font-size: var(--text-sm);
  text-decoration: none;
}
.page-header__back:hover {
  color: var(--text);
}
.page-header__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
.page-header__heading {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-1) var(--space-3);
  min-width: 0;
}
.page-header__meta {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.page-header__tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}
</style>
