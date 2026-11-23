/**
 * Единая обёртка над fetch для API Langed.
 *
 *   import { api, ApiError, isAbortError } from '@/api/client'
 *   const data = await api.get('/api/games/', { params: { page: 2 }, signal })
 *   await api.post('/api/games/', payload)          // объект → JSON, FormData → как есть
 *
 * Любая ошибка (сеть, HTTP ≥ 400) — ApiError; отмена запроса — исходный AbortError
 * (проверяется через isAbortError и обычно молча игнорируется).
 */

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])
const CSRF_COOKIE = 'csrftoken'
const CSRF_BOOTSTRAP_URL = '/api/auth/user/'

const STATUS_MESSAGES = {
  0: 'Нет связи с сервером. Проверьте подключение к интернету.',
  400: 'Проверьте введённые данные.',
  401: 'Нужно войти в аккаунт.',
  403: 'Недостаточно прав для этого действия.',
  404: 'Не найдено.',
  413: 'Файл слишком большой.',
  429: 'Слишком много попыток. Подождите немного и повторите.',
  503: 'Сервис временно недоступен. Попробуйте позже.',
}

export class ApiError extends Error {
  /**
   * @param {object} init
   * @param {number} init.status       HTTP-статус; 0 — сеть недоступна
   * @param {string} [init.code]       машинный код ошибки (invalid_credentials, …)
   * @param {string} [init.detail]     сообщение для пользователя
   * @param {Record<string,string[]>} [init.fieldErrors] ошибки по полям формы
   * @param {*} [init.data]            исходное тело ответа
   */
  constructor({ status, code = null, detail, fieldErrors = {}, data = null }) {
    super(detail || STATUS_MESSAGES[status] || 'Что-то пошло не так. Попробуйте ещё раз.')
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.detail = this.message
    this.fieldErrors = fieldErrors
    this.data = data
  }

  get isNetwork() {
    return this.status === 0
  }
  get isNotFound() {
    return this.status === 404
  }
  get isUnauthorized() {
    return this.status === 401 || this.status === 403
  }
  get hasFieldErrors() {
    return Object.keys(this.fieldErrors).length > 0
  }
  /** Первая ошибка поля или undefined — удобно для :error у FormField. */
  field(name) {
    // Принимает и имя поля API (city_id), и camelCase из интерфейса (cityId, city → city_id).
    const snake = name.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`)
    const errors = this.fieldErrors[name] ?? this.fieldErrors[snake] ?? this.fieldErrors[`${snake}_id`]
    return errors?.[0]
  }
}

export function isAbortError(error) {
  return error?.name === 'AbortError'
}

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]+)`))
  return match ? decodeURIComponent(match[1]) : ''
}

function toMessages(value) {
  if (Array.isArray(value)) return value.map(String)
  if (value && typeof value === 'object') return Object.values(value).flatMap(toMessages)
  return [String(value)]
}

/**
 * Приводит тело ошибки к ApiError. Формы backend: {detail} (права, 404), {error} (ответы @action),
 * {code, detail, errors?} (auth), {field: [msgs], status_code} (валидация DRF), 429 с retry_after.
 */
function buildError(status, data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    const detail = Array.isArray(data) ? toMessages(data).join(' ') : undefined
    return new ApiError({ status, detail, data })
  }
  // status_code и retry_after — служебные числа, в ошибки полей не попадают (см. фильтр ниже).
  const { code = null, detail, error, errors, non_field_errors: nonField, ...rest } = data
  const fieldErrors = {}
  const source = errors && typeof errors === 'object' ? errors : rest
  for (const [field, value] of Object.entries(source)) {
    if (value == null || value === '' || typeof value === 'number' || typeof value === 'boolean') continue
    fieldErrors[field] = toMessages(value)
  }
  let message = typeof detail === 'string' ? detail : typeof error === 'string' ? error : undefined
  if (!message && nonField) message = toMessages(nonField).join(' ')
  if (!message && fieldErrors.non_field_errors) {
    message = fieldErrors.non_field_errors.join(' ')
    delete fieldErrors.non_field_errors
  }
  // Валидация без общего текста: показываем первую ошибку поля вместо безличного сообщения.
  if (!message && status === 400) message = Object.values(fieldErrors)[0]?.[0]
  return new ApiError({ status, code, detail: message, fieldErrors, data })
}

function buildUrl(url, params) {
  if (!params) return url
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) value.forEach((item) => search.append(key, item))
    else search.set(key, value)
  }
  const query = search.toString()
  return query ? `${url}${url.includes('?') ? '&' : '?'}${query}` : url
}

async function parseBody(response) {
  if (response.status === 204 || response.status === 205) return null
  const type = response.headers.get('content-type') || ''
  if (type.includes('application/json')) {
    try {
      return await response.json()
    } catch {
      return null
    }
  }
  try {
    return (await response.text()) || null
  } catch {
    // Тело не дочиталось (обрыв соединения, некорректный ответ прокси) — считаем, что его нет.
    return null
  }
}

async function ensureCsrfToken(signal) {
  let token = readCookie(CSRF_COOKIE)
  if (!token) {
    // Cookie ставит GET /api/auth/user/ — добираем её, если приложение ещё не успело.
    await fetch(CSRF_BOOTSTRAP_URL, { credentials: 'same-origin', signal }).catch(() => {})
    token = readCookie(CSRF_COOKIE)
  }
  return token
}

/**
 * @param {string} method
 * @param {string} url
 * @param {object} [options]
 * @param {object} [options.params]  query-параметры (пустые значения отбрасываются)
 * @param {*} [options.body]         объект → JSON; FormData/Blob/строка — как есть
 * @param {AbortSignal} [options.signal]
 * @param {object} [options.headers]
 */
export async function request(method, url, { params, body, signal, headers = {} } = {}) {
  const upper = method.toUpperCase()
  const init = {
    method: upper,
    credentials: 'same-origin',
    signal,
    headers: { Accept: 'application/json', ...headers },
  }

  if (body !== undefined && body !== null) {
    const raw = body instanceof FormData || body instanceof Blob || typeof body === 'string'
    if (raw) {
      init.body = body
    } else {
      init.body = JSON.stringify(body)
      init.headers['Content-Type'] = 'application/json'
    }
  }

  if (!SAFE_METHODS.has(upper)) {
    const token = await ensureCsrfToken(signal)
    if (token) init.headers['X-CSRFToken'] = token
  }

  let response
  try {
    response = await fetch(buildUrl(url, params), init)
  } catch (error) {
    if (isAbortError(error)) throw error
    throw new ApiError({ status: 0, code: 'network_error' })
  }

  const data = await parseBody(response)
  if (!response.ok) {
    // HTML-страницы ошибок (502 от nginx и т.п.) пользователю не показываем.
    throw buildError(response.status, typeof data === 'string' ? null : data)
  }
  return data
}

export const api = {
  get: (url, options) => request('GET', url, options),
  post: (url, body, options) => request('POST', url, { ...options, body }),
  put: (url, body, options) => request('PUT', url, { ...options, body }),
  patch: (url, body, options) => request('PATCH', url, { ...options, body }),
  delete: (url, options) => request('DELETE', url, options),
}
