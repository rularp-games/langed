import { api } from './client'

/**
 * Пользователь в едином виде для интерфейса.
 * Backend: {is_authenticated:false} | {is_authenticated:true, id, username, email, first_name,
 * last_name, display_name, is_staff, has_password_login}. В интерфейсе: те же поля + displayName,
 * isStaff, hasPasswordLogin (вошёл по почте и паролю — может сменить пароль).
 */
export function normalizeUser(raw) {
  if (!raw || !raw.is_authenticated) return null
  const fullName = [raw.first_name, raw.last_name].filter(Boolean).join(' ')
  return {
    ...raw,
    isStaff: Boolean(raw.is_staff),
    hasPasswordLogin: Boolean(raw.has_password_login),
    displayName: raw.display_name || fullName || raw.username || raw.email || 'Пользователь',
  }
}

/** Ответы login/register — объект пользователя (is_authenticated может отсутствовать). */
function normalizeAuthResponse(raw) {
  return normalizeUser({ is_authenticated: true, ...raw })
}

export const authApi = {
  /** Текущий пользователь или null. Заодно ставит CSRF-cookie. */
  async fetchUser(options) {
    return normalizeUser(await api.get('/api/auth/user/', options))
  },

  /** [{id, name}] — провайдеры входа через соцсети. */
  async fetchProviders(options) {
    const data = await api.get('/api/auth/providers/', options)
    return Array.isArray(data) ? data : (data?.results ?? [])
  },

  async login({ email, password }) {
    return normalizeAuthResponse(await api.post('/api/auth/login/', { email, password }))
  },

  async register({ email, password, firstName, lastName }) {
    return normalizeAuthResponse(
      await api.post('/api/auth/register/', {
        email,
        password,
        first_name: firstName,
        last_name: lastName,
      }),
    )
  },

  requestPasswordReset(email) {
    return api.post('/api/auth/password-reset/', { email })
  },

  logout() {
    return api.post('/api/auth/logout/')
  },

  /** Правка имени и фамилии (обе строки можно оставить пустыми, но не одновременно). @returns пользователь */
  async updateProfile({ firstName, lastName }) {
    return normalizeAuthResponse(
      await api.patch('/api/auth/user/', { first_name: firstName, last_name: lastName }),
    )
  },

  /** Смена пароля — только для вошедших по почте и паролю (user.hasPasswordLogin). */
  changePassword({ currentPassword, newPassword }) {
    return api.post('/api/auth/password-change/', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },
}

/** Адрес обычного перехода браузера для входа через соцсеть. */
export function socialLoginUrl(providerId, next = '/') {
  const query = new URLSearchParams({ idp: providerId, next })
  return `/oidc/authenticate/?${query}`
}

/**
 * Сообщения для ?auth_error=<code> после возврата из соцсети. Код — либо от Keycloak
 * (access_denied, login_required, …), либо от backend: invalid_state, auth_unavailable, auth_failed.
 */
const SOCIAL_ERROR_MESSAGES = {
  access_denied: 'Вход через соцсеть отменён.',
  login_required: 'Вход не завершён. Попробуйте ещё раз.',
  interaction_required: 'Вход не завершён. Попробуйте ещё раз.',
  temporarily_unavailable: 'Сервис входа временно недоступен. Попробуйте позже.',
  invalid_state: 'Время на вход истекло. Попробуйте ещё раз.',
  auth_unavailable: 'Сервис входа временно недоступен. Попробуйте позже.',
  auth_failed: 'Не удалось войти через соцсеть. Попробуйте ещё раз или войдите по почте и паролю.',
}

export function socialErrorMessage(code) {
  return SOCIAL_ERROR_MESSAGES[code] || 'Не удалось войти через соцсеть. Попробуйте ещё раз.'
}
