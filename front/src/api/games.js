import { api } from './client'
import { compact, fileForm, normalizeGame, normalizePage } from './normalize'

export { normalizeGame }

/**
 * Тело запроса создания/изменения игры. Поля — в camelCase, все необязательны (PATCH).
 * Числа состава: null — не указано.
 * poster: File — загрузить (запрос уйдёт как multipart); null — убрать постер; не задан — не менять.
 */
function gamePayload(data) {
  const fields = compact({
    name: data.name,
    announcement: data.announcement,
    red_flags: data.redFlags,
    authors_text: data.authorsText,
    source_url: data.sourceUrl,
    players_min: data.playersMin,
    players_max: data.playersMax,
    female_roles_min: data.femaleRolesMin,
    female_roles_max: data.femaleRolesMax,
    male_roles_min: data.maleRolesMin,
    male_roles_max: data.maleRolesMax,
    technicians: data.technicians,
  })
  if (data.poster instanceof Blob) {
    const form = new FormData()
    for (const [key, value] of Object.entries(fields)) form.append(key, value ?? '')
    form.append('poster', data.poster)
    return form
  }
  if (data.poster === null) fields.poster = null
  return fields
}

export const gamesApi = {
  /**
   * @param {{page?, pageSize?, search?, ordering?: 'name'|'-name'|'created_at'|'-created_at',
   *          creator?: number, mine?: boolean}} [filters]
   * @returns {Promise<{count:number, hasNext:boolean, hasPrevious:boolean, items:object[]}>}
   */
  async list({ page = 1, pageSize = 24, search = '', ordering = '', creator, mine } = {}, options) {
    const data = await api.get('/api/games/', {
      ...options,
      params: { page, page_size: pageSize, search, ordering, creator, mine: mine ? 1 : undefined },
    })
    return normalizePage(data, normalizeGame)
  },

  async get(id, options) {
    return normalizeGame(await api.get(`/api/games/${id}/`, options))
  },

  /** Создать игру; текущий пользователь становится автором. */
  async create(data) {
    return normalizeGame(await api.post('/api/games/', gamePayload(data)))
  },

  /** Частичное изменение (PATCH). */
  async update(id, data) {
    return normalizeGame(await api.patch(`/api/games/${id}/`, gamePayload(data)))
  },

  remove(id) {
    return api.delete(`/api/games/${id}/`)
  },

  /** @returns {Promise<object>} обновлённая игра */
  async addCreator(id, username) {
    return normalizeGame(await api.post(`/api/games/${id}/add_creator/`, { username }))
  },

  /** @returns {Promise<object>} обновлённая игра */
  async removeCreator(id, userId) {
    return normalizeGame(await api.post(`/api/games/${id}/remove_creator/`, { user_id: userId }))
  },

  /** CSV со столбцами «название», «анонс», «красные флаги». @returns {{created, skipped, games[]}} */
  async importCsv(file) {
    const data = await api.post('/api/games/import_csv/', fileForm(file))
    return {
      created: data?.created ?? 0,
      skipped: data?.skipped ?? 0,
      games: (data?.games ?? []).map(normalizeGame),
    }
  },
}
