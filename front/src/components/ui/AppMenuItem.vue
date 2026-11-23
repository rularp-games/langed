<script setup>
import { computed, inject } from 'vue'
import { RouterLink } from 'vue-router'
import { Check } from '@lucide/vue'

/** Пункт AppMenu: кнопка (событие select) либо ссылка (to). `checked` делает пункт радио-вариантом. */
const props = defineProps({
  to: { type: [String, Object], default: null },
  /** true/false — пункт-переключатель (menuitemradio); не задано — обычный пункт. */
  checked: { type: Boolean, default: undefined },
  danger: Boolean,
})
const emit = defineEmits(['select'])
const menu = inject('appMenu', null)

const isRadio = computed(() => props.checked !== undefined)

function onClick() {
  emit('select')
  menu?.close({ focusTrigger: !props.to })
}
</script>

<template>
  <component
    :is="to ? RouterLink : 'button'"
    :to="to || undefined"
    :type="to ? undefined : 'button'"
    class="menu-item"
    :class="{ 'menu-item--danger': danger }"
    :role="isRadio ? 'menuitemradio' : 'menuitem'"
    :aria-checked="isRadio ? checked : undefined"
    tabindex="-1"
    @click="onClick"
  >
    <span class="menu-item__content"><slot /></span>
    <Check v-if="checked" :size="16" class="menu-item__check" aria-hidden="true" />
  </component>
</template>

<style scoped>
.menu-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  min-height: var(--control-h-md);
  padding: 0 var(--space-3);
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text);
  font-size: var(--text-base);
  text-align: left;
  text-decoration: none;
}
.menu-item:hover,
.menu-item:focus-visible {
  background: var(--surface-hover);
  color: var(--text);
  outline-offset: -2px;
}
.menu-item--danger {
  color: var(--danger-text);
}
.menu-item__content {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
}
.menu-item__check {
  flex: none;
  color: var(--accent-text);
}
</style>
