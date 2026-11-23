<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Link, Pencil, Plus, Trash2 } from '@lucide/vue'
import { conventionsApi } from '@/api/conventions'
import { eventsApi } from '@/api/events'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { usePageTitle } from '@/composables/usePageTitle'
import { useToast } from '@/composables/useToast'
import { isDatePast } from '@/utils/datetime'
import { plural } from '@/utils/format'
import EventCard from '@/components/EventCard.vue'
import LinkList from '@/components/LinkList.vue'
import PeopleEditor from '@/components/PeopleEditor.vue'
import EventForm from '@/components/event/EventForm.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: { type: String, required: true },
})

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const back = { to: { name: 'conventions' }, label: 'Все конвенты' }

const { data: convention, error, reload } = useAsyncData((signal) => conventionsApi.get(props.id, { signal }), {
  watch: () => props.id,
})
const {
  data: events,
  error: eventsError,
  reload: reloadEvents,
} = useAsyncData((signal) => eventsApi.list({ convention: props.id, time: 'all', pageSize: 100 }, { signal }), {
  watch: () => props.id,
})

usePageTitle(() => convention.value?.name)

const isOver = (event) => isDatePast(event.dateEnd, { timeZone: event.city?.timezone })
// Предстоящие — ближайшие первыми; прошедшие — недавние первыми.
const upcoming = computed(() =>
  (events.value?.items ?? []).filter((event) => !isOver(event)).sort((a, b) => a.dateStart.localeCompare(b.dateStart)),
)
const past = computed(() =>
  (events.value?.items ?? []).filter(isOver).sort((a, b) => b.dateStart.localeCompare(a.dateStart)),
)
const hiddenCount = computed(() => (events.value ? events.value.count - events.value.items.length : 0))

const deleting = ref(false)
const eventFormOpen = ref(false)

async function copyLink() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    toast.success('Ссылка скопирована')
  } catch {
    toast.error('Не удалось скопировать ссылку. Скопируйте её из адресной строки.')
  }
}

async function addOrganizer(user) {
  convention.value = await conventionsApi.addOrganizer(convention.value.id, user.username)
}

async function removeOrganizer(person) {
  convention.value = await conventionsApi.removeOrganizer(convention.value.id, person.id)
}

async function removeConvention() {
  const count = events.value?.count ?? convention.value.eventsCount
  const ok = await confirm({
    title: 'Удалить конвент?',
    message: count
      ? `«${convention.value.name}» будет удалён вместе с ${count} ${plural(count, ['проведением', 'проведениями', 'проведениями'])}, их расписаниями и заявками участников. Восстановить не получится.`
      : `«${convention.value.name}» будет удалён без возможности восстановления.`,
    confirmText: 'Удалить',
    danger: true,
  })
  if (!ok) return
  deleting.value = true
  try {
    await conventionsApi.remove(convention.value.id)
    toast.success('Конвент удалён')
    router.push({ name: 'conventions' })
  } catch (err) {
    toast.apiError(err, 'Не удалось удалить конвент')
  } finally {
    deleting.value = false
  }
}

function onEventCreated(event) {
  // Новое проведение сразу открываем в редакторе расписания.
  router.push({ name: 'event-edit', params: { id: event.id } })
}
</script>

<template>
  <div class="container">
    <template v-if="error">
      <PageHeader :back="back" />
      <ErrorState :error="error" title="Не удалось загрузить конвент" not-found-title="Конвент не найден" @retry="reload" />
    </template>

    <template v-else-if="!convention">
      <PageHeader :back="back">
        <template #title><AppSkeleton width="min(320px, 70vw)" height="1.2em" /></template>
      </PageHeader>
      <div aria-busy="true" aria-label="Загрузка конвента">
        <AppSkeleton v-for="n in 4" :key="n" height="1em" :width="n === 4 ? '60%' : '100%'" class="convention__line" />
      </div>
    </template>

    <template v-else>
      <PageHeader :title="convention.name" :back="back">
        <template #actions>
          <AppButton @click="copyLink">
            <Link :size="16" aria-hidden="true" />
            Скопировать ссылку
          </AppButton>
          <template v-if="convention.canEdit">
            <AppButton :to="{ name: 'convention-edit', params: { id: convention.id } }">
              <Pencil :size="16" aria-hidden="true" />
              Изменить
            </AppButton>
            <AppButton variant="ghost" :loading="deleting" @click="removeConvention">
              <Trash2 :size="16" aria-hidden="true" />
              Удалить
            </AppButton>
          </template>
        </template>
      </PageHeader>

      <div class="convention">
        <div class="convention__main">
          <section v-if="convention.description" aria-labelledby="convention-about">
            <h2 id="convention-about" class="visually-hidden">Описание</h2>
            <p class="prose">{{ convention.description }}</p>
          </section>

          <section aria-labelledby="convention-events">
            <div class="convention__section-head">
              <h2 id="convention-events">Проведения</h2>
              <AppButton v-if="convention.canEdit" size="sm" @click="eventFormOpen = true">
                <Plus :size="16" aria-hidden="true" />
                Добавить проведение
              </AppButton>
            </div>

            <ErrorState v-if="eventsError" :error="eventsError" title="Не удалось загрузить проведения" @retry="reloadEvents" />
            <div v-else-if="!events" class="convention__events" aria-busy="true" aria-label="Загрузка проведений">
              <AppSkeleton v-for="n in 2" :key="n" height="116px" radius="lg" />
            </div>
            <p v-else-if="!events.items.length" class="text-muted">
              {{
                convention.canEdit
                  ? 'Проведений пока нет. Добавьте первое — с городом и датами, затем составьте расписание.'
                  : 'Проведений пока нет.'
              }}
            </p>
            <template v-else>
              <template v-if="upcoming.length">
                <h3 class="convention__group">Предстоящие</h3>
                <ul class="convention__events">
                  <li v-for="event in upcoming" :key="event.id"><EventCard :event="event" :show-name="false" /></li>
                </ul>
              </template>
              <template v-if="past.length">
                <h3 class="convention__group">Прошедшие</h3>
                <ul class="convention__events">
                  <li v-for="event in past" :key="event.id"><EventCard :event="event" :show-name="false" /></li>
                </ul>
              </template>
              <p v-if="hiddenCount > 0" class="text-muted convention__more">
                Показаны последние {{ events.items.length }} проведений из {{ events.count }}.
              </p>
            </template>
          </section>
        </div>

        <aside
          v-if="convention.links.length || convention.organizers.length || convention.canEdit"
          class="convention__aside"
        >
          <section v-if="convention.links.length" aria-labelledby="convention-links">
            <h2 id="convention-links" class="convention__aside-title">Ссылки</h2>
            <LinkList :links="convention.links" />
          </section>

          <section v-if="convention.organizers.length || convention.canEdit" aria-labelledby="convention-organizers">
            <h2 id="convention-organizers" class="convention__aside-title">
              {{ convention.organizers.length === 1 ? 'Организатор' : 'Организаторы' }}
            </h2>
            <PeopleEditor
              :people="convention.organizers"
              :editable="convention.canEdit"
              :min="1"
              :add="addOrganizer"
              :remove="removeOrganizer"
              add-label="Добавить организатора"
              remove-title="Убрать организатора?"
              empty-text="Организаторы не указаны"
            />
          </section>
        </aside>
      </div>

      <EventForm
        v-model:open="eventFormOpen"
        :convention-id="convention.id"
        :convention-name="convention.name"
        @saved="onEventCreated"
      />
    </template>
  </div>
</template>

<style scoped>
.convention {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: var(--space-8) var(--space-10);
  align-items: start;
}
.convention:not(:has(.convention__aside)) {
  grid-template-columns: minmax(0, 1fr);
}
.convention__main {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  min-width: 0;
}
.convention__line {
  margin-bottom: var(--space-1);
}
.convention__section-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-3);
  margin-bottom: var(--space-3);
}
.convention__section-head h2 {
  font-size: var(--text-lg);
}
.convention__group {
  margin-block: var(--space-4) var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: 600;
}
.convention__group:first-of-type {
  margin-top: 0;
}
.convention__events {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-3);
}
.convention__events > li {
  min-width: 0;
}
.convention__more {
  margin-top: var(--space-3);
}
.convention__aside {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  min-width: 0;
}
.convention__aside-title {
  margin-bottom: var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: 600;
  letter-spacing: 0;
}
@media (max-width: 859px) {
  .convention {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-6);
  }
}
</style>
