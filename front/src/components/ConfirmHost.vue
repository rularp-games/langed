<script setup>
import { useUiStore } from '@/stores/ui'
import ConfirmDialog from './ui/ConfirmDialog.vue'

/** Единственный экземпляр диалога подтверждения для useConfirm(); подключён в App.vue. */
const ui = useUiStore()
</script>

<template>
  <ConfirmDialog
    :open="ui.confirmState.open"
    v-bind="ui.confirmState.options"
    @update:open="(value) => !value && ui.settleConfirm(false)"
    @confirm="ui.settleConfirm(true)"
  />
</template>
