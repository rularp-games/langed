import { api } from './client'
import { compact, normalizeList, normalizePage, normalizeRun, normalizeRunRegistration } from './normalize'

export { normalizeRun, normalizeRunRegistration }

/**
 * Тело запроса создания/изменения прогона (camelCase → поля API). Все поля необязательны (PATCH).
 * date — локальное время города без пояса: 'YYYY-MM-DDTHH:mm[:ss]' (см. utils/datetime fromDateTimeInput).
 * maxPlayers: null — брать максимум игроков из игры. eventId: null — прогон вне конвента.
 */
export function runPayload(data) {
  return compact({
    game_id: data.gameId,
    date: data.date,
    duration: data.duration,
    city_id: data.cityId,
    room_ids: data.roomIds,
    convention_event_id: data.eventId,
    max_players: data.maxPlayers,
    registration_open: data.registrationOpen,
  })
}

export const runsApi = {
  /**
   * @param {{page?, pageSize?, time?: 'upcoming'|'past'|'all', city?: number, game?: number,
   *          event?: number, master?: number, standalone?: boolean, mine?: boolean}} [filters]
   *   time по умолчанию 'upcoming' (ближайшие первыми); past/all — недавние первыми.
   * @returns {Promise<{count:number, hasNext:boolean, hasPrevious:boolean, items:object[]}>}
   */
  async list(filters = {}, options) {
    const { page = 1, pageSize = 24, time = 'upcoming', city, game, event, master, standalone, mine } = filters
    const data = await api.get('/api/runs/', {
      ...options,
      params: {
        page,
        page_size: pageSize,
        time,
        city,
        game,
        convention_event: event,
        master,
        standalone: standalone ? 1 : undefined,
        mine: mine ? 1 : undefined,
      },
    })
    return normalizePage(data, normalizeRun)
  },

  /** Полный прогон: game с анонсом и красными флагами, registrations — если есть право управлять. */
  async get(id, options) {
    return normalizeRun(await api.get(`/api/runs/${id}/`, options))
  },

  /** Города, в которых есть прогоны: [{id, name}]. */
  async cities(options) {
    return (await api.get('/api/runs/cities/', options)) ?? []
  },

  /** Обязательны gameId, date, cityId. Текущий пользователь становится мастером. */
  async create(data) {
    return normalizeRun(await api.post('/api/runs/', runPayload(data)))
  },

  async update(id, data) {
    return normalizeRun(await api.patch(`/api/runs/${id}/`, runPayload(data)))
  },

  remove(id) {
    return api.delete(`/api/runs/${id}/`)
  },

  async addMaster(id, username) {
    return normalizeRun(await api.post(`/api/runs/${id}/add_master/`, { username }))
  },

  async removeMaster(id, userId) {
    return normalizeRun(await api.post(`/api/runs/${id}/remove_master/`, { user_id: userId }))
  },

  /**
   * Записаться на прогон.
   * @param {{rolePreference?: 'any'|'female'|'male', isTechnician?: boolean, comment?: string}} [data]
   * @returns {Promise<{registration: object, run: object}>}
   */
  async register(id, { rolePreference = 'any', isTechnician = false, comment = '' } = {}) {
    const data = await api.post(`/api/runs/${id}/register/`, {
      role_preference: rolePreference,
      is_technician: isTechnician,
      comment,
    })
    return { registration: normalizeRunRegistration(data.registration), run: normalizeRun(data.run) }
  },

  /** @returns {Promise<{run: object}>} */
  async unregister(id) {
    const data = await api.post(`/api/runs/${id}/unregister/`)
    return { run: normalizeRun(data.run) }
  },

  /** Заявки на прогон (мастер, организатор конвента, staff). */
  async registrations(id, options) {
    return normalizeList(await api.get(`/api/runs/${id}/registrations/`, options), normalizeRunRegistration)
  },

  /**
   * @param {'pending'|'confirmed'|'rejected'|'cancelled'|'waitlist'} status
   * @returns {Promise<{registration: object, run: object}>}
   */
  async updateRegistration(id, registrationId, status) {
    const data = await api.post(`/api/runs/${id}/update_registration/`, {
      registration_id: registrationId,
      status,
    })
    return { registration: normalizeRunRegistration(data.registration), run: normalizeRun(data.run) }
  },
}
