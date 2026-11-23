<script setup>
import { computed, reactive, ref } from 'vue'
import { Check, MessageSquare, RotateCcw, X } from '@lucide/vue'
import { eventsApi } from '@/api/events'
import { useAsyncData } from '@/composables/useAsyncData'
import { useToast } from '@/composables/useToast'
import { formatTimestamp } from '@/utils/datetime'
import RegistrationStatusBadge from '@/components/RegistrationStatusBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import AppTextarea from '@/components/ui/AppTextarea.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import FormField from '@/components/ui/FormField.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'

/**
 * Заявки на проведение для организаторов: таблица, подтверждение / отклонение, комментарий
 * организатора. После изменения статуса — событие `changed` (счётчики мест у проведения).
 */
const props = defineProps({
  eventId: { type: Number, required: true },
  /** Лимит участников проведения или null. */
  capacity: { type: Number, default: null },
})
const emit = defineEmits(['changed'])

const toast = useToast()
const { data, error, reload } = useAsyncData((signal) => eventsApi.registrations(props.eventId, { signal }), {
  watch: () => props.eventId,
})

const ORDER = { pending: 0, confirmed: 1, rejected: 2, cancelled: 3 }
const filter = ref('all')
const busy = reactive(new Set())

const counts = computed(() => {
  const result = { all: 0, pending: 0, confirmed: 0, rejected: 0, cancelled: 0 }
  for (const item of data.value ?? []) {
    result.all += 1
    if (item.status in result) result[item.status] += 1
  }
  return result
})
const filters = computed(() => [
  { value: 'all', label: `Все ${counts.value.all}` },
  { value: 'pending', label: `Ожидают ${counts.value.pending}` },
  { value: 'confirmed', label: `Подтверждены ${counts.value.confirmed}` },
  { value: 'rejected', label: `Отклонены ${counts.value.rejected + counts.value.cancelled}` },
])
const rows = computed(() =>
  (data.value ?? [])
    .filter((item) => {
      if (filter.value === 'all') return true
      if (filter.value === 'rejected') return item.status === 'rejected' || item.status === 'cancelled'
      return item.status === filter.value
    })
    .sort((a, b) => (ORDER[a.status] ?? 9) - (ORDER[b.status] ?? 9) || String(a.createdAt).localeCompare(String(b.createdAt))),
)
const summary = computed(() => {
  const confirmed = counts.value.confirmed
  return props.capacity ? `Подтверждено ${confirmed} из ${props.capacity}` : `Подтверждено ${confirmed}`
})

function replace(updated) {
  data.value = data.value.map((item) => (item.id === updated.id ? updated : item))
}

async function setStatus(registration, status) {
  if (busy.has(registration.id)) return
  busy.add(registration.id)
  try {
    replace(await eventsApi.updateRegistration(props.eventId, registration.id, { status }))
    emit('changed')
  } catch (err) {
    toast.apiError(err, 'Не удалось изменить статус заявки')
  } finally {
    busy.delete(registration.id)
  }
}

// Комментарий организатора.
const commenting = ref(null)
const commentText = ref('')
const commentSaving = ref(false)
const commentOpen = computed({
  get: () => commenting.value !== null,
  set: (value) => {
    if (!value) commenting.value = null
  },
})

function openComment(registration) {
  commentText.value = registration.adminComment
  commenting.value = registration
}

async function saveComment() {
  if (commentSaving.value) return
  commentSaving.value = true
  try {
    replace(
      await eventsApi.updateRegistration(props.eventId, commenting.value.id, { adminComment: commentText.value.trim() }),
    )
    toast.success('Комментарий сохранён')
    commenting.value = null
  } catch (err) {
    toast.apiError(err, 'Не удалось сохранить комментарий')
  } finally {
    commentSaving.value = false
  }
}
</script>

<template>
  <section class="eregs" aria-labelledby="eregs-title">
    <div class="eregs__head">
      <h2 id="eregs-title">Заявки на участие</h2>
      <span v-if="data" class="eregs__summary">{{ summary }}</span>
    </div>

    <ErrorState v-if="error" :error="error" title="Не удалось загрузить заявки" @retry="reload" />
    <AppSkeleton v-else-if="!data" height="6rem" radius="lg" />
    <p v-else-if="!data.length" class="eregs__empty">Заявок пока нет.</p>

    <template v-else>
      <SegmentedControl v-model="filter" :options="filters" label="Статус заявок" size="sm" class="eregs__filter" />

      <p v-if="!rows.length" class="eregs__empty">Заявок с таким статусом нет.</p>
      <div v-else class="eregs__scroll" role="region" aria-label="Таблица заявок" tabindex="0">
        <table class="eregs__table">
          <thead>
            <tr>
              <th scope="col">Участник</th>
              <th scope="col">Комментарий</th>
              <th scope="col">Подана</th>
              <th scope="col">Статус</th>
              <th scope="col"><span class="visually-hidden">Действия</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in rows" :key="item.id">
              <th scope="row" class="eregs__user">
                {{ item.user.displayName }}
                <span v-if="item.user.username && item.user.username !== item.user.displayName" class="eregs__username">
                  {{ item.user.username }}
                </span>
              </th>
              <td class="eregs__comment">
                <p v-if="item.comment" class="prose">{{ item.comment }}</p>
                <p v-if="item.adminComment" class="eregs__admin prose">
                  <span class="eregs__admin-label">Организатор:</span> {{ item.adminComment }}
                </p>
              </td>
              <td class="eregs__date">{{ formatTimestamp(item.createdAt) }}</td>
              <td><RegistrationStatusBadge :status="item.status" /></td>
              <td>
                <div class="eregs__actions">
                  <AppButton
                    v-if="item.status !== 'confirmed'"
                    size="sm"
                    :loading="busy.has(item.id)"
                    :aria-label="`Подтвердить заявку: ${item.user.displayName}`"
                    @click="setStatus(item, 'confirmed')"
                  >
                    <Check :size="14" aria-hidden="true" />
                    Подтвердить
                  </AppButton>
                  <AppButton
                    v-if="item.status === 'pending' || item.status === 'confirmed'"
                    size="sm"
                    variant="ghost"
                    :disabled="busy.has(item.id)"
                    :aria-label="`Отклонить заявку: ${item.user.displayName}`"
                    @click="setStatus(item, 'rejected')"
                  >
                    <X :size="14" aria-hidden="true" />
                    Отклонить
                  </AppButton>
                  <AppButton
                    v-if="item.status === 'rejected' || item.status === 'cancelled'"
                    size="sm"
                    variant="ghost"
                    :disabled="busy.has(item.id)"
                    :aria-label="`Вернуть на рассмотрение: ${item.user.displayName}`"
                    @click="setStatus(item, 'pending')"
                  >
                    <RotateCcw :size="14" aria-hidden="true" />
                    Вернуть
                  </AppButton>
                  <AppButton
                    size="sm"
                    variant="ghost"
                    icon-only
                    :aria-label="`Комментарий организатора: ${item.user.displayName}`"
                    title="Комментарий организатора"
                    @click="openComment(item)"
                  >
                    <MessageSquare :size="14" aria-hidden="true" />
                  </AppButton>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <AppDialog v-model:open="commentOpen" title="Комментарий организатора" :dismissible="!commentSaving">
      <form id="ereg-comment-form" novalidate @submit.prevent="saveComment">
        <FormField
          :label="`Для участника: ${commenting?.user.displayName ?? ''}`"
          hint="Участник увидит комментарий рядом со своей заявкой"
        >
          <AppTextarea v-model="commentText" rows="3" autofocus />
        </FormField>
      </form>
      <template #footer>
        <AppButton :disabled="commentSaving" @click="commentOpen = false">Отмена</AppButton>
        <AppButton variant="primary" type="submit" form="ereg-comment-form" :loading="commentSaving">Сохранить</AppButton>
      </template>
    </AppDialog>
  </section>
</template>

<style scoped>
.eregs {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-width: 0;
}
.eregs__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-1) var(--space-3);
}
.eregs__head h2 {
  font-size: var(--text-lg);
}
.eregs__summary {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.eregs__filter {
  align-self: flex-start;
  max-width: 100%;
  overflow-x: auto;
}
.eregs__empty {
  color: var(--text-muted);
}
.eregs__scroll {
  /* Опора для абсолютно позиционированных потомков (.visually-hidden), иначе они растягивают страницу. */
  position: relative;
  max-width: 100%;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  overflow-x: auto;
}
.eregs__table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
  font-size: var(--text-sm);
}
.eregs__table th,
.eregs__table td {
  padding: var(--space-2) var(--space-3);
  text-align: left;
  vertical-align: top;
}
.eregs__table thead th {
  background: var(--surface-2);
  color: var(--text-muted);
  font-weight: 550;
  white-space: nowrap;
}
.eregs__table tbody tr {
  border-top: 1px solid var(--border);
}
.eregs__user {
  font-weight: 550;
}
.eregs__username {
  display: block;
  color: var(--text-subtle);
  font-weight: 400;
}
.eregs__comment {
  min-width: 12rem;
  max-width: 24rem;
}
.eregs__admin {
  color: var(--text-muted);
}
.eregs__admin-label {
  font-weight: 550;
}
.eregs__date {
  color: var(--text-muted);
  white-space: nowrap;
}
.eregs__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-1);
}
</style>
