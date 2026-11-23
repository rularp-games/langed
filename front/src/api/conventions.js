import { api } from './client'
import { compact, fileForm, normalizeLink, normalizePage, normalizePeople } from './normalize'

export { normalizeLink }

/** Типы ссылок конвента (link_type) с подписями. */
export const LINK_TYPES = [
  { value: 'website', label: 'Сайт' },
  { value: 'vk', label: 'ВКонтакте' },
  { value: 'telegram', label: 'Telegram' },
  { value: 'discord', label: 'Discord' },
  { value: 'youtube', label: 'YouTube' },
  { value: 'other', label: 'Другое' },
]

/** Конвент: {id, name, description, organizers[], eventsCount, links[], canEdit, createdAt, updatedAt}. */
export function normalizeConvention(raw) {
  if (!raw) return null
  return {
    id: raw.id,
    name: raw.name ?? '',
    description: raw.description ?? '',
    organizers: normalizePeople(raw.organizers),
    eventsCount: raw.events_count ?? 0,
    links: (raw.links ?? []).map(normalizeLink),
    canEdit: Boolean(raw.can_edit),
    createdAt: raw.created_at ?? null,
    updatedAt: raw.updated_at ?? null,
  }
}

function linkPayload(data) {
  return compact({
    convention_id: data.conventionId,
    url: data.url,
    link_type: data.type,
    title: data.title,
  })
}

export const conventionsApi = {
  /**
   * @param {{page?, pageSize?, search?}} [filters]  сортировка — по названию
   * @returns {Promise<{count:number, hasNext:boolean, hasPrevious:boolean, items:object[]}>}
   */
  async list({ page = 1, pageSize = 24, search = '' } = {}, options) {
    const data = await api.get('/api/conventions/', { ...options, params: { page, page_size: pageSize, search } })
    return normalizePage(data, normalizeConvention)
  },

  async get(id, options) {
    return normalizeConvention(await api.get(`/api/conventions/${id}/`, options))
  },

  /** {name, description}. Текущий пользователь становится организатором. */
  async create({ name, description }) {
    return normalizeConvention(await api.post('/api/conventions/', compact({ name, description })))
  },

  async update(id, { name, description }) {
    return normalizeConvention(await api.patch(`/api/conventions/${id}/`, compact({ name, description })))
  },

  remove(id) {
    return api.delete(`/api/conventions/${id}/`)
  },

  /** @returns {Promise<object>} обновлённый конвент */
  async addOrganizer(id, username) {
    return normalizeConvention(await api.post(`/api/conventions/${id}/add_organizer/`, { username }))
  },

  async removeOrganizer(id, userId) {
    return normalizeConvention(await api.post(`/api/conventions/${id}/remove_organizer/`, { user_id: userId }))
  },

  /** Только staff. @returns {{conventionsCreated, eventsCreated, eventsSkipped}} */
  async importCsv(file) {
    const data = await api.post('/api/conventions/import_csv/', fileForm(file))
    return {
      conventionsCreated: data?.conventions_created ?? 0,
      eventsCreated: data?.events_created ?? 0,
      eventsSkipped: data?.events_skipped ?? 0,
    }
  },

  // --- Ссылки конвента (/api/convention-links/); читаются вместе с конвентом в поле links ---

  /** Обязательны conventionId, url, type; title необязателен. */
  async createLink(data) {
    return normalizeLink(await api.post('/api/convention-links/', linkPayload(data)))
  },

  async updateLink(linkId, data) {
    return normalizeLink(await api.patch(`/api/convention-links/${linkId}/`, linkPayload(data)))
  },

  removeLink(linkId) {
    return api.delete(`/api/convention-links/${linkId}/`)
  },
}
