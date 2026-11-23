<script setup>
import { computed } from 'vue'
import { registrationStatusMeta } from '@/utils/registration'
import AppBadge from './ui/AppBadge.vue'

/**
 * Статус заявки на прогон или на конвент (pending | confirmed | waitlist | rejected | cancelled).
 *   <RegistrationStatusBadge :status="registration.status" />        — «Ожидает подтверждения»
 *   <RegistrationStatusBadge :status="run.myRegistration.status" mine />  — «Заявка на рассмотрении»
 */
const props = defineProps({
  status: { type: String, required: true },
  /** Формулировка для самого участника («Вы участвуете») вместо нейтральной («Подтверждена»). */
  mine: Boolean,
})

const meta = computed(() => registrationStatusMeta(props.status))
</script>

<template>
  <AppBadge :tone="meta.tone">{{ mine ? meta.mine : meta.label }}</AppBadge>
</template>
