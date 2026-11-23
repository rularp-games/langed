<script setup>
import { watch } from 'vue'
import AppButton from './AppButton.vue'
import AppDialog from './AppDialog.vue'

/** Подтверждение действия. Обычно вызывается через useConfirm(), напрямую — редко. */
defineProps({
  title: { type: String, default: 'Подтвердите действие' },
  message: { type: String, default: '' },
  confirmText: { type: String, default: 'Подтвердить' },
  cancelText: { type: String, default: 'Отмена' },
  /** Опасное действие (удаление): красная кнопка подтверждения. */
  danger: Boolean,
  loading: Boolean,
})
const emit = defineEmits(['confirm', 'cancel'])
const open = defineModel('open', { type: Boolean, default: false })

// «cancel» — только если диалог закрыли без подтверждения.
let confirmed = false
watch(open, (value) => {
  if (value) confirmed = false
})

function onConfirm() {
  confirmed = true
  emit('confirm')
}

function onClose() {
  if (!confirmed) emit('cancel')
}
</script>

<template>
  <AppDialog v-model:open="open" :title="title" :dismissible="!loading" @close="onClose">
    <p class="confirm__message"><slot>{{ message }}</slot></p>
    <template #footer>
      <AppButton autofocus :disabled="loading" @click="open = false">{{ cancelText }}</AppButton>
      <AppButton :variant="danger ? 'danger' : 'primary'" :loading="loading" @click="onConfirm">
        {{ confirmText }}
      </AppButton>
    </template>
  </AppDialog>
</template>

<style scoped>
.confirm__message {
  color: var(--text-muted);
  white-space: pre-line;
}
</style>
