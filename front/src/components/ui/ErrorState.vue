<script setup>
import { computed } from 'vue'
import { CircleAlert, RotateCw, SearchX } from '@lucide/vue'
import AppButton from './AppButton.vue'
import EmptyState from './EmptyState.vue'

/**
 * Ошибка загрузки. Для 404 показывает «не найдено» без кнопки повтора.
 *   <ErrorState v-else-if="error" :error="error" @retry="reload" />
 */
const props = defineProps({
  /** ApiError (или любой объект с detail/status) либо строка. */
  error: { type: [Object, String], default: null },
  title: { type: String, default: '' },
  /** Заголовок для случая 404. */
  notFoundTitle: { type: String, default: 'Страница не найдена' },
})
defineEmits(['retry'])

const notFound = computed(() => props.error?.status === 404)
const heading = computed(() => {
  if (notFound.value) return props.notFoundTitle
  return props.title || 'Не удалось загрузить данные'
})
const description = computed(() => {
  if (notFound.value) return 'Возможно, ссылка устарела или запись удалена.'
  return typeof props.error === 'string' ? props.error : props.error?.detail || ''
})
</script>

<template>
  <EmptyState :title="heading" :description="description" :icon="notFound ? SearchX : CircleAlert" role="alert">
    <slot>
      <AppButton v-if="!notFound" @click="$emit('retry')">
        <RotateCw :size="16" aria-hidden="true" />
        Повторить
      </AppButton>
    </slot>
  </EmptyState>
</template>
