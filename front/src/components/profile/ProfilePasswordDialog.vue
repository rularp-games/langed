<script setup>
import { nextTick, reactive, ref, watch } from 'vue'
import { authApi } from '@/api/auth'
import { useToast } from '@/composables/useToast'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import AppInput from '@/components/ui/AppInput.vue'
import FormField from '@/components/ui/FormField.vue'

/** Смена пароля (для вошедших по почте и паролю): текущий пароль и новый. */
const PASSWORD_MIN_LENGTH = 8

const open = defineModel('open', { type: Boolean, default: false })

const toast = useToast()
const formEl = ref(null)
const form = reactive({ currentPassword: '', newPassword: '' })
const errors = ref({})
const formError = ref('')
const saving = ref(false)

watch(open, (value) => {
  if (!value) return
  Object.assign(form, { currentPassword: '', newPassword: '' })
  errors.value = {}
  formError.value = ''
  saving.value = false
})

function validate() {
  const result = {}
  if (!form.currentPassword) result.currentPassword = 'Введите текущий пароль'
  if (!form.newPassword) result.newPassword = 'Введите новый пароль'
  else if (form.newPassword.length < PASSWORD_MIN_LENGTH) {
    result.newPassword = `Пароль должен быть не короче ${PASSWORD_MIN_LENGTH} символов`
  }
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
    focusFirstError()
    return
  }
  saving.value = true
  try {
    await authApi.changePassword(form)
    toast.success('Пароль изменён')
    open.value = false
  } catch (err) {
    errors.value = {
      currentPassword: err.field?.('current_password'),
      newPassword: err.field?.('new_password'),
    }
    if (errors.value.currentPassword || errors.value.newPassword) focusFirstError()
    else formError.value = err.detail || 'Не удалось сменить пароль. Попробуйте ещё раз.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppDialog v-model:open="open" title="Сменить пароль" :dismissible="!saving">
    <form id="profile-password-form" ref="formEl" class="profile-form" novalidate @submit.prevent="submit">
      <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>
      <FormField label="Текущий пароль" :error="errors.currentPassword">
        <AppInput
          v-model="form.currentPassword"
          type="password"
          name="current_password"
          autocomplete="current-password"
          autofocus
        />
      </FormField>
      <FormField
        label="Новый пароль"
        :error="errors.newPassword"
        :hint="`Не короче ${PASSWORD_MIN_LENGTH} символов`"
      >
        <AppInput v-model="form.newPassword" type="password" name="new_password" autocomplete="new-password" />
      </FormField>
    </form>
    <template #footer>
      <AppButton :disabled="saving" @click="open = false">Отмена</AppButton>
      <AppButton type="submit" form="profile-password-form" variant="primary" :loading="saving">
        Сменить пароль
      </AppButton>
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
