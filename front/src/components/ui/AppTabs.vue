<script setup>
import { ref } from 'vue'
import { moveFocus } from '@/utils/roving'

/**
 * Полоса вкладок (только переключатель; содержимое вкладки рендерит страница по v-model).
 *   <AppTabs v-model="tab" :tabs="[{ value: 'about', label: 'Описание' }, { value: 'runs', label: 'Прогоны', count: 3 }]" label="Разделы игры" />
 */
defineProps({
  tabs: { type: Array, required: true },
  /** Подпись группы для экранных дикторов. */
  label: { type: String, default: '' },
})
const model = defineModel({ type: [String, Number], required: true })
const list = ref(null)

function onKeydown(event) {
  const target = moveFocus(event, list.value, '[role="tab"]')
  if (target) model.value = target.dataset.value
}
</script>

<template>
  <div ref="list" class="tabs" role="tablist" :aria-label="label || undefined" @keydown="onKeydown">
    <button
      v-for="tab in tabs"
      :key="tab.value"
      type="button"
      role="tab"
      class="tabs__tab"
      :data-value="tab.value"
      :aria-selected="String(tab.value) === String(model)"
      :tabindex="String(tab.value) === String(model) ? 0 : -1"
      @click="model = tab.value"
    >
      {{ tab.label }}
      <span v-if="tab.count != null" class="tabs__count">{{ tab.count }}</span>
    </button>
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: var(--space-5);
  border-bottom: 1px solid var(--border);
  overflow-x: auto;
  scrollbar-width: none;
}
.tabs__tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) 0;
  margin-bottom: -1px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--text-muted);
  font-weight: 550;
  white-space: nowrap;
}
.tabs__tab:hover {
  color: var(--text);
}
.tabs__tab[aria-selected='true'] {
  border-bottom-color: var(--accent);
  color: var(--text);
}
.tabs__tab:focus-visible {
  outline-offset: -2px;
}
.tabs__count {
  font-size: var(--text-xs);
  color: var(--text-subtle);
}
</style>
