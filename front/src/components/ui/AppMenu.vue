<script setup>
import { nextTick, onBeforeUnmount, provide, ref, useId, watch } from 'vue'
import { moveFocus } from '@/utils/roving'

/**
 * Выпадающее меню. Кнопка — в слоте `trigger` (получает attrs и toggle), пункты — AppMenuItem
 * в слоте по умолчанию.
 *   <AppMenu>
 *     <template #trigger="{ attrs, toggle }">
 *       <AppButton v-bind="attrs" @click="toggle">Ещё</AppButton>
 *     </template>
 *     <AppMenuItem @select="edit">Изменить</AppMenuItem>
 *   </AppMenu>
 */
defineProps({
  /** Сторона, к которой прижато меню: start | end */
  align: { type: String, default: 'end' },
  label: { type: String, default: '' },
})

const open = ref(false)
const root = ref(null)
const menu = ref(null)
const menuId = `menu-${useId()}`
const ITEM = '[role^="menuitem"]'

function close({ focusTrigger = false } = {}) {
  if (!open.value) return
  open.value = false
  if (focusTrigger) root.value?.querySelector('[aria-haspopup]')?.focus()
}

function toggle() {
  open.value = !open.value
}

function onDocumentPointerDown(event) {
  if (!root.value?.contains(event.target)) close()
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.stopPropagation()
    close({ focusTrigger: true })
  } else if (event.key === 'Tab') {
    close()
  } else {
    moveFocus(event, menu.value, ITEM, { vertical: true })
  }
}

watch(open, async (value) => {
  if (value) {
    document.addEventListener('pointerdown', onDocumentPointerDown)
    await nextTick()
    const items = menu.value?.querySelectorAll(ITEM) ?? []
    const current = [...items].find((el) => el.getAttribute('aria-checked') === 'true')
    ;(current || items[0])?.focus()
  } else {
    document.removeEventListener('pointerdown', onDocumentPointerDown)
  }
})
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocumentPointerDown))

provide('appMenu', { close })
</script>

<template>
  <div ref="root" class="menu">
    <slot
      name="trigger"
      :open="open"
      :toggle="toggle"
      :attrs="{ 'aria-haspopup': 'menu', 'aria-expanded': open, 'aria-controls': open ? menuId : undefined }"
    />
    <div
      v-if="open"
      :id="menuId"
      ref="menu"
      class="menu__list"
      :class="`menu__list--${align}`"
      role="menu"
      :aria-label="label || undefined"
      @keydown="onKeydown"
    >
      <slot :close="close" />
    </div>
  </div>
</template>

<style scoped>
.menu {
  position: relative;
  display: inline-flex;
}
.menu__list {
  position: absolute;
  top: calc(100% + var(--space-1));
  z-index: 30;
  min-width: 200px;
  max-width: min(320px, calc(100vw - 2 * var(--space-4)));
  padding: var(--space-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--shadow-md);
}
.menu__list--end {
  right: 0;
}
.menu__list--start {
  left: 0;
}
</style>
