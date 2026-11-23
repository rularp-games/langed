<script setup>
import { computed, ref, watch } from 'vue'
import { eventsApi } from '@/api/events'
import { useAuthDialog } from '@/composables/useAuthDialog'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { plural } from '@/utils/format'
import { eventAvailability, eventSeatsLabel } from '@/utils/registration'
import RegistrationStatusBadge from '@/components/RegistrationStatusBadge.vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppTextarea from '@/components/ui/AppTextarea.vue'
import FormField from '@/components/ui/FormField.vue'

/**
 * Регистрация участника на проведение конвента: состояние, места, заявка с комментарием,
 * собственная заявка со статусом и отменой. После изменения — событие `changed` (родитель
 * перезагружает проведение).
 */
const props = defineProps({
  /** Проведение (eventsApi.schedule). */
  event: { type: Object, required: true },
})
const emit = defineEmits(['changed'])

const auth = useAuthStore()
const toast = useToast()
const confirm = useConfirm()
const { requireAuth } = useAuthDialog()

const availability = computed(() => eventAvailability(props.event))
const mine = computed(() => props.event.myRegistration)
const seats = computed(() => (availability.value.key === 'open' ? eventSeatsLabel(props.event) : ''))
const participants = computed(() => {
  const n = props.event.registrationsCount
  if (!n) return ''
  const total = props.event.capacity ? ` из ${props.event.capacity}` : ''
  return `${n}${total} ${plural(n, ['участник', 'участника', 'участников'])}`
})

const formOpen = ref(false)
const comment = ref('')
const submitting = ref(false)
const cancelling = ref(false)
const failure = ref('')

watch(
  () => [props.event.id, mine.value?.id ?? null, auth.user?.id ?? null],
  () => {
    formOpen.value = false
    failure.value = ''
  },
)

const statusNote = computed(() => {
  switch (mine.value?.status) {
    case 'pending':
      return 'Организаторы ещё не подтвердили заявку. Записываться на прогоны можно после подтверждения.'
    case 'confirmed':
      return 'Участие подтверждено — можно записываться на прогоны из расписания.'
    case 'rejected':
      return 'Организаторы отклонили заявку.'
    case 'cancelled':
      return 'Заявка отменена. Её можно удалить и подать заново.'
    default:
      return ''
  }
})

function start() {
  requireAuth(
    () => {
      // После входа заявка могла уже найтись — тогда форма не нужна.
      if (!props.event.myRegistration) formOpen.value = true
    },
    { reason: 'Войдите, чтобы зарегистрироваться на конвент.' },
  )
}

async function submit() {
  if (submitting.value) return
  submitting.value = true
  failure.value = ''
  try {
    const { message } = await eventsApi.register(props.event.id, { comment: comment.value.trim() })
    toast.success(message || 'Заявка отправлена')
    comment.value = ''
    formOpen.value = false
    emit('changed')
  } catch (err) {
    failure.value = err.detail || 'Не удалось отправить заявку. Попробуйте ещё раз.'
  } finally {
    submitting.value = false
  }
}

async function cancel() {
  const ok = await confirm({
    title: 'Отменить регистрацию?',
    message:
      mine.value.status === 'confirmed'
        ? 'Ваше участие в конвенте будет отменено, заявка удалится. Записи на предстоящие прогоны конвента тоже будут сняты.'
        : 'Заявка на участие будет удалена.',
    confirmText: 'Отменить регистрацию',
    cancelText: 'Не отменять',
    danger: true,
  })
  if (!ok) return
  cancelling.value = true
  try {
    const { runsUnregistered: n } = await eventsApi.unregister(props.event.id)
    toast.success(
      n
        ? `Регистрация отменена. Также ${plural(n, ['снята', 'сняты', 'сняты'])} ${plural(n, ['запись', 'записи', 'записи'])} на ${n} ${plural(n, ['прогон', 'прогона', 'прогонов'])}`
        : 'Регистрация отменена',
    )
    emit('changed')
  } catch (err) {
    toast.apiError(err, 'Не удалось отменить регистрацию')
  } finally {
    cancelling.value = false
  }
}
</script>

<template>
  <section class="ereg" aria-labelledby="ereg-title">
    <h2 id="ereg-title" class="ereg__title">Участие в конвенте</h2>

    <p class="ereg__state">
      <RegistrationStatusBadge v-if="mine" :status="mine.status" mine />
      <AppBadge v-if="!mine || availability.key !== 'open'" :tone="availability.tone">{{ availability.label }}</AppBadge>
      <span v-if="participants" class="ereg__count">{{ participants }}</span>
      <span v-if="seats" class="ereg__count">{{ seats }}</span>
    </p>

    <template v-if="mine">
      <p v-if="statusNote" class="ereg__note">{{ statusNote }}</p>
      <dl v-if="mine.comment || mine.adminComment" class="ereg__comments">
        <div v-if="mine.comment">
          <dt>Ваш комментарий</dt>
          <dd class="prose">{{ mine.comment }}</dd>
        </div>
        <div v-if="mine.adminComment">
          <dt>Ответ организаторов</dt>
          <dd class="prose">{{ mine.adminComment }}</dd>
        </div>
      </dl>
      <AppButton v-if="availability.key !== 'past'" size="sm" :loading="cancelling" @click="cancel">
        Отменить регистрацию
      </AppButton>
    </template>

    <template v-else-if="availability.canRegister">
      <form v-if="formOpen" class="ereg__form" novalidate @submit.prevent="submit">
        <AppAlert v-if="failure" tone="danger">{{ failure }}</AppAlert>
        <FormField label="Комментарий для организаторов" hint="Необязательно">
          <AppTextarea v-model="comment" rows="2" maxlength="1000" autofocus />
        </FormField>
        <div class="ereg__actions">
          <AppButton variant="primary" type="submit" :loading="submitting">Отправить заявку</AppButton>
          <AppButton :disabled="submitting" @click="formOpen = false">Отмена</AppButton>
        </div>
      </form>
      <template v-else>
        <p class="ereg__note">Заявку подтверждают организаторы. После подтверждения можно записываться на прогоны.</p>
        <AppButton variant="primary" @click="start">Зарегистрироваться</AppButton>
      </template>
    </template>

    <p v-else-if="availability.key === 'full'" class="ereg__note">Все места на конвент заняты.</p>
    <p v-else-if="availability.key === 'closed'" class="ereg__note">Организаторы пока не открыли регистрацию.</p>
  </section>
</template>

<style scoped>
.ereg {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
}
.ereg__title {
  font-size: var(--text-md);
}
.ereg__state {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2) var(--space-3);
}
.ereg__count {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.ereg__note {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.ereg__comments {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  align-self: stretch;
  font-size: var(--text-sm);
}
.ereg__comments dt {
  color: var(--text-muted);
}
.ereg__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  align-self: stretch;
}
.ereg__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>
