<script setup>
import { computed, onMounted } from 'vue'
import { useCitiesStore } from '@/stores/cities'
import AppSelect from './ui/AppSelect.vue'

/**
 * Выбор города. v-model — id города (число) или '' (не выбран).
 * По умолчанию показывает весь справочник /api/cities/ (кэш в useCitiesStore); для фильтров
 * можно передать свой список, например runsApi.cities() — только города с прогонами.
 * Работает внутри FormField; прочие атрибуты (aria-label, disabled) уходят на <select>.
 */
const props = defineProps({
  /** Свой список [{id, name}] вместо справочника. */
  cities: { type: Array, default: null },
  /** Подпись пустого варианта: «Все города» для фильтра, «Выберите город» для формы. */
  placeholder: { type: String, default: 'Все города' },
  /** sm | md | lg */
  size: { type: String, default: 'md' },
})
const model = defineModel({ type: [Number, String], default: '' })

const store = useCitiesStore()
onMounted(() => {
  if (!props.cities) store.load().catch(() => {})
})

const options = computed(() =>
  (props.cities ?? store.items).map((city) => ({ value: city.id, label: city.name })),
)
</script>

<template>
  <AppSelect v-model="model" :options="options" :placeholder="placeholder" :size="size" />
</template>
