import { api } from './client'
import { compact, normalizeCity, normalizeList, normalizePage, normalizeRoom } from './normalize'

export { normalizeRoom }

/** Площадка: {id, name, address, city, description, capacity (число|null), rooms[], createdAt, updatedAt}. */
export function normalizeVenue(raw) {
  if (!raw) return null
  return {
    id: raw.id,
    name: raw.name ?? '',
    address: raw.address ?? '',
    city: normalizeCity(raw.city),
    description: raw.description ?? '',
    capacity: raw.capacity ?? null,
    rooms: (raw.rooms ?? []).map(normalizeRoom),
    createdAt: raw.created_at ?? null,
    updatedAt: raw.updated_at ?? null,
  }
}

function venuePayload(data) {
  return compact({
    name: data.name,
    address: data.address,
    city_id: data.cityId,
    description: data.description,
    capacity: data.capacity,
  })
}

function roomPayload(data) {
  return compact({ venue_id: data.venueId, name: data.name, blackbox: data.blackbox })
}

export const venuesApi = {
  /**
   * @param {{page?, pageSize?, search?, city?: number}} [filters]  поиск по названию и адресу
   * @returns {Promise<{count:number, hasNext:boolean, hasPrevious:boolean, items:object[]}>}
   */
  async list({ page = 1, pageSize = 24, search = '', city } = {}, options) {
    const data = await api.get('/api/venues/', { ...options, params: { page, page_size: pageSize, search, city } })
    return normalizePage(data, normalizeVenue)
  },

  async get(id, options) {
    return normalizeVenue(await api.get(`/api/venues/${id}/`, options))
  },

  /** Обязательны name, cityId. Создавать и менять может любой вошедший, удалять — только staff. */
  async create(data) {
    return normalizeVenue(await api.post('/api/venues/', venuePayload(data)))
  },

  async update(id, data) {
    return normalizeVenue(await api.patch(`/api/venues/${id}/`, venuePayload(data)))
  },

  remove(id) {
    return api.delete(`/api/venues/${id}/`)
  },

  // --- Помещения (/api/rooms/, простой массив) ---

  /** @param {{venue?: number, blackbox?: boolean}} [filters] */
  async listRooms({ venue, blackbox } = {}, options) {
    const data = await api.get('/api/rooms/', {
      ...options,
      params: { venue, blackbox: blackbox === undefined ? undefined : String(blackbox) },
    })
    return normalizeList(data, normalizeRoom)
  },

  /** Обязательны venueId, name. */
  async createRoom(data) {
    return normalizeRoom(await api.post('/api/rooms/', roomPayload(data)))
  },

  async updateRoom(roomId, data) {
    return normalizeRoom(await api.patch(`/api/rooms/${roomId}/`, roomPayload(data)))
  },

  /** Только staff. */
  removeRoom(roomId) {
    return api.delete(`/api/rooms/${roomId}/`)
  },
}
