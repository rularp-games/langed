<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { CircleAlert, CircleCheck, Info, TriangleAlert, X } from '@lucide/vue'
import { useUiStore } from '@/stores/ui'

/**
 * Область уведомлений; подключается один раз в App.vue. Показ — через useToast().
 * Контейнер выводится в top layer (popover), а при открытом модальном диалоге переносится
 * внутрь него: всё вне <dialog> браузер делает неактивным, и крестик нельзя было бы нажать.
 */
const ui = useUiStore()
const host = ref(null)
const icons = { info: Info, success: CircleCheck, warning: TriangleAlert, error: CircleAlert }

function raise() {
  const el = host.value
  if (!el?.showPopover) return
  try {
    if (el.matches(':popover-open')) el.hidePopover()
    if (ui.toasts.length) el.showPopover()
  } catch {
    // Popover API недоступен — остаётся обычный position: fixed.
  }
}

onMounted(raise)
watch(
  () => ui.toasts.length,
  (length, previous) => {
    if (length > previous || length === 0) nextTick(raise)
  },
)
// После переноса в другой контейнер popover закрывается — открываем заново поверх диалога.
watch(
  () => ui.topModal,
  () => nextTick(raise),
  { flush: 'post' },
)
</script>

<template>
  <Teleport :to="ui.topModal || 'body'">
  <div ref="host" class="toasts" popover="manual" aria-live="polite" aria-atomic="false">
    <TransitionGroup name="toast">
      <div
        v-for="toast in ui.toasts"
        :key="toast.id"
        class="toast"
        :class="`toast--${toast.type}`"
        :role="toast.type === 'error' ? 'alert' : 'status'"
      >
        <component :is="icons[toast.type] || Info" :size="18" class="toast__icon" aria-hidden="true" />
        <div class="toast__body">
          <p v-if="toast.title" class="toast__title">{{ toast.title }}</p>
          <p>{{ toast.message }}</p>
        </div>
        <button type="button" class="toast__close" aria-label="Закрыть уведомление" @click="ui.dismissToast(toast.id)">
          <X :size="16" aria-hidden="true" />
        </button>
      </div>
    </TransitionGroup>
  </div>
  </Teleport>
</template>

<style scoped>
.toasts {
  position: fixed;
  inset: auto var(--space-4) var(--space-4) auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: min(380px, calc(100vw - 2 * var(--space-4)));
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  overflow: visible;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--border);
  border-left-width: 3px;
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--text);
  font-size: var(--text-sm);
  box-shadow: var(--shadow-md);
  pointer-events: auto;
}
.toast__icon {
  flex: none;
  margin-top: 1px;
}
.toast__body {
  flex: 1;
  min-width: 0;
}
.toast__title {
  font-weight: 600;
}
.toast__close {
  flex: none;
  display: grid;
  place-items: center;
  width: 1.5rem;
  height: 1.5rem;
  margin: -2px -2px 0 0;
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-subtle);
}
.toast__close:hover {
  background: var(--surface-hover);
  color: var(--text);
}

.toast--info {
  border-left-color: var(--info-text);
}
.toast--info .toast__icon {
  color: var(--info-text);
}
.toast--success {
  border-left-color: var(--success-text);
}
.toast--success .toast__icon {
  color: var(--success-text);
}
.toast--warning {
  border-left-color: var(--warning-text);
}
.toast--warning .toast__icon {
  color: var(--warning-text);
}
.toast--error {
  border-left-color: var(--danger-text);
}
.toast--error .toast__icon {
  color: var(--danger-text);
}

.toast-enter-active,
.toast-leave-active {
  transition:
    opacity var(--duration),
    transform var(--duration);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
