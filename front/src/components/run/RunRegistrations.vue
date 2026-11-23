<script setup>
import { computed, ref } from 'vue'
import { Check, Clock, X } from '@lucide/vue'
import { runsApi } from '@/api/runs'
import { useToast } from '@/composables/useToast'
import { formatTimestamp } from '@/utils/datetime'
import { ROLE_PREFERENCES, registrationStatusMeta } from '@/utils/registration'
import RegistrationStatusBadge from '@/components/RegistrationStatusBadge.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'

/**
 * Заявки на прогон для мастера, организатора конвента и staff: счётчики по статусам и таблица
 * с изменением статуса (на телефоне строки превращаются в карточки).
 * Обновлённый прогон (ответ update_registration) отдаёт родителю событием `update`.
 */
const props = defineProps({
  /** Полный прогон из runsApi.get с массивом registrations. */
  run: { type: Object, required: true },
})
const emit = defineEmits(['update'])

const toast = useToast()

const STATUS_ORDER = ['pending', 'confirmed', 'waitlist', 'rejected', 'cancelled']
const ACTIONS = [
  { status: 'confirmed', label: 'Подтвердить', icon: Check, done: 'Заявка подтверждена' },
  { status: 'waitlist', label: 'В лист ожидания', icon: Clock, done: 'Заявка перенесена в лист ожидания' },
  { status: 'rejected', label: 'Отклонить', icon: X, done: 'Заявка отклонена' },
]

const rank = (status) => {
  const index = STATUS_ORDER.indexOf(status)
  return index === -1 ? STATUS_ORDER.length : index
}

const registrations = computed(() =>
  [...(props.run.registrations ?? [])].sort(
    (a, b) => rank(a.status) - rank(b.status) || String(a.createdAt).localeCompare(String(b.createdAt)),
  ),
)

const counters = computed(() =>
  STATUS_ORDER.map((status) => ({
    status,
    ...registrationStatusMeta(status),
    count: registrations.value.filter((item) => item.status === status).length,
  })).filter((item) => item.count),
)

const hasRoles = computed(() => {
  const game = props.run.game
  return Boolean(game && (game.femaleRolesMax || game.femaleRolesMin || game.maleRolesMax || game.maleRolesMin))
})
const showRole = computed(() => hasRoles.value || registrations.value.some((item) => item.rolePreference !== 'any'))
const showTechnician = computed(
  () => Number(props.run.game?.technicians) > 0 || registrations.value.some((item) => item.isTechnician),
)

const roleLabel = (value) => ROLE_PREFERENCES.find((option) => option.value === value)?.label ?? value
const actionsFor = (registration) => ACTIONS.filter((action) => action.status !== registration.status)

/** `${id}:${status}` заявки, статус которой сейчас меняется. */
const busy = ref('')

async function setStatus(registration, action) {
  if (busy.value) return
  busy.value = `${registration.id}:${action.status}`
  try {
    const { run } = await runsApi.updateRegistration(props.run.id, registration.id, action.status)
    emit('update', run)
    toast.success(`${action.done}: ${registration.user.displayName}`)
  } catch (err) {
    toast.apiError(err, 'Не удалось изменить статус заявки')
  } finally {
    busy.value = ''
  }
}
</script>

<template>
  <section class="regs" aria-labelledby="run-registrations-title">
    <div class="regs__head">
      <h2 id="run-registrations-title">Заявки</h2>
      <ul v-if="counters.length" class="regs__counters" aria-label="Заявки по статусам">
        <li v-for="item in counters" :key="item.status">
          <AppBadge :tone="item.tone">{{ item.label }}: {{ item.count }}</AppBadge>
        </li>
      </ul>
    </div>

    <p v-if="!registrations.length" class="text-muted">Заявок пока нет.</p>

    <div v-else class="regs__scroll">
      <table class="regs__table">
        <thead>
          <tr>
            <th scope="col">Игрок</th>
            <th v-if="showRole" scope="col">Роль</th>
            <th v-if="showTechnician" scope="col">Игротехник</th>
            <th scope="col">Комментарий</th>
            <th scope="col">Подана</th>
            <th scope="col">Статус</th>
            <th scope="col"><span class="visually-hidden">Действия</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="registration in registrations" :key="registration.id">
            <th scope="row" class="regs__name">{{ registration.user.displayName }}</th>
            <td v-if="showRole" data-label="Роль">{{ roleLabel(registration.rolePreference) }}</td>
            <td v-if="showTechnician" data-label="Игротехник" :class="{ 'regs__cell--empty': !registration.isTechnician }">
              {{ registration.isTechnician ? 'Да' : '—' }}
            </td>
            <td data-label="Комментарий" class="regs__comment" :class="{ 'regs__cell--empty': !registration.comment }">
              {{ registration.comment || '—' }}
            </td>
            <td data-label="Подана" class="regs__date">{{ formatTimestamp(registration.createdAt) }}</td>
            <td data-label="Статус" class="regs__status">
              <RegistrationStatusBadge :status="registration.status" />
            </td>
            <td class="regs__actions">
              <AppButton
                v-for="action in actionsFor(registration)"
                :key="action.status"
                size="sm"
                :variant="action.status === 'confirmed' ? 'secondary' : 'ghost'"
                :loading="busy === `${registration.id}:${action.status}`"
                :disabled="Boolean(busy)"
                :aria-label="`${action.label}: ${registration.user.displayName}`"
                @click="setStatus(registration, action)"
              >
                <component :is="action.icon" :size="14" aria-hidden="true" />
                {{ action.label }}
              </AppButton>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.regs {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-width: 0;
}
.regs__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2) var(--space-4);
}
.regs__head h2 {
  font-size: var(--text-md);
}
.regs__counters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.regs__scroll {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
}
.regs__table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}
.regs__table th,
.regs__table td {
  padding: var(--space-2) var(--space-3);
  text-align: left;
  vertical-align: top;
}
.regs__table thead th {
  border-bottom: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-muted);
  font-weight: 550;
  white-space: nowrap;
}
.regs__table tbody tr + tr > * {
  border-top: 1px solid var(--border);
}
.regs__name {
  font-weight: 600;
}
.regs__comment {
  min-width: 12rem;
  max-width: 28rem;
  white-space: pre-line;
  overflow-wrap: anywhere;
}
.regs__date,
.regs__status {
  white-space: nowrap;
}
.regs__date {
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.regs__cell--empty {
  color: var(--text-subtle);
}
.regs__actions {
  white-space: nowrap;
}
.regs__actions > * + * {
  margin-left: var(--space-1);
}

/* Телефон: каждая заявка — карточка, подписи столбцов — перед значениями. */
@media (max-width: 859px) {
  .regs__scroll {
    overflow: visible;
    border: 0;
    border-radius: 0;
    background: transparent;
  }
  .regs__table,
  .regs__table tbody {
    display: block;
  }
  .regs__table thead {
    display: none;
  }
  .regs__table tbody {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
  .regs__table tbody tr {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    padding: var(--space-3);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--surface);
  }
  .regs__table tbody tr > * {
    display: flex;
    gap: var(--space-3);
    padding: 0;
    border: 0;
  }
  .regs__table tbody tr + tr > * {
    border-top: 0;
  }
  .regs__table td[data-label]::before {
    content: attr(data-label);
    flex: none;
    width: 6.5rem;
    color: var(--text-muted);
  }
  .regs__name {
    font-size: var(--text-base);
  }
  .regs__comment {
    min-width: 0;
    max-width: none;
  }
  .regs__date,
  .regs__status {
    white-space: normal;
  }
  .regs__cell--empty {
    display: none !important;
  }
  .regs__actions {
    flex-wrap: wrap;
    gap: var(--space-2) !important;
    margin-top: var(--space-2);
    white-space: normal;
  }
  .regs__actions > * + * {
    margin-left: 0;
  }
}
</style>
