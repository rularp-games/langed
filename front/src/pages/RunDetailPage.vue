<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { CalendarDays, Link, MapPin, Pencil, Ticket, Trash2 } from '@lucide/vue'
import { runsApi } from '@/api/runs'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { usePageTitle } from '@/composables/usePageTitle'
import { useToast } from '@/composables/useToast'
import { formatDate, formatDateTime, formatDuration, formatTimeRange } from '@/utils/datetime'
import { gameFacts } from '@/utils/game'
import PeopleEditor from '@/components/PeopleEditor.vue'
import PosterImage from '@/components/PosterImage.vue'
import RunRegistration from '@/components/run/RunRegistration.vue'
import RunRegistrations from '@/components/run/RunRegistrations.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

/** Анонс длиннее этого числа символов показывается свёрнутым. */
const ANNOUNCEMENT_LIMIT = 600

const props = defineProps({
  id: { type: String, required: true },
})

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()

const { data: run, error, reload } = useAsyncData((signal) => runsApi.get(props.id, { signal }), {
  watch: () => props.id,
})

// Прогон конвента открывают из расписания — туда и ведёт ссылка «назад».
const back = computed(() =>
  run.value?.eventId
    ? { to: { name: 'event', params: { id: run.value.eventId } }, label: run.value.conventionName || 'Конвент' }
    : { to: { name: 'afisha' }, label: 'Афиша' },
)

const when = computed(() => formatDateTime(run.value.dateLocal, { relative: true, timeZone: run.value.cityTimezone }))
const title = computed(() => (run.value?.game ? `${run.value.game.name} — ${formatDateTime(run.value.dateLocal)}` : ''))
usePageTitle(title)

const dateLine = computed(() => formatDate(run.value.dateLocal, { weekday: true }))
const timeLine = computed(() => {
  const range = formatTimeRange(run.value.dateLocal, run.value.duration)
  const duration = formatDuration(run.value.duration)
  return duration ? `${range} · ${duration}` : range
})

// Площадки прогона — по его помещениям (обычно одна): [{id, name}].
const venues = computed(() => {
  const byId = new Map()
  for (const room of run.value.rooms) {
    if (room.venueId && room.venueName) byId.set(room.venueId, { id: room.venueId, name: room.venueName })
  }
  return [...byId.values()]
})
const roomNames = computed(() => run.value.rooms.map((room) => room.name).join(', '))

const facts = computed(() => (run.value?.game ? gameFacts(run.value.game) : []))
const announcement = computed(() => run.value?.game?.announcement ?? '')
const isLong = computed(() => announcement.value.length > ANNOUNCEMENT_LIMIT)
const expanded = ref(false)
watch(
  () => props.id,
  () => (expanded.value = false),
)
const announcementText = computed(() => {
  if (!isLong.value || expanded.value) return announcement.value
  const cut = announcement.value.slice(0, ANNOUNCEMENT_LIMIT)
  // Обрезаем по границе слова, чтобы текст не обрывался посередине.
  return `${cut.slice(0, Math.max(cut.lastIndexOf(' '), ANNOUNCEMENT_LIMIT - 80)).trimEnd()}…`
})

const deleting = ref(false)

/** Ответы действий (запись, заявки, мастера) содержат обновлённый прогон целиком. */
function applyRun(updated) {
  run.value = updated
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    toast.success('Ссылка скопирована')
  } catch {
    toast.error('Не удалось скопировать ссылку. Скопируйте её из адресной строки.')
  }
}

async function addMaster(user) {
  run.value = await runsApi.addMaster(run.value.id, user.username)
}

async function removeMaster(person) {
  run.value = await runsApi.removeMaster(run.value.id, person.id)
}

async function removeRun() {
  const ok = await confirm({
    title: 'Удалить прогон?',
    message: `Прогон «${run.value.game?.name ?? ''}» (${formatDateTime(run.value.dateLocal)}) будет удалён вместе с заявками игроков. Восстановить его не получится.`,
    confirmText: 'Удалить',
    danger: true,
  })
  if (!ok) return
  deleting.value = true
  try {
    const target = back.value.to
    await runsApi.remove(run.value.id)
    toast.success('Прогон удалён')
    router.push(target)
  } catch (err) {
    toast.apiError(err, 'Не удалось удалить прогон')
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="container">
    <template v-if="error">
      <PageHeader :back="{ to: { name: 'afisha' }, label: 'Афиша' }" />
      <ErrorState :error="error" title="Не удалось загрузить прогон" not-found-title="Прогон не найден" @retry="reload" />
    </template>

    <template v-else-if="!run">
      <PageHeader :back="{ to: { name: 'afisha' }, label: 'Афиша' }">
        <template #title><AppSkeleton width="min(320px, 70vw)" height="1.2em" /></template>
      </PageHeader>
      <div class="run" aria-busy="true" aria-label="Загрузка прогона">
        <div class="run__main">
          <AppSkeleton v-for="n in 5" :key="n" height="1em" :width="n === 5 ? '60%' : '100%'" />
        </div>
        <AppSkeleton class="run__aside" height="220px" radius="lg" />
      </div>
    </template>

    <template v-else>
      <PageHeader :title="run.game?.name ?? 'Прогон'" :back="back">
        <template #meta>{{ when }}</template>
        <template #actions>
          <AppButton @click="copyLink">
            <Link :size="16" aria-hidden="true" />
            Скопировать ссылку
          </AppButton>
          <template v-if="run.canEdit">
            <AppButton :to="{ name: 'run-edit', params: { id: run.id } }">
              <Pencil :size="16" aria-hidden="true" />
              Изменить
            </AppButton>
            <AppButton variant="ghost" :loading="deleting" @click="removeRun">
              <Trash2 :size="16" aria-hidden="true" />
              Удалить
            </AppButton>
          </template>
        </template>
      </PageHeader>

      <article class="run">
        <div class="run__main">
          <section aria-labelledby="run-when-where">
            <h2 id="run-when-where" class="visually-hidden">Когда и где</h2>
            <dl class="run__summary">
              <div>
                <dt>
                  <CalendarDays :size="16" aria-hidden="true" />
                  Когда
                </dt>
                <dd>
                  <p class="run__strong">{{ dateLine }}</p>
                  <p>{{ timeLine }}</p>
                  <p v-if="run.cityName" class="run__note">По времени города {{ run.cityName }}</p>
                </dd>
              </div>
              <div v-if="run.cityName || venues.length || roomNames">
                <dt>
                  <MapPin :size="16" aria-hidden="true" />
                  Где
                </dt>
                <dd>
                  <p v-if="run.cityName" class="run__strong">{{ run.cityName }}</p>
                  <p v-if="venues.length">
                    <template v-for="(venue, index) in venues" :key="venue.id">
                      <template v-if="index">, </template>
                      <RouterLink :to="{ name: 'venue', params: { id: venue.id } }">{{ venue.name }}</RouterLink>
                    </template>
                  </p>
                  <p v-if="roomNames">{{ roomNames }}</p>
                </dd>
              </div>
              <div v-if="run.eventId">
                <dt>
                  <Ticket :size="16" aria-hidden="true" />
                  Конвент
                </dt>
                <dd>
                  <RouterLink :to="{ name: 'event', params: { id: run.eventId } }" class="run__strong">
                    {{ run.conventionName || 'Открыть расписание' }}
                  </RouterLink>
                </dd>
              </div>
            </dl>
          </section>

          <section v-if="run.game" aria-labelledby="run-game">
            <h2 id="run-game">Об игре</h2>
            <p class="run__game-link">
              <RouterLink :to="{ name: 'game', params: { id: run.game.id } }">{{ run.game.name }}</RouterLink>
              <span v-if="facts.length" class="run__facts">
                <template v-for="(fact, index) in facts" :key="fact.key">
                  <template v-if="index"> · </template>{{ fact.label.toLowerCase() }}: {{ fact.value }}
                </template>
              </span>
            </p>
            <template v-if="announcement">
              <p :id="`run-announcement-${run.id}`" class="prose">{{ announcementText }}</p>
              <button
                v-if="isLong"
                type="button"
                class="run__more"
                :aria-expanded="expanded"
                :aria-controls="`run-announcement-${run.id}`"
                @click="expanded = !expanded"
              >
                {{ expanded ? 'Свернуть' : 'Читать полностью' }}
              </button>
            </template>
            <p v-else class="text-muted">Анонс игры пока не добавлен.</p>
          </section>

          <section v-if="run.game?.redFlags" class="run__flags" aria-labelledby="run-red-flags">
            <h2 id="run-red-flags">Красные флаги</h2>
            <p class="prose">{{ run.game.redFlags }}</p>
          </section>
        </div>

        <aside class="run__aside">
          <RunRegistration :run="run" @update="applyRun" />

          <section v-if="run.masters.length || run.canEdit" aria-labelledby="run-masters">
            <h2 id="run-masters" class="run__aside-title">
              {{ run.masters.length === 1 ? 'Мастер' : 'Мастера' }}
            </h2>
            <PeopleEditor
              :people="run.masters"
              :editable="run.canEdit"
              :min="1"
              :add="addMaster"
              :remove="removeMaster"
              add-label="Добавить мастера"
              remove-title="Убрать мастера?"
              empty-text="Мастера не указаны"
            />
          </section>

          <PosterImage
            v-if="run.game?.poster"
            :src="run.game.poster"
            :alt="`Постер игры «${run.game.name}»`"
            fit="contain"
            class="run__poster"
          />
        </aside>

        <RunRegistrations
          v-if="run.canManageRegistrations && run.registrations"
          :run="run"
          class="run__registrations"
          @update="applyRun"
        />
      </article>
    </template>
  </div>
</template>

<style scoped>
.run {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: var(--space-8) var(--space-10);
  align-items: start;
}
.run__main {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  min-width: 0;
}
.run__main h2 {
  margin-bottom: var(--space-2);
  font-size: var(--text-md);
}
.run__summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4) var(--space-6);
  padding: var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
}
.run__summary > div {
  min-width: 0;
}
.run__summary dt {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.run__summary dt svg {
  flex: none;
  color: var(--text-subtle);
}
.run__summary dd {
  overflow-wrap: anywhere;
}
.run__strong {
  font-weight: 600;
}
.run__strong::first-letter {
  text-transform: uppercase;
}
.run__note {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.run__game-link {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-1) var(--space-3);
  margin-bottom: var(--space-3);
  font-weight: 600;
}
.run__facts {
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: 400;
}
.run__more {
  margin-top: var(--space-2);
  padding: 0;
  border: 0;
  background: none;
  color: var(--accent-text);
  font-weight: 550;
}
.run__more:hover {
  text-decoration: underline;
}
.run__flags {
  padding: var(--space-4);
  border-left: 3px solid var(--warning-text);
  border-radius: var(--radius-md);
  background: var(--warning-soft);
}
.run__aside {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  min-width: 0;
}
.run__aside-title {
  margin-bottom: var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: 600;
  letter-spacing: 0;
}
.run__poster {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  max-height: 440px;
}
.run__registrations {
  grid-column: 1 / -1;
}

/* Телефон и планшет: одна колонка; запись — сразу после «когда и где». */
@media (max-width: 859px) {
  .run {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-6);
  }
  .run__main {
    display: contents;
  }
  .run__main > section:first-child {
    order: -2;
  }
  .run__aside {
    order: -1;
  }
  .run__poster {
    max-height: 320px;
  }
  .run__registrations {
    order: 1;
  }
}
</style>
