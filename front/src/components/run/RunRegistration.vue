<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { runsApi } from '@/api/runs'
import { useAuthDialog } from '@/composables/useAuthDialog'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { ROLE_PREFERENCES, runAvailability, runSeatsLabel } from '@/utils/registration'
import { plural } from '@/utils/format'
import RegistrationStatusBadge from '@/components/RegistrationStatusBadge.vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppCheckbox from '@/components/ui/AppCheckbox.vue'
import AppTextarea from '@/components/ui/AppTextarea.vue'
import FormField from '@/components/ui/FormField.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'

/**
 * Блок записи на прогон: места, состояние записи, форма заявки и собственная заявка игрока.
 * Обновлённый прогон (ответ register / unregister) отдаёт родителю событием `update`.
 */
const props = defineProps({
  /** Полный прогон из runsApi.get. */
  run: { type: Object, required: true },
})
const emit = defineEmits(['update'])

const auth = useAuthStore()
const toast = useToast()
const confirm = useConfirm()
const { requireAuth } = useAuthDialog()

const availability = computed(() => runAvailability(props.run))
const mine = computed(() => props.run.myRegistration)
const isMaster = computed(() => props.run.masters.some((master) => master.id === auth.user?.id))

const seats = computed(() => runSeatsLabel(props.run))
const free = computed(() => {
  if (availability.value.key !== 'open' || props.run.availableSlots === null) return ''
  const n = props.run.availableSlots
  return `${plural(n, ['свободно', 'свободны', 'свободно'])} ${n} ${plural(n, ['место', 'места', 'мест'])}`
})

// Предпочтение роли спрашиваем, только если у игры заданы женские или мужские роли.
const asksRole = computed(() => {
  const game = props.run.game
  return Boolean(game && (game.femaleRolesMax || game.femaleRolesMin || game.maleRolesMax || game.maleRolesMin))
})
const asksTechnician = computed(() => Number(props.run.game?.technicians) > 0)

const formOpen = ref(false)
const form = reactive({ rolePreference: 'any', isTechnician: false, comment: '' })
const submitting = ref(false)
const cancelling = ref(false)
const failure = ref('')

// Вход, выход и запись меняют состояние блока — закрываем форму и убираем прежнюю ошибку.
watch(
  () => [props.run.id, mine.value?.id ?? null, auth.user?.id ?? null],
  () => {
    formOpen.value = false
    failure.value = ''
  },
)

/** Отказ связан с участием в конвенте — рядом показываем ссылку на проведение. */
const failureAboutEvent = ref(false)
/** Отклонённую или отменённую заявку можно только удалить (и подать заново). */
const removable = computed(() => ['rejected', 'cancelled'].includes(mine.value?.status))

const statusNote = computed(() => {
  switch (mine.value?.status) {
    case 'pending':
      return 'Мастер ещё не подтвердил заявку. Статус появится на этой странице.'
    case 'confirmed':
      return 'Мастер подтвердил ваше участие.'
    case 'waitlist':
      return 'Мест сейчас нет. Если место освободится, заявка перейдёт на рассмотрение мастеру.'
    case 'rejected':
    case 'cancelled':
      return 'Заявку можно удалить и подать заново.'
    default:
      return ''
  }
})
const rolePreferenceLabel = computed(
  () => ROLE_PREFERENCES.find((option) => option.value === mine.value?.rolePreference)?.label ?? '',
)

function openForm() {
  failure.value = ''
  requireAuth(
    () => {
      // После входа прогон перезагружается: могло оказаться, что заявка уже есть или это мастер.
      if (!mine.value && !isMaster.value) formOpen.value = true
    },
    { reason: 'Войдите, чтобы записаться на игру.' },
  )
}

async function submit() {
  if (submitting.value) return
  submitting.value = true
  failure.value = ''
  try {
    const { registration, run } = await runsApi.register(props.run.id, {
      rolePreference: asksRole.value ? form.rolePreference : 'any',
      isTechnician: asksTechnician.value && form.isTechnician,
      comment: form.comment.trim(),
    })
    emit('update', run)
    toast.success(
      registration.status === 'waitlist' ? 'Вы записаны в лист ожидания' : 'Заявка отправлена мастеру',
    )
    Object.assign(form, { rolePreference: 'any', isTechnician: false, comment: '' })
  } catch (err) {
    failure.value = err.detail || 'Не удалось записаться. Попробуйте ещё раз.'
    failureAboutEvent.value = Boolean(props.run.eventId) && err.code === 'event_registration_required'
  } finally {
    submitting.value = false
  }
}

async function cancel() {
  const rejected = removable.value
  const ok = await confirm({
    title: rejected ? 'Удалить заявку?' : 'Отменить запись?',
    message: rejected
      ? 'После удаления можно будет подать заявку заново.'
      : `Ваша заявка на «${props.run.game?.name ?? 'прогон'}» будет удалена. Записаться снова можно, пока запись открыта.`,
    confirmText: rejected ? 'Удалить' : 'Отменить запись',
    cancelText: 'Не отменять',
    danger: true,
  })
  if (!ok) return
  cancelling.value = true
  try {
    const { run } = await runsApi.unregister(props.run.id)
    emit('update', run)
    toast.success(rejected ? 'Заявка удалена' : 'Запись отменена')
  } catch (err) {
    toast.apiError(err, 'Не удалось отменить запись')
  } finally {
    cancelling.value = false
  }
}
</script>

<template>
  <section class="signup" aria-labelledby="run-signup-title">
    <div class="signup__head">
      <h2 id="run-signup-title">Запись</h2>
      <AppBadge :tone="availability.tone">{{ availability.label }}</AppBadge>
    </div>

    <p v-if="availability.key !== 'past' && seats" class="signup__seats">
      {{ seats }}<template v-if="free"> · {{ free }}</template>
    </p>

    <!-- Моя заявка -->
    <div v-if="mine" class="signup__mine">
      <RegistrationStatusBadge :status="mine.status" mine />
      <p v-if="statusNote && availability.key !== 'past'" class="text-muted">{{ statusNote }}</p>
      <dl v-if="(asksRole && rolePreferenceLabel) || mine.isTechnician || mine.comment" class="signup__details">
        <div v-if="asksRole && rolePreferenceLabel">
          <dt>Роль</dt>
          <dd>{{ rolePreferenceLabel }}</dd>
        </div>
        <div v-if="mine.isTechnician">
          <dt>Участие</dt>
          <dd>Игротехник</dd>
        </div>
        <div v-if="mine.comment">
          <dt>Комментарий</dt>
          <dd class="prose">{{ mine.comment }}</dd>
        </div>
      </dl>
      <AppButton v-if="availability.key !== 'past'" :loading="cancelling" block @click="cancel">
        {{ removable ? 'Удалить заявку' : 'Отменить запись' }}
      </AppButton>
    </div>

    <p v-else-if="availability.key === 'past'" class="text-muted">Прогон уже прошёл — запись недоступна.</p>

    <p v-else-if="isMaster" class="text-muted">
      Вы ведёте этот прогон, поэтому записаться игроком нельзя.
    </p>

    <p v-else-if="availability.key === 'closed'" class="text-muted">
      Мастер закрыл запись на этот прогон.
    </p>

    <template v-else>
      <p v-if="availability.key === 'full'" class="text-muted">
        Все места заняты. Можно записаться в лист ожидания — если место освободится, заявка перейдёт мастеру.
      </p>
      <p v-if="run.eventId && !formOpen" class="text-muted">
        Игра идёт в программе конвента — записаться могут участники с подтверждённой регистрацией на
        <RouterLink :to="{ name: 'event', params: { id: run.eventId } }">{{ run.conventionName || 'конвент' }}</RouterLink>.
      </p>

      <form v-if="formOpen" class="signup__form" novalidate @submit.prevent="submit">
        <div v-if="asksRole" class="signup__roles">
          <span class="signup__label" aria-hidden="true">Предпочтение роли</span>
          <SegmentedControl
            v-model="form.rolePreference"
            :options="ROLE_PREFERENCES"
            label="Предпочтение роли"
            size="sm"
          />
        </div>
        <AppCheckbox v-if="asksTechnician" v-model="form.isTechnician">Хочу быть игротехником</AppCheckbox>
        <FormField label="Комментарий для мастера" hint="Необязательно">
          <AppTextarea v-model="form.comment" rows="2" maxlength="1000" />
        </FormField>
        <div class="signup__buttons">
          <AppButton type="submit" variant="primary" :loading="submitting">
            {{ availability.key === 'full' ? 'В лист ожидания' : 'Отправить заявку' }}
          </AppButton>
          <AppButton variant="ghost" :disabled="submitting" @click="formOpen = false">Отмена</AppButton>
        </div>
      </form>
      <AppButton v-else variant="primary" block @click="openForm">
        {{ availability.key === 'full' ? 'Записаться в лист ожидания' : 'Записаться' }}
      </AppButton>

      <AppAlert v-if="failure" tone="danger">
        {{ failure }}
        <template v-if="failureAboutEvent">
          <br />
          <RouterLink :to="{ name: 'event', params: { id: run.eventId } }">
            Перейти к конвенту{{ run.conventionName ? ` «${run.conventionName}»` : '' }}
          </RouterLink>
        </template>
      </AppAlert>
    </template>
  </section>
</template>

<style scoped>
.signup {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
}
.signup__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
.signup__head h2 {
  font-size: var(--text-md);
}
.signup__seats {
  font-weight: 550;
  font-variant-numeric: tabular-nums;
}
.signup__mine {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-3);
}
.signup__details {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  width: 100%;
  font-size: var(--text-sm);
}
.signup__details div {
  display: flex;
  gap: var(--space-3);
}
.signup__details dt {
  flex: none;
  width: 6.5rem;
  color: var(--text-muted);
}
.signup__details dd {
  min-width: 0;
  overflow-wrap: anywhere;
}
.signup__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.signup__roles {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-1);
}
.signup__label {
  font-size: var(--text-sm);
  font-weight: 550;
}
.signup__buttons {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>
