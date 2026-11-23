<script setup>
import { nextTick, reactive, ref, watch } from 'vue'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import AppInput from '@/components/ui/AppInput.vue'
import FormField from '@/components/ui/FormField.vue'

/** Правка имени и фамилии текущего пользователя. */
const open = defineModel('open', { type: Boolean, default: false })

const auth = useAuthStore()
const toast = useToast()
const formEl = ref(null)
const form = reactive({ firstName: '', lastName: '' })
const errors = ref({})
const formError = ref('')
const saving = ref(false)

watch(open, (value) => {
  if (!value) return
  form.firstName = auth.user?.first_name ?? ''
  form.lastName = auth.user?.last_name ?? ''
  errors.value = {}
  formError.value = ''
  saving.value = false
})

async function submit() {
  if (saving.value) return
  errors.value = {}
  formError.value = ''
  const firstName = form.firstName.trim()
  const lastName = form.lastName.trim()
  if (!firstName && !lastName) {
    errors.value = { firstName: 'Укажите имя или фамилию' }
    await nextTick()
    formEl.value?.querySelector('[aria-invalid="true"]')?.focus()
    return
  }
  saving.value = true
  try {
    await auth.updateProfile({ firstName, lastName })
    toast.success('Имя сохранено')
    open.value = false
  } catch (err) {
    errors.value = { firstName: err.field?.('first_name'), lastName: err.field?.('last_name') }
    if (!errors.value.firstName && !errors.value.lastName) {
      formError.value = err.detail || 'Не удалось сохранить имя. Попробуйте ещё раз.'
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppDialog v-model:open="open" title="Изменить имя" :dismissible="!saving">
    <form id="profile-name-form" ref="formEl" class="profile-form" novalidate @submit.prevent="submit">
      <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>
      <FormField label="Имя" :error="errors.firstName">
        <AppInput v-model="form.firstName" name="first_name" autocomplete="given-name" maxlength="150" autofocus />
      </FormField>
      <FormField label="Фамилия" :error="errors.lastName" hint="Так вас видят мастера, игроки и организаторы.">
        <AppInput v-model="form.lastName" name="last_name" autocomplete="family-name" maxlength="150" />
      </FormField>
    </form>
    <template #footer>
      <AppButton :disabled="saving" @click="open = false">Отмена</AppButton>
      <AppButton type="submit" form="profile-name-form" variant="primary" :loading="saving">Сохранить</AppButton>
    </template>
  </AppDialog>
</template>

<style scoped>
.profile-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
</style>
