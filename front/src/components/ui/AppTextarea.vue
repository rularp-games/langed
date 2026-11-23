<script setup>
import { useFormField } from '@/composables/useFormField'

defineOptions({ inheritAttrs: false })

defineProps({
  rows: { type: [Number, String], default: 4 },
})

const model = defineModel({ type: String, default: '' })
const controlAttrs = useFormField()
</script>

<template>
  <textarea v-model="model" v-bind="controlAttrs" :rows="rows" class="control"></textarea>
</template>
