<script setup>
import { computed, ref } from 'vue'
import { CalendarCog, CalendarDays, Link, MapPin } from '@lucide/vue'
import { eventsApi } from '@/api/events'
import { usePageTitle } from '@/composables/usePageTitle'
import { useToast } from '@/composables/useToast'
import { formatDateRange } from '@/utils/datetime'
import LinkList from '@/components/LinkList.vue'
import PeopleEditor from '@/components/PeopleEditor.vue'
import EventRegistration from '@/components/event/EventRegistration.vue'
import EventRegistrations from '@/components/event/EventRegistrations.vue'
import { useEventSchedule } from '@/components/event/useEventSchedule'
import ScheduleView from '@/components/schedule/ScheduleView.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: { type: String, required: true },
})

const toast = useToast()
const { event, error, reload, myRuns, userId } = useEventSchedule(() => props.id)

const dates = computed(() => (event.value ? formatDateRange(event.value.dateStart, event.value.dateEnd) : ''))
usePageTitle(() => (event.value ? `${event.value.conventionName}, ${dates.value}` : ''))

const back = computed(() =>
  event.value?.conventionId
    ? { to: { name: 'convention', params: { id: event.value.conventionId } }, label: 'О конвенте' }
    : { to: { name: 'conventions' }, label: 'Все конвенты' },
)
// Площадки без своей площадки у проведения — те, в помещениях которых идут прогоны расписания.
const venues = computed(() => {
  if (event.value.venue) return [event.value.venue]
  const byId = new Map()
  for (const run of event.value.runs) {
    for (const room of run.rooms) {
      if (room.venueId && room.venueName) byId.set(room.venueId, { id: room.venueId, name: room.venueName, address: '' })
    }
  }
  return [...byId.values()]
})

// Длинное описание конвента свёрнуто: на конвенте важнее расписание.
const DESCRIPTION_LIMIT = 280
const expanded = ref(false)
const isLong = computed(() => event.value.description.length > DESCRIPTION_LIMIT)

async function copyLink() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    toast.success('Ссылка скопирована')
  } catch {
    toast.error('Не удалось скопировать ссылку. Скопируйте её из адресной строки.')
  }
}

// add_/remove_organizer возвращают проведение без расписания — берём из ответа только организаторов.
async function addOrganizer(user) {
  const updated = await eventsApi.addOrganizer(event.value.id, user.username)
  event.value = { ...event.value, organizers: updated.organizers }
}

async function removeOrganizer(person) {
  const updated = await eventsApi.removeOrganizer(event.value.id, person.id)
  event.value = { ...event.value, organizers: updated.organizers }
  // Убрав себя, организатор проведения может потерять права — сверяемся с сервером.
  if (person.id === userId.value) reload()
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
      <div aria-busy="true" aria-label="Загрузка проведения">
        <AppSkeleton height="1em" width="60%" class="event__line" />
        <AppSkeleton height="320px" radius="lg" />
      </div>
    </template>

    <template v-else>
      <PageHeader :back="back">
        <template #title>
          <RouterLink :to="{ name: 'convention', params: { id: event.conventionId } }" class="event__convention">
            {{ event.conventionName }}
          </RouterLink>
        </template>
        <template #actions>
          <AppButton @click="copyLink">
            <Link :size="16" aria-hidden="true" />
            Скопировать ссылку
          </AppButton>
          <AppButton v-if="event.canEdit" :to="{ name: 'event-edit', params: { id: event.id } }">
            <CalendarCog :size="16" aria-hidden="true" />
            Редактировать расписание
          </AppButton>
        </template>
        <ul class="event__facts">
          <li class="event__dates">
            <CalendarDays :size="16" aria-hidden="true" />
            <span>{{ dates }}</span>
          </li>
          <li v-if="event.cityName || venues.length">
            <MapPin :size="16" aria-hidden="true" />
            <span>
              {{ event.cityName }}<template v-if="event.cityName && venues.length"> · </template>
              <template v-for="(venue, index) in venues" :key="venue.id">
                <template v-if="index">, </template>
                <RouterLink :to="{ name: 'venue', params: { id: venue.id } }">{{ venue.name }}</RouterLink>
                <template v-if="venue.address"> · {{ venue.address }}</template>
              </template>
            </span>
          </li>
        </ul>
      </PageHeader>

      <div class="event">
        <div class="event__top">
          <div class="event__about">
            <section v-if="event.description" aria-labelledby="event-about">
              <h2 id="event-about" class="visually-hidden">О конвенте</h2>
              <p id="event-description" class="prose" :class="{ 'event__description--clamped': isLong && !expanded }">
                {{ event.description }}
              </p>
              <button
                v-if="isLong"
                type="button"
                class="event__more"
                :aria-expanded="expanded"
                aria-controls="event-description"
                @click="expanded = !expanded"
              >
                {{ expanded ? 'Свернуть' : 'Показать полностью' }}
              </button>
            </section>

            <LinkList :links="event.links" class="event__links" />

            <section v-if="event.organizers.length || event.canEdit" aria-labelledby="event-organizers">
              <h2 id="event-organizers" class="event__subtitle">
                {{ event.organizers.length === 1 ? 'Организатор' : 'Организаторы' }}
              </h2>
              <PeopleEditor
                :people="event.organizers"
                :editable="event.canEdit"
                :add="addOrganizer"
                :remove="removeOrganizer"
                add-label="Добавить организатора"
                remove-title="Убрать организатора проведения?"
                empty-text="У этого проведения нет своих организаторов — им управляют организаторы конвента."
              />
            </section>
          </div>

          <EventRegistration :event="event" class="event__registration" @changed="reload" />
        </div>

        <section aria-labelledby="event-schedule" class="event__schedule">
          <h2 id="event-schedule" class="event__title">Расписание</h2>
          <ScheduleView :event="event" :my-runs="myRuns" :user-id="userId">
            <template v-if="event.canEdit" #empty-actions>
              <AppButton variant="primary" :to="{ name: 'event-edit', params: { id: event.id } }">
                Составить расписание
              </AppButton>
            </template>
          </ScheduleView>
        </section>

        <EventRegistrations v-if="event.canEdit" :event-id="event.id" :capacity="event.capacity" @changed="reload" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.event {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
  min-width: 0;
}
.event__line {
  margin-bottom: var(--space-4);
}
.event__convention {
  color: var(--text);
  text-decoration: none;
}
.event__convention:hover {
  color: var(--accent-text);
}
.event__facts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-5);
  color: var(--text-muted);
}
.event__facts li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  min-width: 0;
}
.event__facts svg {
  flex: none;
  margin-top: 0.2em;
}
.event__dates {
  color: var(--accent-text);
  font-weight: 600;
}
.event__top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: var(--space-6) var(--space-10);
  align-items: start;
}
.event__about {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  min-width: 0;
}
.event__about:empty {
  display: none;
}
.event__description--clamped {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  line-clamp: 4;
}
.event__more {
  margin-top: var(--space-1);
  padding: 0;
  border: 0;
  background: none;
  color: var(--accent-text);
  font-size: var(--text-sm);
  font-weight: 550;
}
.event__more:hover {
  text-decoration: underline;
}
.event__subtitle {
  margin-bottom: var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: 600;
  letter-spacing: 0;
}
.event__title {
  margin-bottom: var(--space-3);
  font-size: var(--text-lg);
}
.event__schedule {
  min-width: 0;
}
@media (max-width: 859px) {
  .event__top {
    grid-template-columns: minmax(0, 1fr);
  }
  /* На телефоне участие и расписание важнее описания. */
  .event__registration {
    order: -1;
  }
}
</style>
