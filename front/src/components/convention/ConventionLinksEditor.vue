<script setup>
import { reactive, ref } from 'vue'
import { Pencil, Plus, Trash2 } from '@lucide/vue'
import { ApiError } from '@/api/client'
import { LINK_TYPES, conventionsApi } from '@/api/conventions'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import FormField from '@/components/ui/FormField.vue'

/**
 * Редактор ссылок конвента: каждая ссылка сохраняется сразу (отдельный ресурс API).
 * v-model:links — массив ссылок конвента.
 */
const props = defineProps({
  conventionId: { type: Number, required: true },
})
const links = defineModel('links', { type: Array, required: true })

const toast = useToast()
const confirm = useConfirm()

/** null — форма закрыта; 'new' — добавление; число — id изменяемой ссылки. */
const editing = ref(null)
const form = reactive({ type: 'website', url: '', title: '' })
const errors = ref({})
const formError = ref('')
const saving = ref(false)
const removingId = ref(null)

function openForm(link = null) {
  editing.value = link ? link.id : 'new'
  Object.assign(form, { type: link?.type ?? 'website', url: link?.url ?? '', title: link?.title ?? '' })
  errors.value = {}
  formError.value = ''
}

/** Адрес без схемы дополняем https://, иначе backend его не примет. */
function normalizeUrl(value) {
  const url = value.trim()
  return url && !/^[a-z][a-z0-9+.-]*:\/\//i.test(url) ? `https://${url}` : url
}

async function save() {
  if (saving.value) return
  formError.value = ''
  const url = normalizeUrl(form.url)
  if (!url) {
    errors.value = { url: 'Укажите адрес ссылки' }
    return
  }
  errors.value = {}
  const data = { conventionId: props.conventionId, url, type: form.type, title: form.title.trim() }
  saving.value = true
  try {
    if (editing.value === 'new') {
      links.value = [...links.value, await conventionsApi.createLink(data)]
      toast.success('Ссылка добавлена')
    } else {
      const saved = await conventionsApi.updateLink(editing.value, data)
      links.value = links.value.map((link) => (link.id === saved.id ? saved : link))
      toast.success('Ссылка сохранена')
    }
    editing.value = null
  } catch (err) {
    if (err instanceof ApiError && err.hasFieldErrors) {
      errors.value = { url: err.field('url'), type: err.field('linkType'), title: err.field('title') }
    }
    if (!Object.values(errors.value).some(Boolean)) {
      formError.value = err instanceof ApiError ? err.detail : 'Что-то пошло не так. Попробуйте ещё раз.'
    }
  } finally {
    saving.value = false
  }
}

async function remove(link) {
  const ok = await confirm({ title: 'Удалить ссылку?', message: link.url, confirmText: 'Удалить', danger: true })
  if (!ok) return
  removingId.value = link.id
  try {
    await conventionsApi.removeLink(link.id)
    links.value = links.value.filter((item) => item.id !== link.id)
    if (editing.value === link.id) editing.value = null
    toast.success('Ссылка удалена')
  } catch (err) {
    toast.apiError(err, 'Не удалось удалить ссылку')
  } finally {
    removingId.value = null
  }
}
</script>

<template>
  <div class="links-editor">
    <ul v-if="links.length" class="links-editor__list">
      <li v-for="link in links" :key="link.id" class="links-editor__item">
        <div class="links-editor__text">
          <span class="links-editor__title">{{ link.displayTitle }}</span>
          <span class="links-editor__type">{{ link.typeLabel }}</span>
          <a :href="link.url" target="_blank" rel="noopener noreferrer" class="links-editor__url">{{ link.url }}</a>
        </div>
        <AppButton size="sm" variant="ghost" icon-only :aria-label="`Изменить ссылку: ${link.displayTitle}`" @click="openForm(link)">
          <Pencil :size="16" aria-hidden="true" />
        </AppButton>
        <AppButton
          size="sm"
          variant="ghost"
          icon-only
          :loading="removingId === link.id"
          :aria-label="`Удалить ссылку: ${link.displayTitle}`"
          @click="remove(link)"
        >
          <Trash2 :size="16" aria-hidden="true" />
        </AppButton>
      </li>
    </ul>
    <p v-else-if="editing === null" class="links-editor__empty">Ссылок пока нет.</p>

    <form v-if="editing !== null" class="links-editor__form" novalidate @submit.prevent="save">
      <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>
      <div class="links-editor__row">
        <FormField label="Тип" :error="errors.type">
          <AppSelect v-model="form.type" :options="LINK_TYPES" />
        </FormField>
        <FormField label="Адрес" :error="errors.url" required>
          <AppInput v-model="form.url" type="url" inputmode="url" placeholder="https://" autocomplete="off" autofocus />
        </FormField>
      </div>
      <FormField label="Подпись" :error="errors.title" hint="Необязательно: без подписи показывается тип ссылки">
        <AppInput v-model="form.title" maxlength="255" autocomplete="off" />
      </FormField>
      <div class="links-editor__actions">
        <AppButton variant="primary" type="submit" :loading="saving">
          {{ editing === 'new' ? 'Добавить ссылку' : 'Сохранить ссылку' }}
        </AppButton>
        <AppButton :disabled="saving" @click="editing = null">Отмена</AppButton>
      </div>
    </form>

    <AppButton v-else class="links-editor__add" @click="openForm()">
      <Plus :size="16" aria-hidden="true" />
      Добавить ссылку
    </AppButton>
  </div>
</template>

<style scoped>
.links-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.links-editor__list {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
}
.links-editor__item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-2) var(--space-2) var(--space-3);
}
.links-editor__item + .links-editor__item {
  border-top: 1px solid var(--border);
}
.links-editor__text {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0 var(--space-2);
  flex: 1;
  min-width: 0;
}
.links-editor__title {
  font-weight: 550;
}
.links-editor__type {
  color: var(--text-subtle);
  font-size: var(--text-sm);
}
.links-editor__url {
  flex-basis: 100%;
  min-width: 0;
  font-size: var(--text-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.links-editor__empty {
  color: var(--text-muted);
}
.links-editor__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
}
.links-editor__row {
  display: grid;
  grid-template-columns: minmax(0, 11rem) minmax(0, 1fr);
  gap: var(--space-3);
  align-items: start;
}
.links-editor__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.links-editor__add {
  align-self: flex-start;
}
@media (max-width: 519px) {
  .links-editor__row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
