<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Pencil, Trash2 } from '@lucide/vue'
import { eventsApi } from '@/api/events'
import { venuesApi } from '@/api/venues'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { usePageTitle } from '@/composables/usePageTitle'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { plural } from '@/utils/format'
import EventCard from '@/components/EventCard.vue'
import VenueRooms from '@/components/venue/VenueRooms.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: { type: String, required: true },
})

const router = useRouter()
const auth = useAuthStore()
const toast = useToast()
const confirm = useConfirm()
const back = { to: { name: 'venues' }, label: 'Все площадки' }

const { data: venue, error, reload } = useAsyncData((signal) => venuesApi.get(props.id, { signal }), {
  watch: () => props.id,
})

usePageTitle(() => venue.value?.name)

// Ближайшие проведения конвентов на площадке; блок скрыт, пока их нет (и при ошибке загрузки).
const { data: events } = useAsyncData(
  (signal) => eventsApi.list({ venue: props.id, time: 'upcoming', pageSize: 6 }, { signal }),
  { watch: () => props.id },
)

const facts = computed(() => {
  const item = venue.value
  if (!item) return []
  return [
    { key: 'city', label: 'Город', value: item.city?.name },
    { key: 'address', label: 'Адрес', value: item.address },
    {
      key: 'capacity',
      label: 'Вместимость',
      value: item.capacity ? `${item.capacity} ${plural(item.capacity, ['человек', 'человека', 'человек'])}` : '',
    },
  ].filter((fact) => fact.value)
})

const deleting = ref(false)

function setRooms(rooms) {
  venue.value = { ...venue.value, rooms }
}

async function removeVenue() {
  const ok = await confirm({
    title: 'Удалить площадку?',
    message: `«${venue.value.name}» и все её помещения будут удалены без возможности восстановления.`,
    confirmText: 'Удалить',
    danger: true,
  })
  if (!ok) return
  deleting.value = true
  try {
    await venuesApi.remove(venue.value.id)
    toast.success('Площадка удалена')
    router.push({ name: 'venues' })
  } catch (err) {
    toast.apiError(err, 'Не удалось удалить площадку')
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="container">
    <template v-if="error">
      <PageHeader :back="back" />
      <ErrorState :error="error" title="Не удалось загрузить площадку" not-found-title="Площадка не найдена" @retry="reload" />
    </template>

    <template v-else-if="!venue">
      <PageHeader :back="back">
        <template #title><AppSkeleton width="min(320px, 70vw)" height="1.2em" /></template>
      </PageHeader>
      <div class="venue" aria-busy="true" aria-label="Загрузка площадки">
        <div class="venue__main">
          <AppSkeleton v-for="n in 4" :key="n" height="1em" :width="n === 4 ? '60%' : '100%'" />
        </div>
        <AppSkeleton class="venue__aside" height="140px" radius="lg" />
      </div>
    </template>

    <template v-else>
      <PageHeader :title="venue.name" :back="back">
        <template v-if="auth.isAuthenticated" #actions>
          <AppButton :to="{ name: 'venue-edit', params: { id: venue.id } }">
            <Pencil :size="16" aria-hidden="true" />
            Изменить
          </AppButton>
          <AppButton v-if="auth.user?.isStaff" variant="ghost" :loading="deleting" @click="removeVenue">
            <Trash2 :size="16" aria-hidden="true" />
            Удалить
          </AppButton>
        </template>
      </PageHeader>

      <article class="venue">
        <div class="venue__main">
          <section v-if="venue.description" aria-labelledby="venue-description">
            <h2 id="venue-description">Описание</h2>
            <p class="prose">{{ venue.description }}</p>
          </section>

          <VenueRooms :venue-id="venue.id" :rooms="venue.rooms" @update:rooms="setRooms" />

          <section v-if="events?.items.length" aria-labelledby="venue-events">
            <h2 id="venue-events">Ближайшие проведения конвентов здесь</h2>
            <ul class="venue__events">
              <li v-for="event in events.items" :key="event.id"><EventCard :event="event" /></li>
            </ul>
          </section>
        </div>

        <aside v-if="facts.length" class="venue__aside">
          <h2 class="visually-hidden">Сведения о площадке</h2>
          <dl class="venue__facts">
            <div v-for="fact in facts" :key="fact.key">
              <dt>{{ fact.label }}</dt>
              <dd>{{ fact.value }}</dd>
            </div>
          </dl>
        </aside>
      </article>
    </template>
  </div>
</template>

<style scoped>
.venue {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--space-8) var(--space-10);
  align-items: start;
  padding-bottom: var(--space-10);
}
.venue__main {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  min-width: 0;
}
.venue__main h2 {
  margin-bottom: var(--space-2);
  font-size: var(--text-md);
}
.venue__events {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-3);
}
.venue__events > li {
  min-width: 0;
}
.venue__aside {
  min-width: 0;
}
.venue__facts {
  border-top: 1px solid var(--border);
}
.venue__facts div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  padding-block: var(--space-2);
  border-bottom: 1px solid var(--border);
}
.venue__facts dt {
  flex: none;
  color: var(--text-muted);
}
.venue__facts dd {
  min-width: 0;
  overflow-wrap: anywhere;
  font-weight: 550;
  text-align: right;
}

/* Телефон и планшет: одна колонка, сведения — над описанием и помещениями. */
@media (max-width: 859px) {
  .venue {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-6);
  }
  .venue__aside {
    order: -1;
  }
}
</style>
