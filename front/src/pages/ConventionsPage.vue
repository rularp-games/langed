<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Globe, Link, MessagesSquare, Play, Plus, Send, Tent, Upload, Users } from '@lucide/vue'
import { conventionsApi } from '@/api/conventions'
import { useAsyncData } from '@/composables/useAsyncData'
import { useAuthDialog } from '@/composables/useAuthDialog'
import { useQueryParam } from '@/composables/useQueryParam'
import { useAuthStore } from '@/stores/auth'
import { plural } from '@/utils/format'
import ConventionImportDialog from '@/components/convention/ConventionImportDialog.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'

const PAGE_SIZE = 24
// Те же нейтральные иконки, что в LinkList.
const LINK_ICONS = { website: Globe, vk: Users, telegram: Send, discord: MessagesSquare, youtube: Play, other: Link }

const router = useRouter()
const auth = useAuthStore()
const { requireAuth } = useAuthDialog()

const page = useQueryParam('page', { number: true, default: 1 })
const search = useQueryParam('search', { replace: true, resets: ['page'] })

const { data, error, loading, reload } = useAsyncData(
  (signal) => conventionsApi.list({ page: page.value, pageSize: PAGE_SIZE, search: search.value }, { signal }),
  { watch: [page, search] },
)

// Страница за пределами списка (устаревшая ссылка) — возвращаемся на первую.
watch(error, (value) => {
  if (value?.status === 404 && page.value > 1) page.value = 1
})

const countLabel = computed(() => {
  if (!data.value) return ''
  const { count } = data.value
  return `${count} ${plural(count, ['конвент', 'конвента', 'конвентов'])}`
})

const eventsLabel = (count) => `${count} ${plural(count, ['проведение', 'проведения', 'проведений'])}`

function addConvention() {
  requireAuth(() => router.push({ name: 'convention-new' }), { reason: 'Войдите, чтобы добавить конвент.' })
}

const importOpen = ref(false)
</script>

<template>
  <div class="container">
    <PageHeader title="Конвенты">
      <template v-if="countLabel" #meta>{{ countLabel }}</template>
      <template #actions>
        <AppButton v-if="auth.user?.isStaff" @click="importOpen = true">
          <Upload :size="16" aria-hidden="true" />
          Импорт из CSV
        </AppButton>
        <AppButton variant="primary" @click="addConvention">
          <Plus :size="16" aria-hidden="true" />
          Добавить конвент
        </AppButton>
      </template>
      <SearchInput v-model="search" label="Поиск по конвентам" placeholder="Название конвента" />
    </PageHeader>

    <ErrorState v-if="error" :error="error" title="Не удалось загрузить конвенты" @retry="reload" />

    <ul v-else-if="!data" class="conventions" aria-busy="true" aria-label="Загрузка конвентов">
      <li v-for="n in 8" :key="n" class="conventions__skeleton">
        <AppSkeleton height="100%" radius="lg" />
      </li>
    </ul>

    <EmptyState
      v-else-if="!data.items.length"
      :icon="Tent"
      :title="search ? 'Ничего не нашлось' : 'Конвентов пока нет'"
      :description="
        search
          ? `По запросу «${search}» конвентов нет. Проверьте написание или попробуйте другое название.`
          : 'Добавьте первый конвент.'
      "
    >
      <AppButton v-if="search" @click="search = ''">Сбросить поиск</AppButton>
    </EmptyState>

    <template v-else>
      <ul class="conventions" :class="{ 'is-loading': loading }" :aria-busy="loading">
        <li v-for="convention in data.items" :key="convention.id" class="convention-row">
          <h2 class="convention-row__title">
            <RouterLink :to="{ name: 'convention', params: { id: convention.id } }" class="convention-row__link">
              {{ convention.name }}
            </RouterLink>
          </h2>
          <p v-if="convention.description" class="convention-row__description">{{ convention.description }}</p>
          <div v-if="convention.eventsCount || convention.links.length" class="convention-row__foot">
            <span v-if="convention.eventsCount" class="convention-row__count">{{ eventsLabel(convention.eventsCount) }}</span>
            <ul v-if="convention.links.length" class="convention-row__links">
              <li v-for="link in convention.links" :key="link.id">
                <a
                  :href="link.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="convention-row__icon"
                  :aria-label="`${link.displayTitle} — ${convention.name}`"
                  :title="link.displayTitle"
                >
                  <component :is="LINK_ICONS[link.type] || Link" :size="16" aria-hidden="true" />
                </a>
              </li>
            </ul>
          </div>
        </li>
      </ul>
      <AppPagination
        v-model:page="page"
        class="conventions-pagination"
        :count="data.count"
        :page-size="PAGE_SIZE"
        :disabled="loading"
      />
    </template>

    <ConventionImportDialog v-model:open="importOpen" @imported="reload" />
  </div>
</template>

<style scoped>
.conventions {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-3);
  transition: opacity var(--duration);
}
.conventions.is-loading {
  opacity: 0.6;
}
.conventions__skeleton {
  height: 108px;
}
.convention-row {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  transition:
    border-color var(--duration),
    box-shadow var(--duration);
}
.convention-row:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
}
.convention-row__title {
  font-size: var(--text-md);
  overflow-wrap: anywhere;
}
.convention-row__link {
  color: var(--text);
  text-decoration: none;
}
/* Вся карточка — область ссылки на конвент; значки внешних ссылок лежат поверх. */
.convention-row__link::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
}
.convention-row__description {
  display: -webkit-box;
  color: var(--text-muted);
  font-size: var(--text-sm);
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}
.convention-row__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  min-height: var(--control-h-sm);
  margin-top: auto;
  padding-top: var(--space-1);
}
.convention-row__count {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.convention-row__links {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-left: auto;
}
.convention-row__icon {
  display: grid;
  place-items: center;
  width: var(--control-h-sm);
  height: var(--control-h-sm);
  border-radius: var(--radius-md);
  color: var(--text-muted);
}
.convention-row__icon:hover {
  background: var(--surface-hover);
  color: var(--accent-text);
}
.conventions-pagination {
  margin-top: var(--space-8);
}
@media (max-width: 519px) {
  .conventions {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
