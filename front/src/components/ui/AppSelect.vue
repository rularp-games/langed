<script setup>
import { computed } from 'vue'
import { ChevronDown } from '@lucide/vue'
import { useFormField } from '@/composables/useFormField'

defineOptions({ inheritAttrs: false })

defineProps({
  /** [{ value, label, disabled? }]; вместо этого можно передать <option> в слот. */
  options: { type: Array, default: () => [] },
  /** Пункт-заглушка с пустым значением. */
  placeholder: { type: String, default: '' },
  /** sm | md | lg */
  size: { type: String, default: 'md' },
})

const model = defineModel({ type: [String, Number, null], default: '' })
const fieldAttrs = useFormField()
// class и style, переданные компоненту, относятся к обёртке (ширина, место в сетке), остальное — к <select>.
const controlAttrs = computed(() => {
  const { class: _class, style: _style, ...rest } = fieldAttrs.value
  return rest
})
</script>

<template>
  <div class="select" :class="$attrs.class" :style="$attrs.style">
    <select v-model="model" v-bind="controlAttrs" class="control" :class="`control--${size}`">
      <option v-if="placeholder" value="">{{ placeholder }}</option>
      <slot>
        <option
          v-for="option in options"
          :key="option.value"
          :value="option.value"
          :disabled="option.disabled"
        >
          {{ option.label }}
        </option>
      </slot>
    </select>
    <ChevronDown class="select__icon" :size="16" aria-hidden="true" />
  </div>
</template>

<style scoped>
.select {
  position: relative;
}
/* :where — чтобы ширину можно было переопределить классом с места использования. */
:where(.select) {
  width: 100%;
}
.select .control {
  appearance: none;
  padding-right: var(--space-8);
  cursor: pointer;
}
.select__icon {
  position: absolute;
  top: 50%;
  right: var(--space-3);
  translate: 0 -50%;
  color: var(--text-muted);
  pointer-events: none;
}
</style>
