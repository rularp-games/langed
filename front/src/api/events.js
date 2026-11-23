import { api } from './client'
import { runPayload } from './runs'
import {
  compact,
  normalizeCity,
  normalizeEventRegistration,
  normalizeGame,
  normalizeLink,
  normalizeList,
  normalizePage,
  normalizePeople,
  normalizeRoom,
  normalizeRun,
  normalizeVenueBrief,
} from './normalize'

/** Общее событие расписания: {id, name, date (UTC), dateLocal, duration (мин), description, canEdit, createdAt, updatedAt}. */
export function normalizeCommonEvent(raw) {
  return {
    id: raw.id,
    name: raw.name ?? '',
    date: raw.date ?? null,
    dateLocal: raw.date_local ?? null,
    duration: raw.duration ?? null,
    description: raw.description ?? '',
    canEdit: Boolean(raw.can_edit),
    createdAt: raw.created_at ?? null,
    updatedAt: raw.updated_at ?? null,
  }
}

/**
 * Проведение конвента: списочный, полный вид и расписание.
 * Всегда: {id, conventionId, conventionName, city, cityName, venue ({id,name,address}|null),
 *   venueName, dateStart, dateEnd ('YYYY-MM-DD'), capacity (null — без ограничения),
 *   registrationOpen, registrationsCount (подтверждённые), pendingRegistrationsCount,
 *   availableSlots (null — без ограничения), isFull, myRegistration, canEdit}
 * Список: + runsCount.
 * Полный вид: + description (описание конвента), links[], organizers[], games[] (кратко),
 *   runs[] ({id, gameName, date}), runsCount, createdAt, updatedAt.
 * Расписание: + description, cityTimezone, venueRooms[], organizers[], conventionOrganizers[],
 *   links[], runs[] (normalizeRun, вид расписания), commonEvents[], venues[], games[], runsCount.
 */
export function normalizeEvent(raw, { schedule = false } = {}) {
  if (!raw) return null
  const runs = raw.runs ?? []
  return {
    id: raw.id,
    conventionId: raw.convention ?? null,
    conventionName: raw.convention_name ?? '',
    description: raw.description ?? raw.convention_description ?? '',
    city: normalizeCity(raw.city),
    cityName: raw.city_name ?? raw.city?.name ?? '',
    cityTimezone: raw.city_timezone ?? raw.city?.timezone ?? null,
    venue: normalizeVenueBrief(raw.venue),
    venueName: raw.venue_name ?? null,
    venueRooms: (raw.venue_rooms ?? []).map(normalizeRoom),
    dateStart: raw.date_start ?? null,
    dateEnd: raw.date_end ?? null,
    capacity: raw.capacity ?? null,
    registrationOpen: Boolean(raw.registration_open),
    registrationsCount: raw.registrations_count ?? 0,
    pendingRegistrationsCount: raw.pending_registrations_count ?? 0,
    availableSlots: raw.available_slots ?? null,
    isFull: Boolean(raw.is_full),
    myRegistration: normalizeEventRegistration(raw.current_user_registration),
    canEdit: Boolean(raw.can_edit),
    organizers: normalizePeople(raw.organizers),
    conventionOrganizers: normalizePeople(raw.convention_organizers),
    links: (raw.links ?? []).map(normalizeLink),
    games: (raw.games ?? []).map(normalizeGame),
    venues: (raw.venues ?? []).map(normalizeVenueBrief),
    runs: schedule
      ? runs.map(normalizeRun)
      : runs.map((run) => ({ id: run.id, gameName: run.game_name ?? '', date: run.date ?? null })),
    commonEvents: (raw.common_events ?? []).map(normalizeCommonEvent),
    runsCount: raw.runs_count ?? runs.length,
    createdAt: raw.created_at ?? null,
    updatedAt: raw.updated_at ?? null,
  }
}

/** Тело создания/изменения проведения. dateStart/dateEnd — 'YYYY-MM-DD'; venueId и capacity можно null. */
function eventPayload(data) {
  return compact({
    convention_id: data.conventionId,
    city_id: data.cityId,
    venue_id: data.venueId,
    date_start: data.dateStart,
    date_end: data.dateEnd,
    capacity: data.capacity,
    registration_open: data.registrationOpen,
  })
}

/** Тело прогона в расписании: город и проведение backend подставляет сам. */
function scheduleRunPayload(data) {
  const { city_id: _city, convention_event_id: _event, ...payload } = runPayload(data)
  return payload
}

/** Тело общего события: date — локальное время города без пояса. */
function commonEventPayload(data) {
  return compact({
    name: data.name,
    date: data.date,
    duration: data.duration,
    description: data.description,
  })
}

const base = (id) => `/api/convention-events/${id}`

export const eventsApi = {
  /**
   * @param {{page?, pageSize?, time?: 'upcoming'|'past'|'all', city?: number, convention?: number,
   *          venue?: number, mine?: boolean}} [filters]  time передаётся всегда; по умолчанию здесь 'upcoming'.
   * @returns {Promise<{count:number, hasNext:boolean, hasPrevious:boolean, items:object[]}>}
   */
  async list(filters = {}, options) {
    const { page = 1, pageSize = 24, time = 'upcoming', city, convention, venue, mine } = filters
    const data = await api.get('/api/convention-events/', {
      ...options,
      params: { page, page_size: pageSize, time, city, convention, venue, mine: mine ? 1 : undefined },
    })
    return normalizePage(data, normalizeEvent)
  },

  async get(id, options) {
    return normalizeEvent(await api.get(`${base(id)}/`, options))
  },

  /** Проведение вместе с расписанием (прогоны, общие события, помещения) — одним запросом. */
  async schedule(id, options) {
    return normalizeEvent(await api.get(`${base(id)}/schedule/`, options), { schedule: true })
  },

  /** Города, в которых есть проведения: [{id, name}]. */
  async cities(options) {
    return (await api.get('/api/convention-events/cities/', options)) ?? []
  },

  /** Обязательны conventionId, cityId, dateStart, dateEnd. Организаторы наследуются от конвента. */
  async create(data) {
    return normalizeEvent(await api.post('/api/convention-events/', eventPayload(data)))
  },

  async update(id, data) {
    return normalizeEvent(await api.patch(`${base(id)}/`, eventPayload(data)))
  },

  remove(id) {
    return api.delete(`${base(id)}/`)
  },

  // --- Расписание ---

  /** Обязательны gameId, date; необязательны duration, roomIds, maxPlayers, registrationOpen. @returns прогон (вид расписания) */
  async addRun(id, data) {
    return normalizeRun(await api.post(`${base(id)}/add_run/`, scheduleRunPayload(data)))
  },

  async updateRun(id, runId, data) {
    return normalizeRun(await api.patch(`${base(id)}/update_run/`, { run_id: runId, ...scheduleRunPayload(data) }))
  },

  removeRun(id, runId) {
    return api.delete(`${base(id)}/remove_run/`, { params: { run_id: runId } })
  },

  /** Обязательны name, date; необязательны duration, description. */
  async addCommonEvent(id, data) {
    return normalizeCommonEvent(await api.post(`${base(id)}/add_common_event/`, commonEventPayload(data)))
  },

  async updateCommonEvent(id, commonEventId, data) {
    return normalizeCommonEvent(
      await api.patch(`${base(id)}/update_common_event/`, {
        common_event_id: commonEventId,
        ...commonEventPayload(data),
      }),
    )
  },

  removeCommonEvent(id, commonEventId) {
    return api.delete(`${base(id)}/remove_common_event/`, { params: { common_event_id: commonEventId } })
  },

  // --- Организаторы проведения ---

  /** @returns {Promise<object>} обновлённое проведение (полный вид) */
  async addOrganizer(id, username) {
    return normalizeEvent(await api.post(`${base(id)}/add_organizer/`, { username }))
  },

  async removeOrganizer(id, userId) {
    return normalizeEvent(await api.post(`${base(id)}/remove_organizer/`, { user_id: userId }))
  },

  // --- Регистрация на конвент ---

  /** @returns {Promise<{registration: object, message: string}>} заявка создаётся в статусе pending */
  async register(id, { comment = '' } = {}) {
    const data = await api.post(`${base(id)}/register/`, { comment })
    return { registration: normalizeEventRegistration(data.registration), message: data.message ?? '' }
  },

  /**
   * Вместе с заявкой на проведение backend снимает заявки участника на его предстоящие прогоны.
   * @returns {Promise<{runsUnregistered: number}>}
   */
  async unregister(id) {
    const data = await api.post(`${base(id)}/unregister/`)
    return { runsUnregistered: data?.runs_unregistered ?? 0 }
  },

  /** Заявки на проведение (организаторы, staff). */
  async registrations(id, options) {
    return normalizeList(await api.get(`${base(id)}/registrations/`, options), normalizeEventRegistration)
  },

  /**
   * @param {{status?: 'pending'|'confirmed'|'rejected'|'cancelled', adminComment?: string}} changes
   * @returns {Promise<object>} обновлённая заявка
   */
  async updateRegistration(id, registrationId, { status, adminComment } = {}) {
    const data = await api.post(
      `${base(id)}/update_registration/`,
      compact({ registration_id: registrationId, status, admin_comment: adminComment }),
    )
    return normalizeEventRegistration(data.registration)
  },
}
