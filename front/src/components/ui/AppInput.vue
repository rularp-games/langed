<script setup>
import { ref } from 'vue'
import { useFormField } from '@/composables/useFormField'

defineOptions({ inheritAttrs: false })

defineProps({
  type: { type: String, default: 'text' },
  /** sm | md | lg */
  size: { type: String, default: 'md' },
})

const model = defineModel({ type: [String, Number], default: '' })
const controlAttrs = useFormField()
const input = ref(null)

defineExpose({ focus: () => input.value?.focus() })
</script>

<template>
  <div class="input" :class="{ 'input--has-suffix': $slots.suffix }">
    <input
      ref="input"
      v-model="model"
      v-bind="controlAttrs"
      :type="type"
      class="control"
      :class="`control--${size}`"
    />
    <span v-if="$slots.suffix" class="input__suffix"><slot name="suffix" /></span>
  </div>
</template>

<style scoped>
.input {
  position: relative;
  width: 100%;
}
.input--has-suffix .control {
  padding-right: var(--control-h-md);
}
.input__suffix {
  position: absolute;
  inset: 0 0 0 auto;
  display: flex;
  align-items: center;
  padding-right: var(--space-1);
}
</style>
