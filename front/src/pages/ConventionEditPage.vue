<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Lock } from '@lucide/vue'
import { ApiError } from '@/api/client'
import { conventionsApi } from '@/api/conventions'
import { useAsyncData } from '@/composables/useAsyncData'
import { usePageTitle } from '@/composables/usePageTitle'
import { useToast } from '@/composables/useToast'
import ConventionLinksEditor from '@/components/convention/ConventionLinksEditor.vue'
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
  /** Идентификатор конвента; не задан — создание нового. */
  id: { type: String, default: null },
})

const router = useRouter()
const toast = useToast()
const isEdit = computed(() => Boolean(props.id))

const { data: convention, error: loadError, reload } = useAsyncData(
  (signal) => (props.id ? conventionsApi.get(props.id, { signal }) : Promise.resolve(null)),
  { watch: () => props.id },
)

const back = computed(() =>
  isEdit.value
    ? { to: { name: 'convention', params: { id: props.id } }, label: convention.value?.name || 'К конвенту' }
    : { to: { name: 'conventions' }, label: 'Все конвенты' },
)
usePageTitle(() => (convention.value ? `${convention.value.name} — редактирование` : ''))

const form = reactive({ name: '', description: '' })
const links = ref([])
const errors = ref({})
const formError = ref('')
const saving = ref(false)
const formEl = ref(null)

// Форму заполняем один раз: повторная загрузка (вход/выход) не должна стирать введённое.
let filledFor = null
watch(
  convention,
  (value) => {
    if (!value) return
    links.value = value.links
    if (filledFor === value.id) return
    filledFor = value.id
    Object.assign(form, { name: value.name, description: value.description })
  },
  { immediate: true },
)

function validate() {
  const result = {}
  if (!form.name.trim()) result.name = 'Укажите название конвента'
  else if (form.name.trim().length > 255) result.name = 'Название длиннее 255 символов'
  errors.value = result
  return Object.keys(result).length === 0
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
  const data = { name: form.name.trim(), description: form.description.trim() }
  saving.value = true
  try {
    if (isEdit.value) {
      const saved = await conventionsApi.update(props.id, data)
      toast.success('Конвент сохранён')
      router.push({ name: 'convention', params: { id: saved.id } })
    } else {
      const saved = await conventionsApi.create(data)
      toast.success('Конвент создан. Теперь можно добавить ссылки.')
      // Остаёмся в редакторе: ссылки доступны только у сохранённого конвента.
      router.replace({ name: 'convention-edit', params: { id: saved.id } })
    }
  } catch (err) {
    if (err instanceof ApiError && err.hasFieldErrors) {
      errors.value = { name: err.field('name'), description: err.field('description') }
    }
    if (!Object.values(errors.value).some(Boolean)) {
      formError.value = err instanceof ApiError ? err.detail : 'Что-то пошло не так. Попробуйте ещё раз.'
    }
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
      <ErrorState :error="loadError" title="Не удалось загрузить конвент" not-found-title="Конвент не найден" @retry="reload" />
    </template>

    <template v-else-if="isEdit && !convention">
      <PageHeader :back="back">
        <template #title><AppSkeleton width="min(320px, 70vw)" height="1.2em" /></template>
      </PageHeader>
      <div aria-busy="true" aria-label="Загрузка конвента">
        <AppSkeleton v-for="n in 3" :key="n" height="2.5rem" radius="md" class="convention-form__skeleton" />
      </div>
    </template>

    <template v-else-if="isEdit && !convention.canEdit">
      <PageHeader :back="back" />
      <EmptyState
        :icon="Lock"
        title="Нет прав на редактирование"
        description="Изменять конвент могут его организаторы и администраторы."
      >
        <AppButton :to="back.to">Вернуться к конвенту</AppButton>
      </EmptyState>
    </template>

    <template v-else>
      <PageHeader :title="isEdit ? 'Редактирование конвента' : 'Новый конвент'" :back="back" />

      <form ref="formEl" class="convention-form" novalidate @submit.prevent="submit">
        <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>

        <FormField label="Название" :error="errors.name" required>
          <AppInput v-model="form.name" maxlength="255" autocomplete="off" />
        </FormField>

        <FormField
          label="Описание"
          :error="errors.description"
          hint="Что это за конвент, для кого он и чем отличается. Показывается на странице конвента и каждого его проведения."
        >
          <AppTextarea v-model="form.description" rows="8" />
        </FormField>

        <div class="convention-form__actions">
          <AppButton variant="primary" type="submit" :loading="saving">
            {{ isEdit ? 'Сохранить' : 'Добавить конвент' }}
          </AppButton>
          <AppButton :to="back.to" :disabled="saving">Отмена</AppButton>
        </div>
      </form>

      <section class="convention-form__links" aria-labelledby="convention-form-links">
        <h2 id="convention-form-links">Ссылки</h2>
        <template v-if="isEdit">
          <p class="convention-form__hint">Сайт, сообщество, чат конвента. Каждая ссылка сохраняется сразу.</p>
          <ConventionLinksEditor v-model:links="links" :convention-id="convention.id" />
        </template>
        <AppAlert v-else tone="info">
          Ссылки на сайт и сообщества можно будет добавить сразу после создания конвента — редактор останется открытым.
        </AppAlert>
      </section>

      <p v-if="!isEdit" class="convention-form__hint">
        Вы станете организатором конвента. Проведения (город, даты, расписание) добавляются на странице конвента.
      </p>
    </template>
  </div>
</template>

<style scoped>
.convention-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.convention-form__skeleton {
  margin-bottom: var(--space-4);
}
.convention-form__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.convention-form__links {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--border);
}
.convention-form__links h2 {
  font-size: var(--text-lg);
}
.convention-form__hint {
  margin-top: var(--space-4);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.convention-form__links .convention-form__hint {
  margin-top: 0;
}
</style>
