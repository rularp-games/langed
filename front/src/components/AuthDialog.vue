<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Eye, EyeOff } from '@lucide/vue'
import { ApiError } from '@/api/client'
import { authApi, socialLoginUrl } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import AppAlert from './ui/AppAlert.vue'
import AppButton from './ui/AppButton.vue'
import AppDialog from './ui/AppDialog.vue'
import AppInput from './ui/AppInput.vue'
import FormField from './ui/FormField.vue'
import ProviderIcon from './ProviderIcon.vue'

/**
 * Вход, регистрация и восстановление пароля в одном диалоге, без ухода со страницы.
 * Подключён один раз в App.vue; открывается через useAuthDialog().
 */
const auth = useAuthStore()
const route = useRoute()
const toast = useToast()

/** login | register | reset | reset-sent */
const mode = ref('login')
const form = reactive({ email: '', password: '', firstName: '', lastName: '' })
const fieldErrors = ref({})
const formError = ref('')
const emailTaken = ref(false)
const submitting = ref(false)
const showPassword = ref(false)
const body = ref(null)

const titles = {
  login: 'Вход',
  register: 'Регистрация',
  reset: 'Восстановление пароля',
  'reset-sent': 'Проверьте почту',
}
const providers = computed(() => auth.providers ?? [])

function clearErrors() {
  fieldErrors.value = {}
  formError.value = ''
  emailTaken.value = false
}

async function setMode(next) {
  mode.value = next
  form.password = ''
  showPassword.value = false
  clearErrors()
  await nextTick()
  body.value?.querySelector('input, button')?.focus()
}

watch(
  () => auth.dialog.open,
  (open) => {
    if (!open) return
    Object.assign(form, { email: '', password: '', firstName: '', lastName: '' })
    mode.value = auth.dialog.mode === 'register' ? 'register' : 'login'
    showPassword.value = false
    submitting.value = false
    clearErrors()
    auth.loadProviders()
  },
)

function validate() {
  const errors = {}
  const email = form.email.trim()
  if (!email) errors.email = 'Укажите почту'
  else if (!/^\S+@\S+\.\S+$/.test(email)) errors.email = 'Проверьте адрес почты'
  if (mode.value !== 'reset' && !form.password) errors.password = 'Введите пароль'
  if (mode.value === 'register') {
    if (!form.firstName.trim()) errors.firstName = 'Укажите имя'
    if (!form.lastName.trim()) errors.lastName = 'Укажите фамилию'
  }
  fieldErrors.value = errors
  return Object.keys(errors).length === 0
}

function applyError(error) {
  if (!(error instanceof ApiError)) {
    console.error(error)
    formError.value = 'Что-то пошло не так. Попробуйте ещё раз.'
    return
  }
  if (error.code === 'email_exists') {
    emailTaken.value = true
    fieldErrors.value = { email: 'Эта почта уже зарегистрирована' }
    return
  }
  if (error.hasFieldErrors) {
    fieldErrors.value = {
      email: error.field('email'),
      password: error.field('password'),
      firstName: error.field('first_name'),
      lastName: error.field('last_name'),
    }
  }
  const known = Object.keys(fieldErrors.value).some((key) => fieldErrors.value[key])
  // Тексты ошибок (неверный пароль, сервис недоступен, слишком много попыток) приходят от backend.
  if (!known) formError.value = error.detail
}

async function submit() {
  if (submitting.value) return
  clearErrors()
  if (!validate()) {
    await nextTick()
    body.value?.querySelector('[aria-invalid="true"]')?.focus()
    return
  }
  submitting.value = true
  const email = form.email.trim()
  try {
    if (mode.value === 'login') {
      await auth.login({ email, password: form.password })
    } else if (mode.value === 'register') {
      await auth.register({
        email,
        password: form.password,
        firstName: form.firstName.trim(),
        lastName: form.lastName.trim(),
      })
    } else {
      await authApi.requestPasswordReset(email)
      await setMode('reset-sent')
      return
    }
    auth.closeDialog(true)
    toast.success(`Вы вошли как ${auth.user.displayName}`)
  } catch (error) {
    applyError(error)
  } finally {
    submitting.value = false
  }
}

function onOpenChange(value) {
  if (!value) auth.closeDialog(false)
}
</script>

<template>
  <AppDialog
    :open="auth.dialog.open"
    :title="titles[mode]"
    :dismissible="!submitting"
    @update:open="onOpenChange"
  >
    <div ref="body" class="auth">
      <p v-if="auth.dialog.reason && mode !== 'reset-sent'" class="auth__reason">{{ auth.dialog.reason }}</p>

      <template v-if="mode === 'reset-sent'">
        <p>
          Если такая почта зарегистрирована, мы отправили на неё письмо со ссылкой для смены пароля.
        </p>
        <AppButton variant="primary" block @click="setMode('login')">Вернуться ко входу</AppButton>
      </template>

      <template v-else>
        <template v-if="mode !== 'reset' && providers.length">
          <div class="auth__providers">
            <AppButton
              v-for="provider in providers"
              :key="provider.id"
              :href="socialLoginUrl(provider.id, route.fullPath)"
              block
            >
              <ProviderIcon :provider="provider.id" />
              Продолжить с {{ provider.name }}
            </AppButton>
          </div>
          <p class="auth__divider"><span>или</span></p>
        </template>

        <p v-if="mode === 'reset'" class="text-muted">
          Укажите почту, с которой регистрировались, — пришлём ссылку для смены пароля.
        </p>

        <form class="auth__form" novalidate @submit.prevent="submit">
          <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>

          <div v-if="mode === 'register'" class="auth__names">
            <FormField label="Имя" :error="fieldErrors.firstName">
              <AppInput v-model="form.firstName" name="first_name" autocomplete="given-name" autofocus />
            </FormField>
            <FormField label="Фамилия" :error="fieldErrors.lastName">
              <AppInput v-model="form.lastName" name="last_name" autocomplete="family-name" />
            </FormField>
          </div>

          <FormField label="Почта" :error="fieldErrors.email">
            <AppInput
              v-model="form.email"
              type="email"
              name="email"
              inputmode="email"
              :autocomplete="mode === 'login' ? 'username' : 'email'"
              autocapitalize="none"
              spellcheck="false"
              :autofocus="mode !== 'register'"
            />
          </FormField>
          <p v-if="emailTaken" class="auth__switch auth__switch--inline">
            <button type="button" class="auth__link" @click="setMode('login')">Войти с этой почтой</button>
            или
            <button type="button" class="auth__link" @click="setMode('reset')">восстановить пароль</button>
          </p>

          <FormField v-if="mode !== 'reset'" label="Пароль" :error="fieldErrors.password">
            <template v-if="mode === 'login'" #labelAside>
              <button type="button" class="auth__link" @click="setMode('reset')">Забыли пароль?</button>
            </template>
            <AppInput
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              name="password"
              :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
            >
              <template #suffix>
                <AppButton
                  variant="ghost"
                  size="sm"
                  icon-only
                  :aria-label="showPassword ? 'Скрыть пароль' : 'Показать пароль'"
                  :aria-pressed="showPassword"
                  @click="showPassword = !showPassword"
                >
                  <component :is="showPassword ? EyeOff : Eye" :size="16" aria-hidden="true" />
                </AppButton>
              </template>
            </AppInput>
          </FormField>

          <AppButton type="submit" variant="primary" block :loading="submitting">
            {{ mode === 'login' ? 'Войти' : mode === 'register' ? 'Зарегистрироваться' : 'Отправить ссылку' }}
          </AppButton>
        </form>

        <p class="auth__switch">
          <template v-if="mode === 'login'">
            Нет аккаунта?
            <button type="button" class="auth__link" @click="setMode('register')">Зарегистрироваться</button>
          </template>
          <template v-else-if="mode === 'register'">
            Уже есть аккаунт?
            <button type="button" class="auth__link" @click="setMode('login')">Войти</button>
          </template>
          <button v-else type="button" class="auth__link" @click="setMode('login')">Вернуться ко входу</button>
        </p>
      </template>
    </div>
  </AppDialog>
</template>

<style scoped>
.auth {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.auth__reason {
  margin-top: calc(-1 * var(--space-2));
  color: var(--text-muted);
}
.auth__providers {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.auth__divider {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--text-subtle);
  font-size: var(--text-sm);
}
.auth__divider::before,
.auth__divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}
.auth__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.auth__form > .btn {
  margin-top: var(--space-1);
}
.auth__names {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}
.auth__switch {
  color: var(--text-muted);
  font-size: var(--text-sm);
  text-align: center;
}
.auth__switch--inline {
  margin-top: calc(-1 * var(--space-2));
  text-align: left;
}
.auth__link {
  padding: 0;
  border: 0;
  background: none;
  color: var(--accent-text);
  font-size: var(--text-sm);
  font-weight: 550;
  text-decoration: underline;
  text-decoration-thickness: 1px;
  text-underline-offset: 0.18em;
}
.auth__link:hover {
  color: var(--accent-hover);
}
</style>
