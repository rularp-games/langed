<script setup>
import { onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { X } from '@lucide/vue'
import { useUiStore } from '@/stores/ui'
import AppButton from './AppButton.vue'

/**
 * Модальный диалог на нативном <dialog>: ловушка фокуса, Esc и возврат фокуса — от браузера,
 * прокрутка страницы блокируется в base.css. Содержимое существует только пока диалог открыт,
 * поэтому формы внутри каждый раз начинают с чистого состояния.
 * Фокус при открытии получает элемент с атрибутом autofocus, иначе — первый фокусируемый.
 */
const props = defineProps({
  title: { type: String, default: '' },
  /** sm (420px) | md (560px) | lg (760px) */
  size: { type: String, default: 'sm' },
  /** false — нельзя закрыть по Esc, клику по подложке и крестику (идёт сохранение и т.п.). */
  dismissible: { type: Boolean, default: true },
})
const emit = defineEmits(['close'])
const open = defineModel('open', { type: Boolean, default: false })

const ui = useUiStore()
const dialog = ref(null)
const titleId = `dialog-${useId()}`
let pressedOnBackdrop = false

function sync(value) {
  const el = dialog.value
  if (!el) return
  if (value && !el.open) {
    el.showModal()
    ui.registerModal(el)
  } else if (!value && el.open) {
    el.close()
  }
}

watch(open, sync, { flush: 'post' })
onMounted(() => sync(open.value))
onBeforeUnmount(() => {
  if (!dialog.value) return
  ui.unregisterModal(dialog.value)
  if (dialog.value.open) dialog.value.close()
})

function requestClose() {
  if (props.dismissible) open.value = false
}

function onNativeClose() {
  ui.unregisterModal(dialog.value)
  open.value = false
  emit('close')
}

function onPointerDown(event) {
  pressedOnBackdrop = event.target === dialog.value
}

function onClick(event) {
  // Закрываем, только если и нажатие, и отпускание пришлись на подложку
  // (иначе диалог закрывался бы при выделении текста с выходом за край).
  if (pressedOnBackdrop && event.target === dialog.value) requestClose()
  pressedOnBackdrop = false
}
</script>

<template>
  <dialog
    ref="dialog"
    class="dialog"
    :class="`dialog--${size}`"
    :aria-labelledby="title || $slots.header ? titleId : undefined"
    @cancel.prevent="requestClose"
    @close="onNativeClose"
    @pointerdown="onPointerDown"
    @click="onClick"
  >
    <div v-if="open" class="dialog__panel">
      <header class="dialog__header">
        <h2 :id="titleId" class="dialog__title">
          <slot name="header">{{ title }}</slot>
        </h2>
        <AppButton
          v-if="dismissible"
          variant="ghost"
          size="sm"
          icon-only
          aria-label="Закрыть"
          class="dialog__close"
          @click="requestClose"
        >
          <X :size="18" aria-hidden="true" />
        </AppButton>
      </header>
      <div class="dialog__body"><slot /></div>
      <footer v-if="$slots.footer" class="dialog__footer"><slot name="footer" /></footer>
    </div>
  </dialog>
</template>

<style scoped>
.dialog {
  width: calc(100% - 2 * var(--space-4));
  max-width: 420px;
  max-height: calc(100dvh - 2 * var(--space-4));
  padding: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}
.dialog--md {
  max-width: 560px;
}
.dialog--lg {
  max-width: 760px;
}

.dialog[open] {
  display: flex;
  animation: dialog-in var(--duration) ease-out;
}
.dialog::backdrop {
  background: var(--backdrop);
}

@keyframes dialog-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
}

.dialog__panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 0;
}
.dialog__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-5) 0;
}
.dialog__title {
  font-size: var(--text-lg);
  padding-top: 2px;
}
.dialog__close {
  flex: none;
  margin: -2px calc(-1 * var(--space-2)) 0 0;
}
.dialog__body {
  padding: var(--space-4) var(--space-5) var(--space-5);
  overflow-y: auto;
  overscroll-behavior: contain;
}
.dialog__footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-5);
  border-top: 1px solid var(--border);
  background: var(--surface-2);
}
</style>
