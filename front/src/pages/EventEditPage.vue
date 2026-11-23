<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Lock, Plus, Settings, Trash2, TriangleAlert } from '@lucide/vue'
import { eventsApi } from '@/api/events'
import { venuesApi } from '@/api/venues'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { usePageTitle } from '@/composables/usePageTitle'
import { useToast } from '@/composables/useToast'
import { formatDateRange } from '@/utils/datetime'
import { plural } from '@/utils/format'
import EventForm from '@/components/event/EventForm.vue'
import { useEventSchedule } from '@/components/event/useEventSchedule'
import CommonEventDialog from '@/components/schedule/CommonEventDialog.vue'
import RunFormDialog from '@/components/schedule/RunFormDialog.vue'
import ScheduleView from '@/components/schedule/ScheduleView.vue'
import { findConflicts } from '@/components/schedule/schedule'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

/**
 * Редактор расписания проведения (/events/:id/edit). Свойства проведения (город, площадка, даты,
 * лимит, регистрация) правятся диалогом EventForm; он же создаёт проведение со страницы конвента.
 */
const props = defineProps({
  id: { type: String, required: true },
})

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const { event, error, reload, myRuns, userId } = useEventSchedule(() => props.id)

const dates = computed(() => (event.value ? formatDateRange(event.value.dateStart, event.value.dateEnd) : ''))
usePageTitle(() => (event.value ? `${event.value.conventionName} — расписание` : ''))

const back = computed(() => ({ to: { name: 'event', params: { id: props.id } }, label: 'К проведению' }))
const subtitle = computed(() =>
  [event.value.conventionName, dates.value, event.value.cityName, event.value.venue?.name].filter(Boolean).join(' · '),
)

// Без площадки (или без помещений у неё) предлагаем все помещения, как в прежнем редакторе.
const needsAllRooms = computed(() => Boolean(event.value) && !event.value.venueRooms.length)
const { data: allRooms } = useAsyncData(
  (signal) => (needsAllRooms.value ? venuesApi.listRooms({}, { signal }) : Promise.resolve(null)),
  { watch: needsAllRooms, reloadOnAuthChange: false },
)
const rooms = computed(() => (event.value.venueRooms.length ? event.value.venueRooms : (allRooms.value ?? [])))

const conflictCount = computed(() => findConflicts(event.value.runs).size)

// Идёт удаление записи расписания: сетка приглушена, повторные действия не принимаются.
const removing = ref(false)

// --- Прогоны ---
const runOpen = ref(false)
const runTarget = ref(null)
const runPreset = ref(null)

function addRun(preset = null) {
  runTarget.value = null
  runPreset.value = preset
  runOpen.value = true
}

function editRun(run) {
  runTarget.value = run
  runPreset.value = null
  runOpen.value = true
}

async function removeRun(run) {
  const count = run.registeredCount
  const ok = await confirm({
    title: 'Удалить прогон из расписания?',
    message:
      `«${run.game?.name}» будет удалён вместе с заявками игроков.` +
      (count ? ` На него уже ${plural(count, ['записан', 'записаны', 'записано'])} ${count} ${plural(count, ['игрок', 'игрока', 'игроков'])}.` : ''),
    confirmText: 'Удалить',
    danger: true,
  })
  if (!ok || removing.value) return
  removing.value = true
  try {
    await eventsApi.removeRun(event.value.id, run.id)
    toast.success('Прогон удалён')
    runOpen.value = false
    await reload()
  } catch (err) {
    toast.apiError(err, 'Не удалось удалить прогон')
  } finally {
    removing.value = false
  }
}

// --- Общие события ---
const commonOpen = ref(false)
const commonTarget = ref(null)

function addCommon() {
  commonTarget.value = null
  commonOpen.value = true
}

function editCommon(item) {
  commonTarget.value = item
  commonOpen.value = true
}

async function removeCommon(item) {
  const ok = await confirm({
    title: 'Удалить событие из расписания?',
    message: `«${item.name}»`,
    confirmText: 'Удалить',
    danger: true,
  })
  if (!ok || removing.value) return
  removing.value = true
  try {
    await eventsApi.removeCommonEvent(event.value.id, item.id)
    toast.success('Событие удалено')
    commonOpen.value = false
    await reload()
  } catch (err) {
    toast.apiError(err, 'Не удалось удалить событие')
  } finally {
    removing.value = false
  }
}

// --- Свойства и удаление проведения ---
const propsOpen = ref(false)
const deleting = ref(false)

async function removeEvent() {
  const runs = event.value.runs.length
  const ok = await confirm({
    title: 'Удалить проведение?',
    message:
      `${event.value.conventionName}, ${dates.value}. Будут удалены расписание` +
      (runs ? ` (${runs} ${plural(runs, ['прогон', 'прогона', 'прогонов'])})` : '') +
      ' и все заявки участников. Восстановить не получится.',
    confirmText: 'Удалить',
    danger: true,
  })
  if (!ok) return
  deleting.value = true
  try {
    await eventsApi.remove(event.value.id)
    toast.success('Проведение удалено')
    router.push({ name: 'convention', params: { id: event.value.conventionId } })
  } catch (err) {
    toast.apiError(err, 'Не удалось удалить проведение')
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="container">
    <template v-if="error">
      <PageHeader :back="back" />
      <ErrorState :error="error" title="Не удалось загрузить проведение" not-found-title="Проведение не найдено" @retry="reload" />
    </template>

    <template v-else-if="!event">
      <PageHeader :back="back">
        <template #title><AppSkeleton width="min(320px, 70vw)" height="1.2em" /></template>
      </PageHeader>
      <AppSkeleton height="320px" radius="lg" aria-busy="true" aria-label="Загрузка расписания" />
    </template>

    <template v-else-if="!event.canEdit">
      <PageHeader :back="back" />
      <EmptyState
        :icon="Lock"
        title="Нет прав на редактирование"
        description="Изменять расписание могут организаторы проведения, организаторы конвента и администраторы."
      >
        <AppButton :to="back.to">Вернуться к проведению</AppButton>
      </EmptyState>
    </template>

    <template v-else>
      <PageHeader title="Редактор расписания" :back="back">
        <template #actions>
          <AppButton @click="propsOpen = true">
            <Settings :size="16" aria-hidden="true" />
            Свойства проведения
          </AppButton>
          <AppButton variant="ghost" :loading="deleting" @click="removeEvent">
            <Trash2 :size="16" aria-hidden="true" />
            Удалить проведение
          </AppButton>
        </template>
        <p class="editor__subtitle">{{ subtitle }}</p>
      </PageHeader>

      <div class="editor">
        <div class="editor__actions">
          <AppButton variant="primary" @click="addRun()">
            <Plus :size="16" aria-hidden="true" />
            Добавить прогон
          </AppButton>
          <AppButton @click="addCommon">
            <Plus :size="16" aria-hidden="true" />
            Общее событие
          </AppButton>
        </div>

        <AppAlert v-if="!event.venue" tone="info">
          У проведения не указана площадка, поэтому в прогонах предлагаются помещения всех площадок. Укажите площадку в
          свойствах проведения — столбцами сетки станут её помещения.
        </AppAlert>
        <AppAlert v-else-if="!event.venueRooms.length" tone="info">
          У площадки «{{ event.venue.name }}» нет помещений. Добавьте их на
          <RouterLink :to="{ name: 'venue', params: { id: event.venue.id } }">странице площадки</RouterLink>, чтобы
          разнести прогоны по столбцам.
        </AppAlert>

        <p v-if="conflictCount" class="editor__conflicts" role="status">
          <TriangleAlert :size="16" aria-hidden="true" />
          Пересечений по помещениям: {{ conflictCount }}
          {{ plural(conflictCount, ['прогон', 'прогона', 'прогонов']) }} — отмечены в расписании.
        </p>

        <p class="editor__hint">
          Прогон или событие открывается нажатием. В сетке нажатие на свободное место добавляет прогон в это помещение
          и время.
        </p>

        <ScheduleView
          class="editor__schedule"
          :class="{ 'is-busy': removing }"
          :aria-busy="removing"
          :event="event"
          :my-runs="myRuns"
          :user-id="userId"
          editable
          @add-run="addRun"
          @edit-run="editRun"
          @remove-run="removeRun"
          @edit-common="editCommon"
          @remove-common="removeCommon"
        />
      </div>

      <RunFormDialog
        v-model:open="runOpen"
        :event="event"
        :run="runTarget"
        :preset="runPreset"
        :rooms="rooms"
        @saved="reload"
        @remove="removeRun"
      />
      <CommonEventDialog
        v-model:open="commonOpen"
        :event="event"
        :item="commonTarget"
        @saved="reload"
        @remove="removeCommon"
      />
      <EventForm v-model:open="propsOpen" :event="event" @saved="reload" />
    </template>
  </div>
</template>

<style scoped>
.editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}
.editor__subtitle {
  color: var(--text-muted);
}
.editor__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.editor__hint {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.editor__schedule {
  transition: opacity var(--duration);
}
.editor__schedule.is-busy {
  opacity: 0.55;
  pointer-events: none;
}
.editor__conflicts {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--danger-text);
  font-size: var(--text-sm);
  font-weight: 550;
}
</style>
