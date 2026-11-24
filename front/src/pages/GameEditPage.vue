<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Lock } from '@lucide/vue'
import { ApiError } from '@/api/client'
import { gamesApi } from '@/api/games'
import { useAsyncData } from '@/composables/useAsyncData'
import { usePageTitle } from '@/composables/usePageTitle'
import { useToast } from '@/composables/useToast'
import { safeHref } from '@/utils/game'
import PosterField from '@/components/game/PosterField.vue'
import RangeField from '@/components/game/RangeField.vue'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import AppTextarea from '@/components/ui/AppTextarea.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import FormField from '@/components/ui/FormField.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  /** Идентификатор игры; не задан — создание новой. */
  id: { type: String, default: null },
})

const router = useRouter()
const toast = useToast()
const isEdit = computed(() => Boolean(props.id))

const { data: game, error: loadError, reload } = useAsyncData(
  (signal) => (props.id ? gamesApi.get(props.id, { signal }) : Promise.resolve(null)),
  { watch: () => props.id },
)

const back = computed(() =>
  isEdit.value
    ? { to: { name: 'game', params: { id: props.id } }, label: game.value?.name || 'К игре' }
    : { to: { name: 'games' }, label: 'Все игры' },
)
usePageTitle(() => (game.value ? `${game.value.name} — редактирование` : ''))

const form = reactive({
  name: '',
  announcement: '',
  redFlags: '',
  authorsText: '',
  sourceUrl: '',
  playersMin: '',
  playersMax: '',
  femaleRolesMin: '',
  femaleRolesMax: '',
  maleRolesMin: '',
  maleRolesMax: '',
  technicians: '',
})
const posterFile = ref(null)
const posterRemoved = ref(false)
const errors = ref({})
const formError = ref('')
const saving = ref(false)
const formEl = ref(null)

/** Число состава в поле формы: null (не указано) — пустое поле, 0 — ноль. */
const countField = (value) => (value === null || value === undefined ? '' : Number(value))
/** Игротехники не бывают «не указаны»: 0 показываем пустым. */
const optional = (value) => (Number(value) > 0 ? Number(value) : '')

// Форму заполняем один раз: повторная загрузка (вход/выход) не должна стирать введённое.
let filledFor = null
watch(game, (value) => {
  if (!value || filledFor === value.id) return
  filledFor = value.id
  Object.assign(form, {
    name: value.name,
    announcement: value.announcement,
    redFlags: value.redFlags,
    authorsText: value.authorsText,
    sourceUrl: value.sourceUrl,
    playersMin: countField(value.playersMin),
    playersMax: countField(value.playersMax),
    femaleRolesMin: countField(value.femaleRolesMin),
    femaleRolesMax: countField(value.femaleRolesMax),
    maleRolesMin: countField(value.maleRolesMin),
    maleRolesMax: countField(value.maleRolesMax),
    technicians: optional(value.technicians),
  })
  posterFile.value = null
  posterRemoved.value = false
})

/** Целое неотрицательное число, null — пусто, NaN — введено не число. */
function toCount(value) {
  if (value === '' || value === null || value === undefined) return null
  const number = Number(value)
  return Number.isInteger(number) && number >= 0 ? number : Number.NaN
}

function rangeError(min, max, { positive = false } = {}) {
  if (Number.isNaN(min) || Number.isNaN(max)) return 'Укажите целые неотрицательные числа'
  if (positive && (min === 0 || max === 0)) return 'Число игроков — не меньше 1'
  if (min !== null && max !== null && min > max) return '«От» не может быть больше «до»'
  return ''
}

function validate() {
  const result = {}
  if (!form.name.trim()) result.name = 'Укажите название игры'
  else if (form.name.trim().length > 255) result.name = 'Название длиннее 255 символов'

  const sourceUrl = form.sourceUrl.trim()
  if (sourceUrl && (!safeHref(sourceUrl) || sourceUrl.length > 500)) {
    result.sourceUrl = 'Укажите адрес целиком, начиная с http:// или https://'
  }

  const players = rangeError(toCount(form.playersMin), toCount(form.playersMax), { positive: true })
  if (players) result.players = players
  const female = rangeError(toCount(form.femaleRolesMin), toCount(form.femaleRolesMax))
  if (female) result.female = female
  const male = rangeError(toCount(form.maleRolesMin), toCount(form.maleRolesMax))
  if (male) result.male = male
  if (Number.isNaN(toCount(form.technicians))) result.technicians = 'Укажите целое неотрицательное число'

  errors.value = result
  return Object.keys(result).length === 0
}

/** Пустое поле состава — null («не указано»). */
function payload() {
  const data = {
    name: form.name.trim(),
    announcement: form.announcement.trim(),
    redFlags: form.redFlags.trim(),
    authorsText: form.authorsText.trim(),
    sourceUrl: form.sourceUrl.trim(),
    playersMin: toCount(form.playersMin),
    playersMax: toCount(form.playersMax),
    femaleRolesMin: toCount(form.femaleRolesMin),
    femaleRolesMax: toCount(form.femaleRolesMax),
    maleRolesMin: toCount(form.maleRolesMin),
    maleRolesMax: toCount(form.maleRolesMax),
    technicians: toCount(form.technicians) ?? 0,
  }
  if (posterFile.value) data.poster = posterFile.value
  else if (posterRemoved.value && game.value?.poster) data.poster = null
  return data
}

function applyError(err) {
  if (!(err instanceof ApiError)) {
    console.error(err)
    formError.value = 'Что-то пошло не так. Попробуйте ещё раз.'
    return
  }
  if (err.hasFieldErrors) {
    errors.value = {
      name: err.field('name'),
      announcement: err.field('announcement'),
      redFlags: err.field('redFlags'),
      authorsText: err.field('authorsText'),
      sourceUrl: err.field('sourceUrl'),
      poster: err.field('poster'),
      players: err.field('playersMin') || err.field('playersMax'),
      female: err.field('femaleRolesMin') || err.field('femaleRolesMax'),
      male: err.field('maleRolesMin') || err.field('maleRolesMax'),
      technicians: err.field('technicians'),
    }
  }
  if (!Object.values(errors.value).some(Boolean)) formError.value = err.detail
}

async function focusFirstError() {
  await nextTick()
  formEl.value?.querySelector('[aria-invalid="true"]')?.focus()
}

async function submit() {
  if (saving.value) return
  formError.value = ''
  if (!validate()) {
    await focusFirstError()
    return
  }
  saving.value = true
  try {
    const saved = isEdit.value
      ? await gamesApi.update(props.id, payload())
      : await gamesApi.create(payload())
    toast.success(isEdit.value ? 'Игра сохранена' : 'Игра добавлена в каталог')
    router.push({ name: 'game', params: { id: saved.id } })
  } catch (err) {
    applyError(err)
    await focusFirstError()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="container container--narrow">
    <template v-if="loadError">
      <PageHeader :back="back" />
      <ErrorState :error="loadError" title="Не удалось загрузить игру" not-found-title="Игра не найдена" @retry="reload" />
    </template>

    <template v-else-if="isEdit && !game">
      <PageHeader :back="back">
        <template #title><AppSkeleton width="min(320px, 70vw)" height="1.2em" /></template>
      </PageHeader>
      <div aria-busy="true" aria-label="Загрузка игры">
        <AppSkeleton v-for="n in 4" :key="n" height="2.5rem" radius="md" class="game-form__skeleton" />
      </div>
    </template>

    <template v-else-if="isEdit && !game.canEdit">
      <PageHeader :back="back" />
      <EmptyState
        :icon="Lock"
        title="Нет прав на редактирование"
        description="Изменять игру могут её авторы и администраторы."
      >
        <AppButton :to="back.to">Вернуться к игре</AppButton>
      </EmptyState>
    </template>

    <template v-else>
      <PageHeader :title="isEdit ? 'Редактирование игры' : 'Новая игра'" :back="back" />

      <form ref="formEl" class="game-form" novalidate @submit.prevent="submit">
        <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>

        <FormField label="Название" :error="errors.name" required>
          <AppInput v-model="form.name" maxlength="255" autocomplete="off" />
        </FormField>

        <FormField
          label="Авторы (текстом)"
          :error="errors.authorsText"
          hint="Для авторов, которых ещё нет на портале: «Имя Фамилия (ссылка на профиль)» через запятую — ссылки станут кликабельными. Зарегистрированных авторов добавляйте на странице игры: они смогут её редактировать."
        >
          <AppTextarea v-model="form.authorsText" rows="2" />
        </FormField>

        <div>
          <PosterField v-model:file="posterFile" v-model:removed="posterRemoved" :current="game?.poster" :disabled="saving" />
          <p v-if="errors.poster" class="game-form__error" role="alert">{{ errors.poster }}</p>
        </div>

        <FormField
          label="Анонс"
          :error="errors.announcement"
          hint="Описание для игроков: жанр, завязка, во что предстоит играть. Показывается в каталоге и на странице прогона."
        >
          <AppTextarea v-model="form.announcement" rows="8" />
        </FormField>

        <FormField
          label="Красные флаги"
          :error="errors.redFlags"
          hint="Темы и приёмы, о которых игроку стоит знать заранее: насилие, физический контакт, тяжёлые переживания. Если таких нет — оставьте пустым."
        >
          <AppTextarea v-model="form.redFlags" rows="4" />
        </FormField>

        <FormField
          label="Ссылка на источник"
          :error="errors.sourceUrl"
          hint="Пост или страница, откуда взят анонс, например запись во ВКонтакте."
        >
          <AppInput v-model="form.sourceUrl" type="url" inputmode="url" maxlength="500" autocomplete="off" placeholder="https://" />
        </FormField>

        <fieldset class="game-form__numbers">
          <legend>Состав</legend>
          <div class="game-form__grid">
            <RangeField
              v-model:min="form.playersMin"
              v-model:max="form.playersMax"
              label="Игроки"
              :error="errors.players"
            />
            <RangeField
              v-model:min="form.femaleRolesMin"
              v-model:max="form.femaleRolesMax"
              label="Женские роли"
              :error="errors.female"
            />
            <RangeField
              v-model:min="form.maleRolesMin"
              v-model:max="form.maleRolesMax"
              label="Мужские роли"
              :error="errors.male"
            />
            <FormField label="Игротехники" :error="errors.technicians">
              <AppInput v-model="form.technicians" type="number" min="0" step="1" inputmode="numeric" />
            </FormField>
          </div>
          <p class="game-form__note">
            Любое поле можно оставить пустым — «не указано», такие параметры на странице игры не показываются.
            0 в ролях означает, что ролей этого типа нет.
          </p>
        </fieldset>

        <div class="game-form__actions">
          <AppButton type="submit" variant="primary" :loading="saving">
            {{ isEdit ? 'Сохранить' : 'Добавить игру' }}
          </AppButton>
          <AppButton :to="back.to" :disabled="saving">Отмена</AppButton>
        </div>
      </form>
    </template>
  </div>
</template>

<style scoped>
.game-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding-bottom: var(--space-10);
}
.game-form__skeleton {
  margin-bottom: var(--space-4);
}
.game-form__numbers {
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
}
.game-form__numbers legend {
  margin-bottom: var(--space-3);
  padding: 0;
  font-size: var(--text-md);
  font-weight: 600;
}
.game-form__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
  align-items: start;
}
.game-form__note {
  margin-top: var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.game-form__error {
  margin-top: var(--space-1);
  color: var(--danger-text);
  font-size: var(--text-sm);
}
.game-form__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

@media (max-width: 719px) {
  .game-form__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
