import { api } from './client'
import { compact, normalizeCity, normalizeList } from './normalize'

export { normalizeCity }

export const citiesApi = {
  /** Все города (простой массив): [{id, name, timezone, region}]. В компонентах — через useCitiesStore. */
  async list(options) {
    return normalizeList(await api.get('/api/cities/', options), normalizeCity)
  },

  /** {name, timezone?} — регион через API не задаётся. */
  async create({ name, timezone }) {
    return normalizeCity(await api.post('/api/cities/', compact({ name, timezone })))
  },

  /** Правка названия и часового пояса — только staff. */
  async update(id, { name, timezone }) {
    return normalizeCity(await api.patch(`/api/cities/${id}/`, compact({ name, timezone })))
  },

}
