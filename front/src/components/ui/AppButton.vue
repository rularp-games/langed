<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import AppSpinner from './AppSpinner.vue'

const props = defineProps({
  /** primary | secondary | ghost | danger */
  variant: { type: String, default: 'secondary' },
  /** sm | md | lg */
  size: { type: String, default: 'md' },
  loading: Boolean,
  disabled: Boolean,
  /** На всю ширину контейнера. */
  block: Boolean,
  /** Квадратная кнопка с одной иконкой — обязательно передать aria-label. */
  iconOnly: Boolean,
  /** Маршрут — кнопка рендерится как <router-link>. */
  to: { type: [String, Object], default: null },
  /** Внешняя ссылка — кнопка рендерится как <a>. */
  href: { type: String, default: null },
  type: { type: String, default: 'button' },
})

const inactive = computed(() => props.disabled || props.loading)
const tag = computed(() => (props.to ? RouterLink : props.href ? 'a' : 'button'))
const tagAttrs = computed(() => {
  if (props.to) return { to: props.to, 'aria-disabled': inactive.value || undefined }
  if (props.href) return { href: props.href, 'aria-disabled': inactive.value || undefined }
  return { type: props.type, disabled: inactive.value }
})

function onClick(event) {
  if (inactive.value) {
    event.preventDefault()
    event.stopImmediatePropagation()
  }
}
</script>

<template>
  <component
    :is="tag"
    v-bind="tagAttrs"
    class="btn"
    :class="[
      `btn--${variant}`,
      `btn--${size}`,
      { 'btn--block': block, 'btn--icon': iconOnly, 'is-inactive': inactive },
    ]"
    :aria-busy="loading || undefined"
    @click.capture="onClick"
  >
    <AppSpinner v-if="loading" :size="16" />
    <slot v-if="!(loading && iconOnly)" />
  </component>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: var(--control-h-md);
  padding: 0 var(--space-4);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text);
  font-size: var(--text-base);
  font-weight: 550;
  line-height: 1.2;
  text-decoration: none;
  white-space: nowrap;
  user-select: none;
  transition:
    background-color var(--duration),
    border-color var(--duration),
    color var(--duration);
}

.btn--sm {
  min-height: var(--control-h-sm);
  padding: 0 var(--space-3);
  font-size: var(--text-sm);
}
.btn--lg {
  min-height: var(--control-h-lg);
  padding: 0 var(--space-5);
}
.btn--block {
  display: flex;
  width: 100%;
}
.btn--icon {
  padding: 0;
  aspect-ratio: 1;
}

.btn--primary {
  background: var(--accent);
  color: var(--on-accent);
}
.btn--primary:hover {
  background: var(--accent-hover);
  color: var(--on-accent);
}

.btn--secondary {
  background: var(--surface);
  border-color: var(--border-strong);
}
.btn--secondary:hover {
  background: var(--surface-hover);
  color: var(--text);
}

.btn--ghost {
  color: var(--text-muted);
}
.btn--ghost:hover {
  background: var(--surface-hover);
  color: var(--text);
}

.btn--danger {
  background: var(--danger-solid);
  color: var(--on-danger);
}
.btn--danger:hover {
  background: var(--danger-solid-hover);
  color: var(--on-danger);
}

.is-inactive {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
