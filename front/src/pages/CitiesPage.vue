<script setup>
import { computed, onMounted, ref } from 'vue'
import { Building2, Pencil, Plus } from '@lucide/vue'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { useCitiesStore } from '@/stores/cities'
import { plural } from '@/utils/format'
import { timezoneLabel } from '@/utils/timezones'
import CityDialog from '@/components/venue/CityDialog.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

/** Справочник городов для администраторов: название и часовой пояс. */
const auth = useAuthStore()
const cities = useCitiesStore()
const toast = useToast()
const back = { to: { name: 'venues' }, label: 'Все площадки' }

const isStaff = computed(() => Boolean(auth.user?.isStaff))

function load() {
  // Справочник кэшируется на сеанс — здесь нужны свежие данные.
  cities.load({ force: true }).catch(() => {})
}
onMounted(load)

const countLabel = computed(() => {
  if (!cities.loaded) return ''
  const count = cities.items.length
  return `${count} ${plural(count, ['город', 'города', 'городов'])}`
})

const dialogOpen = ref(false)
const editing = ref(null)

function openDialog(city = null) {
  editing.value = city
  dialogOpen.value = true
}
</script>

<template>
  <div class="container container--narrow">
    <PageHeader title="Города" :back="back">
      <template v-if="countLabel" #meta>{{ countLabel }}</template>
      <template v-if="isStaff" #actions>
        <AppButton variant="primary" @click="openDialog()">
          <Plus :size="16" aria-hidden="true" />
          Добавить город
        </AppButton>
      </template>
    </PageHeader>

    <EmptyState
      v-if="!isStaff"
      :icon="Building2"
      title="Раздел для администраторов"
      description="Править справочник городов могут только администраторы портала."
    />
    <ErrorState v-else-if="cities.error" :error="cities.error" title="Не удалось загрузить города" @retry="load" />
    <div v-else-if="!cities.loaded" class="cities" aria-busy="true" aria-label="Загрузка городов">
      <AppSkeleton v-for="n in 6" :key="n" height="52px" />
    </div>
    <EmptyState v-else-if="!cities.items.length" :icon="Building2" title="Городов пока нет">
      <AppButton variant="primary" @click="openDialog()">Добавить город</AppButton>
    </EmptyState>

    <ul v-else class="cities">
      <li v-for="city in cities.items" :key="city.id" class="cities__item">
        <div class="cities__text">
          <p class="cities__name">{{ city.name }}</p>
          <p class="cities__zone">
            {{ timezoneLabel(city.timezone) }}<template v-if="city.region"> · {{ city.region.name }}</template>
          </p>
        </div>
        <AppButton size="sm" :aria-label="`Изменить город: ${city.name}`" @click="openDialog(city)">
          <Pencil :size="14" aria-hidden="true" />
          Изменить
        </AppButton>
      </li>
    </ul>

    <CityDialog
      v-model:open="dialogOpen"
      :city="editing"
      @created="(city) => toast.success(`Город «${city.name}» добавлен`)"
      @saved="(city) => toast.success(`Город «${city.name}» сохранён`)"
    />
  </div>
</template>

<style scoped>
.cities {
  display: flex;
  flex-direction: column;
  padding-bottom: var(--space-10);
}
.cities__item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-4);
  padding-block: var(--space-3);
  border-bottom: 1px solid var(--border);
}
.cities__item:first-child {
  border-top: 1px solid var(--border);
}
.cities__text {
  flex: 1 1 220px;
  min-width: 0;
}
.cities__name {
  font-weight: 600;
  overflow-wrap: anywhere;
}
.cities__zone {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
</style>
